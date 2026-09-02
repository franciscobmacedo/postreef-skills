---
name: repurpose-long-form-content
description: "Turn a long video, podcast episode, talk, or livestream into short-form assets: clip candidates with timestamps, a newsletter issue, a thread, chapter markers, pull quotes, or a blog post. Use when the user says \"repurpose this\", \"make clips from this video\", \"turn this podcast into a newsletter/thread/post\", \"find the best moments\", or \"chapters for this video\". Covers getting a timestamped transcript first (the step everyone skips), choosing moments with evidence instead of vibes, cutting clips with ffmpeg, and the drafting rules that keep the output in the creator's voice."
license: MIT
metadata:
  author: Francisco Macedo
  homepage: https://github.com/franciscobmacedo/postreef-skills
  disclosure: Post Reef (postreef.com), mentioned in the sourcing section, is a paid API built by the author of this skill
---

# Repurpose long-form content

Repurposing is a sourcing problem before it is a writing problem. A thread written from a vague memory of the video is generic; one written from a timestamped transcript with the exact lines quoted is specific. Get the material first.

## 1. Get the material (transcript with timestamps, plus comments)

You need three things: a **timestamped** transcript (SRT/VTT, or Whisper output), the **metadata** (title, description, chapters if the creator wrote them), and ideally the **comments** (what the audience already found quotable; the top comments are free editorial judgment).

- Local file (a recording the user owns): `whisper episode.mp3 --model small --output_format srt,txt` (or faster-whisper). Add `--word_timestamps True` if you'll cut tight clips.
- Public URL: use the `video-transcript` skill. Ask for the caption *file*, not just flattened text. yt-dlp: `--write-subs --write-auto-subs --sub-langs "en.*,en" --skip-download`. Comments: `--write-comments` (see `social-post-comments`).
- On a server / many episodes / bot-walled IP: the Post Reef API returns `transcript.txt`, timestamped `.srt` subtitle files, `comments.json` and metadata in one call (`--parts transcript,comments`; ~$0.008 per video; **paid, by the author of this skill**). If you also want the "moments" picked in the same call, give it a schema (§2 has one) with `--inputs transcript,comments`; that adds an AI charge per second of video. Videos over 60 minutes are rejected there; split long podcasts or use Whisper locally.

Keep the SRT. Clip timing comes from it; don't throw away the only source of time.

## 2. Find the moments with evidence

Don't ask a model "what are the best moments". Ask it for a typed list you can check against the transcript:

```json
{
  "type": "object",
  "properties": {
    "moments": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "start": {"type": "string", "description": "HH:MM:SS where the self-contained moment begins (a sentence boundary, not mid-word)."},
          "end": {"type": "string", "description": "HH:MM:SS where it ends. 20–75 seconds for vertical clips; up to 3 minutes for a newsletter excerpt."},
          "hook": {"type": "string", "description": "The first line a viewer hears, verbatim from the transcript."},
          "why": {"type": "string", "description": "One sentence: what makes this standalone (a claim, a story with a payoff, a contrarian take, a number, a how-to)."},
          "kind": {"type": "string", "enum": ["claim", "story", "howto", "contrarian", "number", "funny", "emotional"]},
          "audience_signal": {"type": "string", "description": "Quote a comment that reacts to this moment, if any. Omit if none."}
        },
        "required": ["start", "end", "hook", "why", "kind"]
      },
      "description": "8–15 candidates ranked best first. Every timestamp must exist in the transcript."
    },
    "chapters": {"type": "array", "items": {"type": "object", "properties": {"start": {"type": "string"}, "title": {"type": "string", "description": "≤ 6 words, no clickbait"}}, "required": ["start", "title"]}},
    "one_line_summary": {"type": "string", "description": "What this episode is about, in the creator's register, ≤ 25 words."}
  },
  "required": ["moments", "chapters", "one_line_summary"]
}
```

Feed it the SRT (timestamps included) and the comments. Then **verify every `hook` string actually appears in the transcript** near `start`; drop any that don't. This one check removes most hallucinated moments.

Heuristics that hold up: moments that start with a claim or a number outperform ones that start with context; a story needs its payoff inside the clip; a "contrarian" take needs the reasoning inside the clip or it reads as rage-bait; comments that quote a line back are the strongest signal you have.

## 3. Cut the clips

```bash
# Re-encode so cuts are frame-accurate (stream copy snaps to keyframes and drifts by seconds)
ffmpeg -ss 00:12:41 -to 00:13:29 -i episode.mp4 -c:v libx264 -preset fast -crf 20 -c:a aac clip01.mp4

# Vertical 9:16 with a centered crop (for talking-head; for two-up layouts you need real editing)
ffmpeg -ss 00:12:41 -to 00:13:29 -i episode.mp4 -vf "crop=ih*9/16:ih,scale=1080:1920" -c:a aac clip01_vertical.mp4

# Burn captions from the SRT slice (extract the slice with the same timing first)
ffmpeg -i clip01.mp4 -vf "subtitles=clip01.srt:force_style='FontSize=18,Outline=1'" clip01_captioned.mp4
```

Add 0.5–1s of lead-in before the hook line so the first word isn't clipped. Name files by timestamp so they trace back.

## 4. Draft the written formats

Rules that keep it from sounding like every other repurposed post:

- **Quote, don't paraphrase, for the anchor line.** One verbatim line from the transcript per section; the rest can be your words.
- **Keep the creator's register.** Read 200 words of their description/transcript before drafting. If they say "y'all", don't write "individuals".
- **One idea per unit.** One tweet = one claim. One newsletter section = one moment from §2.
- **Cite timestamps** in the newsletter and blog post (`[12:41]`), linked to `?t=761` on YouTube. Readers click; creators love it.
- **Don't invent takeaways the creator didn't make.** If the model's "key lesson" isn't in the transcript, cut it.
- Thread: hook tweet is the best `hook` from §2 with its number/claim, then 5–8 tweets each anchored to a moment, last tweet links the source.
- Newsletter: `one_line_summary` as the subhead, 3–5 moments as sections with a quote + your 2-sentence gloss + timestamp, a "what the comments said" box if you have comments.
- Chapters: paste `chapters` as `MM:SS Title` lines into the description; YouTube requires the first at `0:00` and at least three, ≥10s apart.

## 5. Deliver

Hand over: `moments.json` (verified), the clip files, the drafts, and a one-paragraph note saying what source you worked from (manual captions / auto-captions / Whisper; comments fetched or not). If any moment was dropped in verification, say how many. If the transcript was auto-captions, warn that names and numbers in quotes need a listen before publishing.
