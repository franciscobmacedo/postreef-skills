#!/usr/bin/env python3
"""Batch-extract a list of URLs through Post Reef with one schema. Stdlib only.

  python3 batch_extract.py urls.txt --schema research.schema.json --inputs transcript,comments --quote-only
  python3 batch_extract.py urls.txt --schema research.schema.json --inputs transcript,comments --out results.jsonl
  python3 batch_extract.py urls.txt --parts comments --out results.jsonl        # download-only (no AI)

Reads one URL per line (blank lines and # comments ignored). Quotes every URL
first via the free probe and prints the total; without --quote-only it then
submits them, keeping within the API's limits (6 submits/min, 2 concurrent
extractions per account; extra submissions queue server-side), waits for each
result, and appends one JSON object per URL to --out. Re-running skips URLs
already present in --out, so a crash is resumable.

Env: POSTREEF_API_KEY (required), POSTREEF_BASE_URL (optional).
Costs credits. 1 credit = $0.0001. Same (url, schema, inputs) within 30 days
is served from cache for free.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import postreef  # noqa: E402  (bundled client, same directory)

SUBMITS_PER_MINUTE = 6
POLL_INTERVAL = 5


def read_urls(path: str) -> list[str]:
    out: list[str] = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and line not in out:
            out.append(line)
    return out


def already_done(out_path: str | None) -> set[str]:
    if not out_path or not Path(out_path).exists():
        return set()
    done = set()
    for line in Path(out_path).read_text().splitlines():
        try:
            done.add(json.loads(line)["url"])
        except (json.JSONDecodeError, KeyError):
            pass
    return done


def body_for(url: str, args) -> dict:
    body: dict = {"url": url}
    if args.parts:
        body["parts"] = postreef.csv_list(args.parts)
    else:
        if args.inputs:
            body["inputs"] = postreef.csv_list(args.inputs)
        if args.schema:
            body["schema"] = json.loads(Path(args.schema).read_text())
        elif args.schema_id:
            body["schemaId"] = args.schema_id
    return body


def probe_body(url: str, args) -> dict:
    b = body_for(url, args)
    return {k: v for k, v in b.items() if k in ("url", "parts", "inputs", "schema", "schemaId")}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("urls_file")
    p.add_argument("--schema", help="JSON Schema file (AI run)")
    p.add_argument("--schema-id", help="predefined/saved schema id (AI run)")
    p.add_argument("--inputs", help="comma list for AI runs, e.g. transcript,comments")
    p.add_argument("--parts", help="comma list for download-only runs, e.g. comments")
    p.add_argument("--prompt", help="extraction guidance sent with the schema")
    p.add_argument("--policy", choices=["strict", "fallback", "best-effort"])
    p.add_argument("--force", action="store_true", help="bypass the 30-day cache")
    p.add_argument("--out", help="JSONL output path (required unless --quote-only)")
    p.add_argument("--quote-only", action="store_true", help="probe every URL, print the total, submit nothing")
    p.add_argument("--max-credits", type=int, help="abort before submitting if the quoted total exceeds this")
    p.add_argument("--timeout", type=float, default=900, help="seconds to wait per extraction")
    args = p.parse_args()

    if args.parts and (args.inputs or args.schema or args.schema_id):
        sys.exit("--parts (download-only) cannot be combined with --inputs/--schema/--schema-id")
    if not args.parts and not (args.schema or args.schema_id):
        sys.exit("give --schema FILE or --schema-id ID for an AI run, or --parts for download-only")
    if not args.quote_only and not args.out:
        sys.exit("--out results.jsonl is required (or use --quote-only)")

    urls = read_urls(args.urls_file)
    done = already_done(args.out)
    todo = [u for u in urls if u not in done]
    postreef.log(f"{len(urls)} urls, {len(done)} already in {args.out or '(none)'}, {len(todo)} to run")

    # 1. Quote everything (free; 10/min limit handled by the client's 429 retry)
    total = 0
    quotes: dict[str, dict] = {}
    unavailable: list[tuple[str, str]] = []
    for i, url in enumerate(todo, 1):
        try:
            _, q, _ = postreef.request("POST", "/v1/probe", probe_body(url, args))
            quotes[url] = q
            total += q["price"]["credits"]
            postreef.log(f"  [{i}/{len(todo)}] {q['price']['credits']:>5} cr  {q.get('durationSec')}s  {q.get('title')!s:.60}")
        except postreef.ApiError as e:
            unavailable.append((url, f"{e.code}: {e.message}"))
            postreef.log(f"  [{i}/{len(todo)}] SKIP {e.code}: {url}")
        if i % 10 == 0:
            time.sleep(60)  # probe limit is 10/min
    postreef.log(f"quoted total: {total} credits (${total / 10000:.4f}); {len(unavailable)} unavailable")
    if args.quote_only:
        print(json.dumps({"urls": len(todo), "credits": total, "usd": total / 10000, "unavailable": unavailable}, indent=2))
        return 0
    if args.max_credits is not None and total > args.max_credits:
        sys.exit(f"quoted {total} credits exceeds --max-credits {args.max_credits}; nothing submitted")

    # 2. Submit + wait, one JSONL row per URL
    out = open(args.out, "a")
    submitted_at: list[float] = []
    for i, url in enumerate([u for u in todo if u in quotes], 1):
        # stay under 6 submits / minute
        submitted_at = [t for t in submitted_at if time.time() - t < 60]
        if len(submitted_at) >= SUBMITS_PER_MINUTE:
            wait = 60 - (time.time() - submitted_at[0]) + 1
            postreef.log(f"  submit window full; sleeping {wait:.0f}s")
            time.sleep(max(wait, 1))
        body = body_for(url, args)
        if args.prompt:
            body["prompt"] = args.prompt
        if args.policy:
            body["policy"] = args.policy
        if args.force:
            body["force"] = True
        row: dict = {"url": url}
        try:
            _, sub, _ = postreef.request("POST", "/v1/extractions", body, headers={"Idempotency-Key": f"batch:{url}:{args.schema or args.schema_id or args.parts}"})
            submitted_at.append(time.time())
            row["id"] = sub["id"]
            postreef.log(f"  [{i}] submitted {sub['id']} ({sub.get('creditsDebited')} cr) {url}")
            result = postreef.wait_for_result(sub["id"], timeout=args.timeout, interval=POLL_INTERVAL)
            row["status"] = result.get("status")
            if result.get("status") == "complete":
                row["outcome"] = result.get("outcome")
                row["verdictReason"] = result.get("verdictReason")
                s = result.get("summary") or {}
                row["summary"] = {k: s.get(k) for k in ("title", "uploader", "duration", "view_count", "like_count", "comment_count", "upload_date", "webpage_url")}
                row["extraction"] = result.get("extraction")
            else:
                row["error"] = result.get("error")
        except postreef.ApiError as e:
            row["status"] = "error"
            row["error"] = f"{e.code}: {e.message}"
            postreef.log(f"  [{i}] ERROR {e.code}: {e.message}")
            if e.code == "insufficient_credits":
                out.write(json.dumps(row) + "\n"); out.flush()
                sys.exit("out of credits; top up and re-run (already-done URLs are skipped)")
        out.write(json.dumps(row) + "\n")
        out.flush()
    postreef.log(f"done -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
