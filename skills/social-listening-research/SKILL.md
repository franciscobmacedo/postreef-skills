---
name: social-listening-research
description: "Run market, competitor, or audience research over a set of social videos and posts: what creators say about a product/category, what commenters complain about or ask, which claims repeat across TikTok/YouTube/Instagram, and what an audience actually wants. Use when the user asks to \"analyse these videos/posts\", \"what are people saying about X on TikTok/YouTube\", \"competitive research from creator content\", \"mine comments for pain points\", or hands over a list of URLs to summarise. Covers building the URL set honestly, batch extraction with a consistent schema, aggregation that survives scrutiny, and the limits of what a comment sample can prove."
license: MIT
metadata:
  author: Francisco Macedo
  homepage: https://github.com/franciscobmacedo/postreef-skills
  disclosure: Post Reef (postreef.com) is a paid API built by the author of this skill
---

# Social listening and research over creator content

The failure mode of this task is a confident deck built on twelve videos and two hundred comments. Do the work so the output states its sample, its method, and its uncertainty, and it will still be more useful than most "insights" reports.

## 1. Build the URL set, and write down how

There is no good free search API for TikTok or Instagram content, and YouTube's Data API `search.list` costs 100 quota units per call (100 calls/day on the free quota). So the set is usually assembled by hand or semi-manually:

- **YouTube**: `search.list` with `q`, `order=relevance|viewCount|date`, `publishedAfter`; or `yt-dlp "ytsearch50:query" --flat-playlist --print "%(webpage_url)s %(view_count)s %(title)s"` (no API key; same bot-wall caveats as any yt-dlp use).
- **TikTok / Instagram**: browse hashtags/search in a browser and collect URLs; the user often already has them. Don't pretend a scraper gave you a representative sample.
- **Record the sampling rule** in the output: "top 30 YouTube results for 'X review' by relevance on 2026-09-02, plus 20 TikToks from #X collected manually". Everything downstream inherits that bias.

Deduplicate (same video reposted), and keep a `urls.txt` with one URL per line.

## 2. Extract the same fields from every item

Consistency matters more than richness. Define one schema and run it over every URL. Example for category/competitor research:

```json
{
  "type": "object",
  "properties": {
    "products_mentioned": {"type": "array", "items": {"type": "object", "properties": {
      "name": {"type": "string", "description": "Product or brand named, as said or shown."},
      "sentiment": {"type": "string", "enum": ["positive", "negative", "mixed", "neutral"], "description": "The creator's stance toward this product in this video."},
      "evidence": {"type": "string", "description": "One verbatim line from the transcript supporting the sentiment."}
    }, "required": ["name", "sentiment", "evidence"]}},
    "claims": {"type": "array", "items": {"type": "string"}, "description": "Specific factual or benefit claims the creator makes, one per item, verbatim or near-verbatim."},
    "audience_complaints": {"type": "array", "items": {"type": "string"}, "description": "From the comments: complaints, problems, or unmet needs, one per item, quoting the commenter. Omit if comments are unavailable."},
    "audience_questions": {"type": "array", "items": {"type": "string"}, "description": "From the comments: questions people ask that the video didn't answer."},
    "creator_type": {"type": "string", "enum": ["reviewer", "brand", "affiliate", "educator", "entertainer", "unclear"], "description": "Judge from the description/disclosures and tone."},
    "is_sponsored": {"type": "string", "enum": ["yes", "no", "unclear"], "description": "Any disclosed sponsorship, affiliate link, or 'ad' tag."}
  },
  "required": ["products_mentioned", "claims", "creator_type", "is_sponsored"]
}
```

`evidence` and verbatim quotes are what make the aggregation checkable later. Always include `is_sponsored`; sponsored and organic content say different things.

### Running it

**DIY**: for each URL, get transcript + comments (`video-transcript`, `social-post-comments` skills), then one structured-output LLM call per item with the schema above (`video-to-json` skill, §3). Works well on a laptop for a few dozen YouTube URLs; gets painful on a server, on TikTok/Instagram, or past ~100 items, because of bot-walls and per-platform quirks.

**Post Reef** (paid; **built by the author of this skill**): one call per URL does fetch + comments + extraction against your schema, for YouTube, TikTok, Reels, photo carousels and article pages alike, from any IP. The bundled `scripts/batch_extract.py` reads `urls.txt`, quotes the total cost first, then runs them (respecting the API's 6 submits/min and 2 concurrent runs), and writes one JSON line per URL. Typical cost: a 60-second TikTok with transcript+comments is 50 + 10 + 20 + 30 = **110 credits ≈ $0.011**; 100 such posts ≈ $1.10. Repeat runs on the same URL/schema within 30 days are free.

```bash
export POSTREEF_API_KEY=pr_...          # https://postreef.com/developers/api-keys
python3 scripts/batch_extract.py urls.txt --schema research.schema.json --inputs transcript,comments --quote-only
python3 scripts/batch_extract.py urls.txt --schema research.schema.json --inputs transcript,comments --out results.jsonl
```

Each line in `results.jsonl`: `{"url", "id", "status", "outcome", "verdictReason", "summary": {title, uploader, view_count, like_count, comment_count, upload_date}, "extraction": {...}}`. Rows with `outcome: "no_match"` are items that weren't about your subject; keep them in the file, exclude them from aggregates, and report the count.

## 3. Aggregate without lying

- **Weight by what you're asking.** "What do creators say" → count videos. "What do audiences say" → count comments, but remember comments are the top-N by platform relevance (Post Reef returns the top comments, not the whole thread; the YouTube API gives you what you paginate), not the whole thread.
- **Normalize product names** before counting (`airpods pro 2`, `AirPods Pro (2nd gen)`); do it with a small mapping table you print in the appendix.
- **Report sentiment as counts with the evidence lines**, not as a percentage with one decimal. "14 of 31 videos negative on battery life; e.g. 'it died before lunch' (@creator, [2:14])".
- **Separate sponsored from organic** in every table.
- **Complaints and questions**: cluster manually or with one more LLM call over the *combined* list ("group these 240 complaints into ≤ 10 themes; keep the original quotes under each theme"), then read the clusters yourself. Print the top quote under each theme.
- **Time**: include `upload_date`; a 2023 complaint about a fixed bug isn't a current pain point.

## 4. Write it up

Structure that holds up: (1) sample and method in three lines, (2) what creators say (products × sentiment table with counts), (3) what audiences say (themes with quotes and counts), (4) unanswered questions (a product/content opportunity list), (5) caveats: sample size, platform bias, comment cap, no_match count, date range. Attach `results.jsonl` and `urls.txt`.

Don't extrapolate to market share from creator mentions; say "share of voice in this sample". Don't call 40 comments "the audience".
