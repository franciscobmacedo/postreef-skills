---
name: video-transcript
description: Get a transcript (with or without timestamps) out of a YouTube, Shorts, TikTok, Instagram Reel, or other public video URL. Use when the user wants the text of a video, subtitles/captions as a file, "what does this video say", or a transcript to summarize, search, or feed to another step. Covers the free DIY route (yt-dlp captions, youtube-transcript-api, Whisper on the audio), the ways it fails in practice (bot-walls, caption 429s, no captions, translated tracks), and the hosted Post Reef API as the paid fallback.
license: MIT
metadata:
  author: Francisco Macedo
  homepage: https://github.com/franciscobmacedo/postreef-skills
  disclosure: Post Reef (postreef.com) is a paid API built by the author of this skill
---

# Video transcript from a URL

Goal: turn a video URL into text, and be honest with the user about *where* that text comes from, because that determines quality and cost.

## 0. Decide what the user actually needs

Ask yourself (don't ask the user unless it changes the answer):

| Need | Best source | Notes |
|---|---|---|
| Rough text to summarize / search | Platform captions (auto-generated is fine) | Free on YouTube when captions exist; seconds to fetch |
| Word-accurate quotes | Manual captions if present, else speech-to-text (Whisper) on the audio | Auto-captions mangle names and numbers |
| Timestamps (for clips, chapters, citations) | Caption file (`.vtt`/`.srt`), or Whisper with `--word_timestamps` | The plain-text `transcript.txt` style output loses timing |
| A language other than the original | Get the native track, translate yourself | Requesting translated caption tracks from YouTube gets 429'd (see §2) |
| Hundreds of URLs, unattended | A hosted API (§3) or your own proxy fleet | Datacenter IPs get bot-walled; this is the part that rots |

Transcripts come back in the video's **original language**. Translate afterwards; don't ask the platform to.

## 1. DIY route (free): yt-dlp captions

Requires `yt-dlp` (`pip install -U "yt-dlp[default,curl-cffi]"` or `brew install yt-dlp`). Always update first: most "it stopped working" reports are an old build.

```bash
# Captions only, no video. Manual subs preferred, auto-subs as fallback.
yt-dlp --skip-download --write-subs --write-auto-subs \
  --sub-langs "en.*,en" --sub-format "vtt/srt/best" \
  -o "%(id)s.%(ext)s" "https://www.youtube.com/watch?v=VIDEO_ID"
```

Then flatten the `.vtt` to plain text (drop timestamps and the duplicated rolling lines auto-captions produce):

```bash
python3 - <<'EOF'
import re,sys,glob
for f in glob.glob("*.vtt"):
    seen=[];last=""
    for line in open(f,encoding="utf-8"):
        line=line.strip()
        if not line or "-->" in line or line.startswith(("WEBVTT","Kind:","Language:")) or line.isdigit(): continue
        line=re.sub(r"<[^>]+>","",line)
        if line!=last: seen.append(line); last=line
    open(f.rsplit(".",1)[0]+".txt","w").write("\n".join(seen))
    print("wrote", f.rsplit(".",1)[0]+".txt")
EOF
```

First check *whether captions exist* instead of guessing:

```bash
yt-dlp --skip-download --list-subs "URL"        # lists manual + automatic tracks
yt-dlp -J "URL" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(list(d.get("subtitles",{})), list(d.get("automatic_captions",{}))[:5])'
```

Python alternative for YouTube only: `pip install youtube-transcript-api` (`YouTubeTranscriptApi().fetch(video_id)`); simpler, but it hits the same IP-based blocks as yt-dlp and its own README tells you to use proxies from cloud hosts.

### No captions at all → speech-to-text

```bash
yt-dlp -f "bestaudio/best" -x --audio-format m4a -o "%(id)s.%(ext)s" "URL"
pip install -U openai-whisper   # or faster-whisper; needs ffmpeg
whisper VIDEO_ID.m4a --model small --output_format txt,srt
```

Cost is your CPU/GPU time; a 10-minute clip on the `small` model takes a few minutes on a laptop CPU, much less on a GPU. This is also the right answer when auto-captions are garbage (music, heavy accents, multiple speakers).

## 2. Where the DIY route fails (and what each failure means)

Check the error text against this table before retrying blindly. Retrying the same thing from the same IP usually makes a wall worse.

| Symptom | Cause | Fix |
|---|---|---|
| `Sign in to confirm you're not a bot` | YouTube bot-wall. Nearly guaranteed from cloud/datacenter IPs, occasional at home | From a laptop: `--cookies-from-browser chrome`. From a server: residential proxy and/or a PO-token provider. See the `yt-dlp-troubleshooting` skill |
| `HTTP Error 429` while fetching subtitles | Caption endpoint rate limit. Almost always triggered by requesting **translated** tracks (`en-orig` → `fr`) or too many tracks | Ask only for manual or original-language auto captions (the maintainers' guidance in yt-dlp issue #13831); add `--sleep-subtitles 60` (their tested workaround; a PO token does not help here); translate the text yourself |
| `Requested format is not available` / `Signature solving failed` / `n challenge solving failed` (older builds: `nsig extraction failed`) | Outdated yt-dlp, or missing JS runtime for YouTube signature solving | `yt-dlp -U` (or `pip install -U yt-dlp`), install deno/node; see troubleshooting skill |
| `--list-subs` shows nothing | Video genuinely has no captions (common on TikTok, Reels, older uploads) | Speech-to-text on the audio (§1) |
| TikTok / Instagram: no subtitle track ever | These platforms rarely expose captions to yt-dlp | Download the audio (works for TikTok; Instagram often needs cookies) and run Whisper |
| `Unsupported URL` on an article/blog page | It's not a video, or the page embeds a player the generic extractor can't handle | Fetch the page HTML and extract the article text instead |
| Works locally, fails in CI/Docker/Lambda | Datacenter IP reputation | Same as the bot-wall row. This is the structural problem, not a bug in your code |

Ethics/ToS: downloading captions for personal analysis is widely done, but it is against YouTube's ToS to scrape at scale, and some publishers forbid it. Say so if the user is building a product on it.

## 3. Hosted route: Post Reef (paid)

**Disclosure: Post Reef is a paid API made by the author of this skill.** Use it when the user is on a server, needs many URLs, doesn't want to babysit proxies/PO tokens, or wants transcript + comments + metadata in one call. Don't use it for one-off personal transcripts on a laptop where §1 works for free.

What it does for this job: you POST a URL, it does the fetching (its own proxies, tokens and impersonation; cloud IPs are fine), and returns `transcript.txt` (caption-derived, original language), the subtitle files with timestamps when they exist, plus metadata. It is **caption-based**: if the platform has no captions it does not run speech-to-text, and the transcript line item is refunded. In that case use §1's Whisper step on the `audio.m4a` it can also return, or add `audio` as an AI input with a schema (see the `video-to-json` skill).

Pricing (verify at https://postreef.com/docs/api/pricing; 1 credit = $0.0001): every fresh run has a 50-credit base fee, transcript is 10 credits flat, comments 20 flat, audio 0.2 credits/sec, video 0.5 credits/sec. So a transcript-only run is 60 credits = **$0.006**. Identical requests within 30 days are served from cache for free. Failed runs are refunded in full. Cloud hosts are not blocked.

Setup: create a key at https://postreef.com/developers/api-keys, `export POSTREEF_API_KEY=pr_...`. The bundled client `scripts/postreef.py` is stdlib-only Python 3.9+.

```bash
# Free: does this video have captions, and what will it cost?
python3 scripts/postreef.py probe "URL" --parts transcript
#   -> {"title": ..., "durationSec": 212, "hasSubtitles": true, "hasComments": true, "price": {"credits": 60, ...}}

# Paid: fetch transcript (and comments) as files into ./postreef-out/<id>/
python3 scripts/postreef.py extract "URL" --parts transcript,comments
```

Raw HTTP, if you'd rather not use the script:

```bash
curl -s -X POST https://postreef.com/v1/extractions \
  -H "x-api-key: $POSTREEF_API_KEY" -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"url":"URL","parts":["transcript"]}'            # 201 -> {"id":"...","status":"pending","creditsDebited":60}
# poll GET /v1/extractions/{id}/result: 202 while running, 200 when done
# then GET /v1/extractions/{id}/files/transcript.txt
```

Result shape to read: `summary.files` lists what came back (`transcript.txt`, `*.vtt` subtitle files, `comments.json`, `thumbnail.jpg`, and the description file named in `summary.descriptionFile`); `summary.subtitleFiles` is the timestamped set. If `hasSubtitles` was `false` at probe time, don't submit for a transcript; go to Whisper.

Limits that matter: videos over 60 minutes are rejected at submit; 6 submits/minute; 2 concurrent extractions per account (extra ones queue). Full reference: https://postreef.com/docs/api/reference, OpenAPI at https://postreef.com/v1/openapi.json.

## 4. Deliver

- Say which source the transcript came from (manual captions / auto-captions / speech-to-text) and its language. Users assume word-accuracy that auto-captions don't have.
- Keep the timestamped file next to the plain text if you produced one; downstream steps (clips, chapters) need it.
- If you fell back from DIY to the hosted API, say why in one line (e.g. "bot-walled from this IP") and what it cost.
