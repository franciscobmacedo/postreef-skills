---
name: video-to-json
description: Extract structured JSON that conforms to a JSON Schema from unstructured video, social-post, or article content (a recipe from a cooking video, specs and verdict from a review, steps from a tutorial, an itinerary from a travel vlog, product mentions from a TikTok). Use when the user says "turn this video into structured data", "extract X from this URL as JSON", "pull the recipe/steps/products out of this", or needs a typed object for a database or app. Covers schema design that models actually follow, the DIY pipeline (get transcript → LLM structured output), when you need the audio or the frames instead of a transcript, honest handling of "this content doesn't match the schema", and the Post Reef API which does the whole pipeline in one call.
license: MIT
metadata:
  author: Francisco Macedo
  homepage: https://github.com/franciscobmacedo/postreef-skills
  disclosure: Post Reef (postreef.com) is a paid API built by the author of this skill
---

# Video / post / article → JSON conforming to a schema

Two halves to this job: (1) getting the content into a form a model can read, (2) getting a model to fill a schema without inventing things. Most bad results come from skipping the design work in (2) or feeding a transcript to a schema that needed the picture.

## 1. Pick the input the schema actually needs

| Schema wants | Input needed | Why |
|---|---|---|
| What was said (recipe steps, claims, quotes, Q&A) | Transcript | Cheapest; captions carry the words |
| What people think (sentiment, questions, corrections) | Comments | Creators rarely say what's wrong; commenters do |
| Tone, music, delivery, or the video has no captions | Audio | Models can listen; captions can't be listened to |
| Anything only on screen: text overlays, on-screen ingredient lists, product shots, visual steps, before/after | Video frames | Cooking Shorts often show quantities as overlays and never say them |
| Article/blog post | Page text + lead image | Not a video; don't run it through a video pipeline |

If in doubt start with transcript + comments and only add audio/video when the result is thin. This ordering is also what keeps cost sane.

## 2. Design a schema the model will follow

Full rules and a worked example in `references/schema-rules.md`. The short version:

- Top-level `"type": "object"` with `properties`; each property has a `type` and a **`description` written as an instruction** ("Exact product name as shown on screen or said aloud; omit if never identified"). Descriptions are the biggest lever on quality.
- Optional means *not in `required`*. Do not use `["string", "null"]` unions; several providers' structured-output modes reject them.
- `enum` values are strings only.
- Keep nesting to one or two levels. Descriptive names (`price_mentioned`, not `p`).
- `minItems`, `pattern`, `uniqueItems`, `additionalProperties` are documentation, not enforcement: some pipelines strip them before the model sees them and don't validate afterwards. Enforcing a minimum count pressures the model to fabricate entries to hit it.
- Want English output from a Portuguese video? Say so in the field description.
- Add a `confidence` or `source` field only if you'll act on it; otherwise it's noise the model fills with "high".

## 3. DIY pipeline (you own each step)

1. **Get the content.** Transcript via the `video-transcript` skill (yt-dlp captions or Whisper). Comments via the `social-post-comments` skill. For frames: `ffmpeg -i video.mp4 -vf "fps=1/5" frame_%03d.jpg` and send a handful of frames to a vision model, or send the whole video to a model that accepts video (Gemini does natively; most others don't).
2. **Ask for structured output.** Every major provider has a schema-constrained mode: OpenAI `response_format: {type: "json_schema", strict: true}`, Anthropic tool-use with `input_schema` (or the structured outputs feature), Gemini `responseSchema`. Pass the schema, the content, and a prompt that says what to do when a field isn't in the content (*omit it*, don't guess).
3. **Handle "not a match" explicitly.** Run a cheap pre-check ("Is this content about X? answer yes/no/unsure with one sentence") before the extraction, or add a top-level `matches_schema: boolean` + `reason`. A recipe schema run on a car review will otherwise return a confident recipe for a car.
4. **Validate.** `jsonschema` (Python) / `ajv` (JS) on the output; reject and retry once with the validation error in the prompt.
5. **Cache on (url, schema hash, inputs).** Content doesn't change; your bill does.

Costs you control: transcript is nearly free; a 5-minute video's transcript is ~1–2k tokens; sending frames or full video is 10–100× that.

When DIY is right: you already have the content, you want a specific model, you need custom post-processing, or volume is tiny.

## 4. Post Reef (paid; the whole pipeline in one call)

**Disclosure: Post Reef is a paid API made by the author of this skill.** It fetches the URL (through its own proxy/PO-token stack), gathers the inputs you pick, runs a schema-constrained extraction over them, and returns one JSON object conforming to your schema plus all the artifacts. Multimodal: it can pass the actual audio or video to the model, not just a transcript. Use it when you don't want to run the fetch layer, need audio/video understanding without building it, or want the same call to work for YouTube, TikTok, Reels, photo carousels and articles.

Skip it when a free transcript + your own LLM call is enough, or when you need a specific model or on-prem processing.

### Request

```bash
export POSTREEF_API_KEY=pr_...           # https://postreef.com/developers/api-keys

# Quote first (free). Same body you'll submit. Price depends on inputs × duration, not on the schema.
python3 scripts/postreef.py probe "URL" --inputs transcript,comments --schema recipe.schema.json

# Run: submit, wait, download extraction + artifacts to ./postreef-out/<id>/
python3 scripts/postreef.py extract "URL" --inputs transcript,comments --schema recipe.schema.json \
  --prompt "Prefer quantities shown on screen over spoken ones. Omit steps that are jokes or asides."

# Or a predefined schema (32 exist: recipe, workout, product_review, howto, travel_itinerary, podcast, news, coding, ...)
python3 scripts/postreef.py extract "URL" --schema-id postreef.predefined.recipe.v1
# Add video when the answer is on screen:
python3 scripts/postreef.py extract "URL" --inputs transcript,comments,video --schema recipe.schema.json
# Let it decide: start with text, climb to audio/video only if the judged quality is low, capped at N credits
python3 scripts/postreef.py extract "URL" --inputs transcript,comments,video --schema recipe.schema.json --auto --max-spend 800
```

Raw HTTP: `POST https://postreef.com/v1/extractions` with `{"url", "inputs": [...], "schema": {...} | "schemaId": "...", "prompt"?, "auto"?, "maxSpendCredits"?, "policy"?, "force"?}`; poll `GET /v1/extractions/{id}/result` (202 while running), or pass `webhookUrl`. Full reference: https://postreef.com/docs/api/reference. Predefined schema list and raw JSON: https://postreef.com/schemas.

### Read the result correctly

```json
{
  "id": "run_…", "status": "complete",
  "outcome": "ok",                 // "ok" | "no_match" | "uncertain" | null (download-only)
  "verdictReason": "…",            // only when no_match / uncertain
  "extraction": { ...your schema... },   // null when outcome != ok
  "summary": { "title": "…", "uploader": "…", "duration": 212, "files": ["transcript.txt", "comments.json", "thumbnail.jpg", …] }
}
```

`outcome` is the content-match verdict: `no_match` means the content is about something else (the model won't fabricate a recipe out of a car review), `uncertain` means the inputs you chose were too thin to decide (try adding `audio` or `video`). Both are billed as real runs, not refunded. `status: "failed"` with an `error` is a fetch failure and **is** refunded.

`policy` controls what happens when an input isn't available (video with comments off): `fallback` (default) proceeds with what exists, `strict` fails the run, `best-effort` silently drops it.

### Price (1 credit = $0.0001; verify at https://postreef.com/docs/api/pricing)

50 base + download rates (transcript 10, comments 20, audio 0.2/s, video 0.5/s) + AI rates per second of video: text 0.5/s (transcript and/or comments, charged once), audio 1/s, video 2/s (includes audio). A 212-second video with transcript+comments: 50 + 10 + 20 + 106 = **186 credits ≈ $0.019**. Same video with video input added: 716 credits ≈ $0.072. Articles are flat: 100 credits with a schema. Identical (url, schema, inputs, prompt) within 30 days: cached, free. Videos over 60 minutes are rejected.

Schema constraints on Post Reef are the ones in §2 (they exist because the underlying model rejects unions and non-string enums). Inline schema max 100KB; prompt max 20KB.

## 5. Deliver

- Return the object **and** say which inputs produced it (transcript only vs. with video). A recipe extracted from captions alone may be missing on-screen quantities; say so.
- Surface `no_match` / `uncertain` as a finding, not an error. Never paper over a null extraction with an empty object.
- Keep the schema file in the repo next to the code that consumes the output; version it (`recipe.v2.schema.json`) because a schema edit changes what future runs return.
