#!/usr/bin/env python3
"""Minimal Post Reef v1 client. Zero dependencies (stdlib only), Python 3.9+.

Post Reef (https://postreef.com) is a paid API that turns a public video /
social-post / article URL into: metadata, transcript, comments, media files
and (optionally) a JSON object conforming to a JSON Schema you supply.

Env:
  POSTREEF_API_KEY   required. Create one at https://postreef.com/developers/api-keys
  POSTREEF_BASE_URL  optional, default https://postreef.com

Commands (all print JSON to stdout, progress to stderr):

  probe   URL [--parts a,b | --inputs a,b --schema FILE | --schema-id ID]
          Free. Returns title, duration, hasSubtitles, hasComments and the
          exact credit price for the run you describe.

  extract URL [--parts a,b] [--inputs a,b] [--schema FILE | --schema-id ID]
          [--prompt TEXT] [--force] [--policy strict|fallback|best-effort]
          [--auto --max-spend N] [--out DIR] [--no-wait] [--timeout SEC]
          Submits, waits for completion, downloads every artifact into DIR
          (default ./postreef-out/<id>/), writes result.json, prints result.
          Costs credits (quote it with `probe` first).

  result  ID [--out DIR]     Fetch/wait for an existing extraction's result.
  files   ID NAME [--out DIR] Download one artifact listed in summary.files.
  list    [--limit N]         List recent extractions.

Artifacts: parts/inputs are any of transcript, comments, audio, video.
`--parts` = download-only run (no AI, no schema). `--inputs` + a schema =
AI extraction. Metadata, thumbnail and description always come back.

API reference: https://postreef.com/docs/api/reference  (OpenAPI 3.1 at
https://postreef.com/v1/openapi.json)
"""
from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

BASE = os.environ.get("POSTREEF_BASE_URL", "https://postreef.com").rstrip("/")
ARTIFACTS = ("transcript", "comments", "audio", "video")
USER_AGENT = "postreef-skills/0.1 (+https://github.com/franciscobmacedo/postreef-skills)"


def _ssl_context() -> ssl.SSLContext:
    """python.org macOS builds ship without system CA certs; prefer certifi when present."""
    try:
        import certifi  # type: ignore
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


_SSL = _ssl_context()


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details=None):
        super().__init__(f"{status} {code}: {message}")
        self.status, self.code, self.message, self.details = status, code, message, details


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def api_key() -> str:
    key = os.environ.get("POSTREEF_API_KEY")
    if not key:
        sys.exit(
            "POSTREEF_API_KEY is not set. Create a key at "
            f"{BASE}/developers/api-keys and export it."
        )
    return key


def request(method: str, path: str, body=None, headers=None, raw=False, retries=3):
    """One HTTP call. Retries 429 using Retry-After and 5xx with backoff.
    Returns (status, parsed_json_or_bytes, response_headers)."""
    url = path if path.startswith("http") else f"{BASE}{path}"
    # A named User-Agent: the default "Python-urllib/x.y" is rejected (403) at postreef.com's edge.
    hdrs = {"x-api-key": api_key(), "Accept": "application/json", "User-Agent": USER_AGENT}
    if body is not None:
        hdrs["Content-Type"] = "application/json"
    if headers:
        hdrs.update(headers)
    data = json.dumps(body).encode() if body is not None else None
    attempt = 0
    while True:
        attempt += 1
        req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
        try:
            with urllib.request.urlopen(req, timeout=120, context=_SSL) as resp:
                payload = resp.read()
                if raw:
                    return resp.status, payload, dict(resp.headers)
                return resp.status, (json.loads(payload) if payload else None), dict(resp.headers)
        except urllib.error.HTTPError as e:
            payload = e.read()
            try:
                parsed = json.loads(payload) if payload else {}
            except json.JSONDecodeError:
                parsed = {"error": {"code": "http_error", "message": payload[:200].decode(errors="replace")}}
            err = parsed.get("error") if isinstance(parsed, dict) else None
            code = (err or {}).get("code", "http_error")
            message = (err or {}).get("message", str(e))
            details = (err or {}).get("details")
            retryable = e.code == 429 or (e.code >= 500 and method == "GET")
            if retryable and attempt <= retries:
                wait = e.headers.get("Retry-After")
                delay = float(wait) if wait and wait.isdigit() else min(2 ** attempt, 30)
                log(f"  {e.code} {code}; retrying in {delay:.0f}s")
                time.sleep(delay)
                continue
            raise ApiError(e.code, code, message, details) from None
        except urllib.error.URLError as e:
            if attempt <= retries:
                delay = min(2 ** attempt, 30)
                log(f"  network error ({e.reason}); retrying in {delay}s")
                time.sleep(delay)
                continue
            raise


def csv_list(value: str | None) -> list[str] | None:
    if not value:
        return None
    items = [v.strip() for v in value.split(",") if v.strip()]
    bad = [i for i in items if i not in ARTIFACTS]
    if bad:
        sys.exit(f"unknown artifact(s) {bad}; valid: {', '.join(ARTIFACTS)}")
    return items


def build_body(args, for_probe: bool) -> dict:
    body: dict = {"url": args.url}
    parts = csv_list(getattr(args, "parts", None))
    inputs = csv_list(getattr(args, "inputs", None))
    schema_file = getattr(args, "schema", None)
    schema_id = getattr(args, "schema_id", None)
    if schema_file and schema_id:
        sys.exit("use either --schema FILE or --schema-id ID, not both")
    if parts and (inputs or schema_file or schema_id):
        sys.exit("--parts is a download-only run; it cannot be combined with --inputs or a schema")
    if inputs and not (schema_file or schema_id):
        sys.exit("--inputs requires a schema (--schema FILE or --schema-id ID); "
                 "for a download-only run use --parts")
    if parts:
        body["parts"] = parts
    if inputs:
        body["inputs"] = inputs
    if schema_file:
        body["schema"] = json.loads(Path(schema_file).read_text())
    if schema_id:
        body["schemaId"] = schema_id
    if for_probe:
        return body
    if getattr(args, "prompt", None):
        body["prompt"] = args.prompt
    if getattr(args, "force", False):
        body["force"] = True
    if getattr(args, "policy", None):
        body["policy"] = args.policy
    if getattr(args, "auto", False):
        if not getattr(args, "max_spend", None):
            sys.exit("--auto requires --max-spend N (credits)")
        body["auto"] = True
        body["maxSpendCredits"] = args.max_spend
    if getattr(args, "webhook_url", None):
        body["webhookUrl"] = args.webhook_url
    return body


def cmd_probe(args) -> dict:
    status, data, _ = request("POST", "/v1/probe", build_body(args, for_probe=True))
    return data


def wait_for_result(run_id: str, timeout: float, interval: float = 5.0) -> dict:
    deadline = time.time() + timeout
    last = None
    while True:
        status, data, _ = request("GET", f"/v1/extractions/{run_id}/result")
        if status == 200:
            return data
        phase = (data or {}).get("status")
        if phase != last:
            log(f"  {run_id}: {phase}")
            last = phase
        if time.time() > deadline:
            sys.exit(f"timed out after {timeout:.0f}s; poll later with: postreef.py result {run_id}")
        time.sleep(interval)


def download_all(run_id: str, result: dict, out_dir: Path) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "result.json").write_text(json.dumps(result, indent=2))
    names = (result.get("summary") or {}).get("files") or []
    saved = []
    for name in names:
        _, payload, _ = request("GET", f"/v1/extractions/{run_id}/files/{urllib.parse.quote(name)}", raw=True)
        (out_dir / name).write_bytes(payload)
        saved.append(name)
        log(f"  saved {out_dir / name} ({len(payload)} bytes)")
    return saved


def cmd_extract(args) -> dict:
    body = build_body(args, for_probe=False)
    headers = {"Idempotency-Key": args.idempotency_key or str(uuid.uuid4())}
    status, sub, _ = request("POST", "/v1/extractions", body, headers=headers)
    run_id = sub["id"]
    log(f"submitted {run_id} status={sub['status']} creditsDebited={sub.get('creditsDebited')}")
    if args.no_wait:
        return sub
    result = wait_for_result(run_id, timeout=args.timeout)
    out_dir = Path(args.out) if args.out else Path("postreef-out") / run_id
    if result.get("status") == "failed":
        log(f"  failed: {result.get('error')} (credits refunded)")
        (out_dir).mkdir(parents=True, exist_ok=True)
        (out_dir / "result.json").write_text(json.dumps(result, indent=2))
        return result
    outcome = result.get("outcome")
    if outcome in ("no_match", "uncertain"):
        log(f"  outcome={outcome}: {result.get('verdictReason')}")
    if not args.no_download:
        download_all(run_id, result, out_dir)
    else:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "result.json").write_text(json.dumps(result, indent=2))
    log(f"  result written to {out_dir / 'result.json'}")
    return result


def cmd_result(args) -> dict:
    result = wait_for_result(args.id, timeout=args.timeout)
    if args.out is not None or args.download:
        out_dir = Path(args.out) if args.out else Path("postreef-out") / args.id
        if result.get("status") == "complete":
            download_all(args.id, result, out_dir)
    return result


def cmd_files(args) -> dict:
    _, payload, hdrs = request("GET", f"/v1/extractions/{args.id}/files/{urllib.parse.quote(args.name)}", raw=True)
    out_dir = Path(args.out) if args.out else Path("postreef-out") / args.id
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / args.name).write_bytes(payload)
    return {"saved": str(out_dir / args.name), "bytes": len(payload), "contentType": hdrs.get("Content-Type")}


def cmd_list(args) -> dict:
    q = urllib.parse.urlencode({"limit": args.limit})
    _, data, _ = request("GET", f"/v1/extractions?{q}")
    return data


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_selection(sp):
        sp.add_argument("url")
        sp.add_argument("--parts", help="download-only: comma list of transcript,comments,audio,video")
        sp.add_argument("--inputs", help="AI run: comma list of transcript,comments,audio,video (needs a schema)")
        sp.add_argument("--schema", help="path to a JSON Schema file (AI run)")
        sp.add_argument("--schema-id", help="predefined or saved schema id, e.g. postreef.predefined.recipe.v1")

    sp = sub.add_parser("probe", help="free quote + availability check")
    add_selection(sp)
    sp.set_defaults(fn=cmd_probe)

    sp = sub.add_parser("extract", help="submit, wait, download (costs credits)")
    add_selection(sp)
    sp.add_argument("--prompt", help="extraction guidance sent with the schema")
    sp.add_argument("--force", action="store_true", help="bypass the 30-day result cache (billed as fresh)")
    sp.add_argument("--policy", choices=["strict", "fallback", "best-effort"])
    sp.add_argument("--auto", action="store_true", help="auto mode: start cheap, climb to audio/video only if needed")
    sp.add_argument("--max-spend", type=int, help="credit ceiling for --auto")
    sp.add_argument("--webhook-url", help="per-run https webhook")
    sp.add_argument("--idempotency-key", help="defaults to a fresh UUID")
    sp.add_argument("--out", help="output directory (default postreef-out/<id>)")
    sp.add_argument("--no-wait", action="store_true", help="return right after submit")
    sp.add_argument("--no-download", action="store_true", help="don't fetch artifacts, just result.json")
    sp.add_argument("--timeout", type=float, default=900, help="seconds to wait for completion")
    sp.set_defaults(fn=cmd_extract)

    sp = sub.add_parser("result", help="fetch or wait for a result")
    sp.add_argument("id")
    sp.add_argument("--out")
    sp.add_argument("--download", action="store_true")
    sp.add_argument("--timeout", type=float, default=900)
    sp.set_defaults(fn=cmd_result)

    sp = sub.add_parser("files", help="download one artifact")
    sp.add_argument("id")
    sp.add_argument("name")
    sp.add_argument("--out")
    sp.set_defaults(fn=cmd_files)

    sp = sub.add_parser("list", help="recent extractions")
    sp.add_argument("--limit", type=int, default=20)
    sp.set_defaults(fn=cmd_list)

    args = p.parse_args(argv)
    try:
        out = args.fn(args)
    except ApiError as e:
        hint = ""
        if e.code == "insufficient_credits" and e.details:
            hint = f" (balance {e.details.get('balance')} credits, cost {e.details.get('cost')}; top up at {BASE}/billing)"
        elif e.code == "content_unavailable":
            hint = " (private, removed or login-gated; permanent, do not retry)"
        elif e.code == "unsupported_url":
            hint = " (channel/playlist pages are not extractable; use a single post URL)"
        elif e.code == "unauthorized":
            hint = f" (check POSTREEF_API_KEY; keys live at {BASE}/developers/api-keys)"
        print(json.dumps({"error": {"status": e.status, "code": e.code, "message": e.message, "details": e.details}}))
        log(f"error: {e}{hint}")
        return 1
    except urllib.error.URLError as e:
        reason = str(e.reason)
        hint = ""
        if "CERTIFICATE_VERIFY_FAILED" in reason:
            hint = " (your Python has no CA bundle: `pip install certifi`, or on macOS python.org builds run 'Install Certificates.command')"
        print(json.dumps({"error": {"status": 0, "code": "network_error", "message": reason}}))
        log(f"error: could not reach {BASE}: {reason}{hint}")
        return 2
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
