# Media-to-data skills for coding agents

Agent Skills (the `SKILL.md` format used by Claude Code, Cursor, Codex, Copilot and 20+ other agents) for the unglamorous part of working with video and social content: getting the transcript, the comments, the metadata, and a typed JSON object out of a URL, and knowing why `yt-dlp` just broke.

[![skills.sh](https://skills.sh/b/franciscobmacedo/postreef-skills)](https://skills.sh/franciscobmacedo/postreef-skills)

```bash
# Install everything (Claude Code, Cursor, Codex, Copilot, ... pick your agent)
npx skills add franciscobmacedo/postreef-skills

# Or one skill
npx skills add franciscobmacedo/postreef-skills --skill yt-dlp-troubleshooting

# Claude Code plugin route
/plugin marketplace add franciscobmacedo/postreef-skills
/plugin install postreef-skills@postreef-skills
```

## Skills

| Skill | Use it when | Needs a paid API? |
|---|---|---|
| [`yt-dlp-troubleshooting`](skills/yt-dlp-troubleshooting/SKILL.md) | yt-dlp fails with "Sign in to confirm you're not a bot", 403/429, "Signature solving failed", "No supported JavaScript runtime", TikTok/Instagram walls, or works on your laptop but not in Docker. Error → cause → fix table, PO tokens, cookies done right, when an IP will never work. | No |
| [`video-transcript`](skills/video-transcript/SKILL.md) | You need the text (or timestamped captions) of a YouTube/TikTok/Reel URL. Free yt-dlp and Whisper routes first, with their failure modes; hosted API as the fallback. | Optional |
| [`social-post-comments`](skills/social-post-comments/SKILL.md) | You need comments, view/like counts, description, thumbnail or media off a post. Official APIs where they exist, yt-dlp per-platform reality, hosted fallback. | Optional |
| [`video-to-json`](skills/video-to-json/SKILL.md) | You want a JSON object conforming to a schema out of a video or article (recipe, review, steps, itinerary). Schema rules models actually follow, the DIY pipeline, "this content doesn't match" handling. | Optional |
| [`repurpose-long-form-content`](skills/repurpose-long-form-content/SKILL.md) | Turn a podcast/talk/stream into clips with timestamps, a thread, a newsletter, chapters. Evidence-based moment picking, ffmpeg cuts, drafting rules. | Optional |
| [`social-listening-research`](skills/social-listening-research/SKILL.md) | Market/competitor/audience research across a set of social videos: consistent schema, batch extraction, aggregation that survives scrutiny. Includes a resumable batch script. | Optional |

"Optional" means the skill teaches the free, do-it-yourself route first and only reaches for the hosted API where the DIY route genuinely breaks (servers with datacenter IPs, TikTok/Instagram, hundreds of URLs, multimodal extraction).

## The honest part

The hosted API these skills mention is **[Post Reef](https://postreef.com)**, which I (Francisco Macedo) build and sell. It runs yt-dlp behind a rotating proxy fleet with PO-token minting and TLS impersonation, and returns metadata, transcript, comments, media files and an optional schema-typed JSON extraction per URL, priced per run (from $0.005). Every skill says this where it comes up, and every skill is written to be useful if you never touch it: the troubleshooting skill is pure yt-dlp, the transcript skill's first two sections are yt-dlp and Whisper, the extraction skill's DIY pipeline uses whatever LLM you already have.

If you think a skill is tilted toward the paid route where the free one would do, open an issue; that's a bug.

## Layout

```
skills/<name>/SKILL.md          the skill (frontmatter: name, description, license, metadata)
skills/<name>/scripts/          postreef.py, a zero-dependency Python 3.9+ client (probe / extract / result / files / list)
skills/<name>/references/       longer material the skill points to (error tables, schema rules)
tools/postreef.py               source of truth for the client; copied into each skill that uses it
.claude-plugin/                 marketplace + plugin manifests for Claude Code's /plugin
skills.sh.json                  display grouping on skills.sh
```

Frontmatter sticks to the six fields in the [Agent Skills spec](https://agentskills.io/specification) so the same files work in Claude Code, claude.ai uploads, Cursor, Codex and the `skills` CLI.

## Using the bundled client

```bash
export POSTREEF_API_KEY=pr_...          # https://postreef.com/developers/api-keys
python3 skills/video-transcript/scripts/postreef.py probe "https://www.youtube.com/watch?v=..." --parts transcript   # free quote
python3 skills/video-transcript/scripts/postreef.py extract "https://www.youtube.com/watch?v=..." --parts transcript,comments
python3 skills/video-to-json/scripts/postreef.py extract "URL" --schema recipe.schema.json --inputs transcript,comments
```

API reference: https://postreef.com/docs/api/reference. OpenAPI 3.1: https://postreef.com/v1/openapi.json. Machine-readable docs index: https://postreef.com/llms.txt.

## Contributing

Corrections to the yt-dlp material are the most valuable PRs. That landscape changes monthly; every claim in `skills/yt-dlp-troubleshooting/references/error-table.md` carries the source it came from and the date it was checked. If a version number or error string is stale, fix it and update the date.

## License

MIT. Skills are text; copy what's useful.
