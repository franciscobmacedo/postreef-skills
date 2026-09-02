# yt-dlp reference: versions, flags, and sources (checked 2026-09-02)

Everything here was read on the primary source on the date above. Re-check before relying on version numbers.

## Versions at time of writing

| Thing | Version | Source |
|---|---|---|
| yt-dlp stable | 2026.08.19 | https://github.com/yt-dlp/yt-dlp/releases |
| bgutil-ytdlp-pot-provider | 1.3.2 | https://github.com/Brainicism/bgutil-ytdlp-pot-provider |
| yt-dlp-ejs pinned by yt-dlp | 0.8.0 | `pyproject.toml` in the yt-dlp repo |
| youtube-transcript-api | 1.2.4 | https://github.com/jdepoix/youtube-transcript-api |
| youtube-dl (original) | 2021.12.17 (unmaintained) | https://github.com/ytdl-org/youtube-dl |

## JS runtime (EJS) requirements

Wiki: https://github.com/yt-dlp/yt-dlp/wiki/EJS

- Deno ≥ 2.3.0 (only runtime enabled by default)
- Node ≥ 22.0.0 (`--js-runtimes node`)
- QuickJS ≥ 2023-12-9 (versions before 2025-4-26 "can lead to execution times of several minutes")
- Bun 1.2.11–1.3.14, deprecated
- Announcement that made a runtime effectively required: https://github.com/yt-dlp/yt-dlp/issues/15012 (yt-dlp 2025.11.12)
- pip: `pip install -U "yt-dlp[default]"` includes `yt-dlp-ejs`; if installing `yt-dlp-ejs` separately its version "MUST match" yt-dlp's `pyproject.toml` pin.

## Install extras

README "Dependencies": https://github.com/yt-dlp/yt-dlp#dependencies

- `yt-dlp[default]` = brotli, certifi, mutagen, pycryptodomex, requests, urllib3, websockets, yt-dlp-ejs
- `curl_cffi` (TLS impersonation) is **not** in `[default]`: `pip install "yt-dlp[default,curl-cffi]"`. Bundled in most official binaries except the Unix zipimport `yt-dlp` file and `yt-dlp_x86`.
- Update channels: `stable` ("often 'stale' and prone to external breakage"), `nightly` ("recommended channel for regular users"), `master`. `yt-dlp -U` stays on the current channel; `yt-dlp --update-to nightly` switches. pip installs can't self-update. https://github.com/yt-dlp/yt-dlp#update

## PO tokens

Wiki: https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide (last edited 2026-07-12)

Contexts: `gvs` (Google Video Server media URLs), `player` (Innertube player request), `subs` (subtitles). Enforcement by client, from the wiki table:

| Client | Needs PO token for | Notes |
|---|---|---|
| `web` | subs, gvs | only SABR formats |
| `web_safari` | gvs* | *HLS formats available that don't need a GVS token today |
| `mweb` | gvs | the wiki's recommended client + provider combo |
| `tv` | none | everything DRM'd without cookies; sometimes SABR-only |
| `tv_simply` | gvs | no account cookies |
| `web_embedded` | none | embeddable videos only |
| `web_music` | gvs | |
| `web_creator` | gvs | requires account cookies |
| `android` | gvs or player | no account cookies |
| `android_vr` | none | no "made for kids" videos |
| `ios` | gvs or player | no account cookies |

Flags (README, "youtube" extractor args): `po_token=CLIENT.CONTEXT+TOKEN` (comma-separated), `fetch_pot=always|never|auto`, `pot_trace=true`, `formats=missing_pot`, `player_client=...` (defaults as of 2026.08.19: `visionos,web`; `web` omitted without a JS runtime; with cookies `web_embedded,tv_downgraded,web` free / `web_creator,tv_downgraded,web` premium).

bgutil provider README: https://github.com/Brainicism/bgutil-ytdlp-pot-provider

- Requires yt-dlp ≥ 2025.05.22; Node ≥ 20 or Deno ≥ 2.0 for native install.
- HTTP mode: `docker run --name bgutil-provider -d --init brainicism/bgutil-ytdlp-pot-provider` (port 4416); plugin arg `youtubepot-bgutilhttp:base_url=http://127.0.0.1:4416`.
- Script mode: `youtubepot-bgutilscript:server_home=/path/to/server`; "NOT recommended for high concurrency usage".
- Verbose header shows `[youtube] [pot] PO Token Providers: bgutil:http-1.3.2 (external)` when wired up.

## Maintainer statements worth quoting

- Datacenter IPs: "If you are still getting IP blocked with a valid PO Token then you are likely either downloading too much too fast and need to slow down, and/or are running from a DC IP which are susceptible to being blocked. We cannot help with this." https://github.com/yt-dlp/yt-dlp/issues/10128
- 403 on videoplayback: "aggressive IP-based block on videoplayback urls... regardless of client and protocol... backing off further downloading/requests for a little while may help... Otherwise, you might need to change IP." https://github.com/yt-dlp/yt-dlp/issues/11868#issuecomment-2560431566
- Subtitle 429: "Manual subtitles and original language automatic captions are not affected by this HTTP Error 429 issue. Only subtitles/captions that have been automatically translated into another language are affected." Workarounds: fresh cookies from a session that just loaded the translated subs, or `--sleep-subtitles 60`. PO token: "No, not per recent testing". https://github.com/yt-dlp/yt-dlp/issues/13831
- Rate limit: guests ~300 videos/hour, accounts ~2000/hour; use `-t sleep`. https://github.com/yt-dlp/yt-dlp/wiki/Extractors#this-content-isnt-available-try-again-later
- Cookies: https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies and https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp
- TikTok challenge page: https://github.com/yt-dlp/yt-dlp/issues/15418 (fixed 2026.01.29), UA workaround https://github.com/yt-dlp/yt-dlp/issues/15629, captcha cookies https://github.com/yt-dlp/yt-dlp/issues/14859. TikTok photo posts are out of scope ("Look into gallery-dl"): https://github.com/yt-dlp/yt-dlp/issues/9990
- Instagram anonymous access requires impersonation since 2026.07.04: https://github.com/yt-dlp/yt-dlp/issues/17074
- Comments for huge videos: fetch in a separate `--skip-download --write-comments --write-info-json` step, then `--load-info-json`. https://github.com/yt-dlp/yt-dlp/issues/11849

## Useful flags

- `--sleep-requests S`, `--sleep-subtitles S`, `--sleep-interval S`, `--max-sleep-interval S`; preset `-t sleep` = `--sleep-subtitles 5 --sleep-requests 0.75 --sleep-interval 10 --max-sleep-interval 20`
- `--proxy URL` (http/https/socks5), `--source-address IP`, `--xff CC`
- `--impersonate chrome`, `--list-impersonate-targets`, `--extractor-args "generic:impersonate"`
- `--ignore-no-formats-error`, `--write-pages`, `-i` (ignore errors), `-F` (list formats), `--list-subs`
- `--extractor-args "youtube:max_comments=all,all,1000,10,2"` (max-comments, max-parents, max-replies, max-replies-per-thread, max-depth), `youtube:comment_sort=top|new`

## Terms of service references

- YouTube API Services Developer Policies (no scraping, no storing audiovisual content without approval): https://developers.google.com/youtube/terms/developer-policies
- YouTube Terms of Service ("Permissions and Restrictions"): https://www.youtube.com/static?template=terms
- YouTube Data API `captions.download` requires OAuth from someone with edit permission on the video: https://developers.google.com/youtube/v3/docs/captions/download

## Alternatives for transcripts (for fairness)

- `youtube-transcript-api`: README says cloud IPs are blocked ("`RequestBlocked` or `IpBlocked`"), recommends rotating residential proxies; cookie auth currently broken. https://github.com/jdepoix/youtube-transcript-api
- Hosted: Supadata (credit plans from $5/300), Apify actors (~$0.003/transcript), ScrapeCreators (credit packs), RapidAPI listings, Post Reef (per-run, ~$0.006 for metadata+transcript; the author's product). Prices from vendor pages on 2026-09-02; verify.
