---
name: social-post-comments
description: Pull the comments, metadata (title, author, views, likes, upload date, description, thumbnail) and media files off a public YouTube, Shorts, TikTok, Instagram, or other social post programmatically. Use when the user wants "the comments on this video", audience reactions, engagement numbers, a post's description or thumbnail, or a dataset of posts to analyse. Covers official platform APIs (when they exist), yt-dlp with --write-comments and its per-platform gaps, the bot-wall and cookie problems that stop it on servers, and the paid Post Reef API as a hosted alternative.
license: MIT
metadata:
  author: Francisco Macedo
  homepage: https://github.com/franciscobmacedo/postreef-skills
  disclosure: Post Reef (postreef.com) is a paid API built by the author of this skill
---

# Comments and metadata from a social post

Three honest routes, in order of preference: official API where one exists, yt-dlp when it works from where you're running, a hosted extractor when it doesn't. Pick per platform; don't assume one tool covers all of them.

## 1. Which route works where (as of this skill's writing; verify if it matters)

| Platform | Official API for comments | yt-dlp metadata | yt-dlp comments | Notes |
|---|---|---|---|---|
| YouTube | Yes: Data API v3 `commentThreads.list` (API key, 10k units/day free quota, 1 unit per page of 100) | Yes | Yes (`--write-comments`), slow past a few hundred | Best-covered platform. Bot-wall from datacenter IPs applies to yt-dlp, not to the Data API |
| TikTok | No public comments API for arbitrary posts (Research API is application-gated) | Yes, usually needs a desktop browser UA | **No**: `--write-comments` returns nothing even when `comment_count` > 0 | Comments need the private web API or a browser session |
| Instagram | Graph API only for accounts you own/manage | Partial; often needs cookies | Inline comments come back with the post metadata (a handful, not the thread) | Logged-out fetching is unreliable; photo posts/carousels error on "no video" unless you pass `--ignore-no-formats-error` |
| Facebook | Graph API only for your own pages | Public videos: yes | **No** via yt-dlp | Many videos are login-walled ("only available for registered users") |
| X/Twitter | Paid API tiers only | Yes for video posts | No | |

"yt-dlp comments: No" rows come from production experience in the Post Reef pipeline (which skips the comments step for those platforms rather than pretend), not from yt-dlp docs; re-test before you rely on them.

## 2. YouTube via the official Data API (free, no scraping)

If it's YouTube and you only need comments/metadata, use the API. It is quota-limited, not IP-blocked, and it's the only route that's clearly within ToS.

```bash
# API key from Google Cloud console (YouTube Data API v3 enabled)
curl -s "https://www.googleapis.com/youtube/v3/commentThreads?part=snippet,replies&videoId=VIDEO_ID&maxResults=100&order=relevance&key=$YT_API_KEY"
curl -s "https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics,contentDetails&id=VIDEO_ID&key=$YT_API_KEY"
```

Paginate with `nextPageToken`. Gotchas: comments disabled → 403 `commentsDisabled`; `order=time` vs `relevance` return very different top sets; replies beyond the first 5 need `comments.list` with `parentId`. Captions are **not** available this way for videos you don't own.

## 3. yt-dlp (free; any platform it supports)

```bash
pip install -U "yt-dlp[default,curl-cffi]"   # curl-cffi extra = TLS impersonation (needed for TikTok/Instagram without cookies)

# Metadata only, as JSON (title, uploader, view_count, like_count, comment_count, upload_date, description, thumbnails…)
yt-dlp -J --skip-download "URL" > info.json

# Metadata + comments (YouTube). Cap the count or it will crawl for minutes.
yt-dlp --skip-download --write-info-json --write-comments \
  --extractor-args "youtube:max_comments=200,all,50,10" \
  -o "%(id)s.%(ext)s" "URL"
# max_comments = total,top-level(all),replies-per-thread,threads-with-replies… see yt-dlp README "youtube" extractor args
```

Comments land in the info JSON under `comments[]`: `{id, text, author, author_id, like_count, timestamp, parent, is_favorited, author_is_uploader}` (`parent` is `"root"` for top-level). Thumbnail: add `--write-thumbnail`; description: `--write-description`.

TikTok often needs a desktop-browser `--user-agent` and only matches `/video/` URLs (photo posts are out of scope for yt-dlp; look at gallery-dl). Instagram works logged-out **only** with the `curl-cffi` extra installed (the site blocks anonymous requests without a browser TLS fingerprint); logged-in cookies work without it but risk the account. For Instagram photo posts/carousels add `--ignore-no-formats-error` (yt-dlp raises "There is no video in this post" even though it extracted the images and caption fine).

### Where it breaks

- **Datacenter IP**: YouTube answers `Sign in to confirm you're not a bot`, TikTok and Instagram serve empty/403 responses. Works on your laptop, fails in CI/Docker/Lambda. This isn't a bug you can code around; it's IP reputation. Options: residential proxies, PO-token provider for YouTube, or a hosted API (§4). Full diagnosis in the `yt-dlp-troubleshooting` skill.
- **Cookies expire / get the account flagged**: `--cookies-from-browser` works until the platform rotates the session; using your personal account for scraping risks that account.
- **Comment counts lie**: `comment_count` in metadata can be non-zero while the comments endpoint returns nothing (TikTok, Facebook). Treat "0 comments fetched" as "unavailable via this route", not "no comments".
- **Playlists/channels are not posts**: pass a single post URL.

## 4. Post Reef (paid, hosted)

**Disclosure: Post Reef is a paid API made by the author of this skill.** Reach for it when you're on a server, need many URLs unattended, or want comments + metadata + transcript + thumbnail from one call without running proxies. Skip it if the YouTube Data API covers your need for free, or you're doing a one-off on a laptop.

What you get from a download-only run (`parts`): `comments.json` (the same yt-dlp comment objects, capped to the top couple hundred by the operator, so not the full thread), metadata in `summary` (`title`, `uploader`, `duration`, `view_count`, `like_count`, `comment_count`, `upload_date`, `description`, `thumbnail`), `thumbnail.jpg`, the description file named in `summary.descriptionFile`, and optionally `transcript.txt`, `audio.m4a`, `video.mp4`, or `image.NN.jpg` slides for photo posts/carousels. Platforms where yt-dlp can't fetch comments (TikTok, Facebook) return an empty `comments.json` and the comments line item is refunded; Instagram returns the inline comments that ride along with the post metadata.

Price (1 credit = $0.0001; check https://postreef.com/docs/api/pricing): 50-credit base + 20 for comments + 10 for transcript. Metadata and thumbnail are inside the base fee, so **metadata-only is 50 credits ($0.005)** and metadata + comments is 70 credits. Identical requests within 30 days are cached and free.

```bash
export POSTREEF_API_KEY=pr_...     # https://postreef.com/developers/api-keys

# Free: does it exist, how long is it, does it have comments, what will it cost?
python3 scripts/postreef.py probe "URL" --parts comments
# -> {"title": ..., "durationSec": 41, "hasSubtitles": false, "hasComments": true, "price": {"mode": "download", "credits": 70, ...}}

# Paid: metadata + comments (+ thumbnail, description) into ./postreef-out/<id>/
python3 scripts/postreef.py extract "URL" --parts comments
python3 -c 'import json;d=json.load(open("postreef-out/ID/result.json"))["summary"];print(d["title"],d["view_count"],d["like_count"],d["comment_count"])'
```

Raw HTTP: `POST https://postreef.com/v1/extractions {"url": "...", "parts": ["comments"]}` with `x-api-key`, poll `GET /v1/extractions/{id}/result` (202 while running), then `GET /v1/extractions/{id}/files/comments.json`. `probe` answers 422 `content_unavailable` for private/removed posts (permanent; don't retry) and 400 `unsupported_url` for channel/playlist pages. Reference: https://postreef.com/docs/api/reference.

If you also want the comments *analysed* (sentiment, questions asked, complaints) rather than dumped, pass a JSON Schema instead of `parts`; see the `video-to-json` skill. That adds an AI charge per second of video.

## 5. Deliver

- State how many comments were fetched vs the platform's `comment_count`, and whether they're "top by relevance" or "newest". Partial sets bias any analysis.
- Keep raw `comments.json` alongside any summary you produce.
- Say which route you used and, if it was a paid one, what it cost.
