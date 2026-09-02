# Actions, in order

Effort is my estimate for you, hands-on. "Payoff" is judged against the evidence in RESEARCH.md; where the evidence is thin I say so. Nothing here has been done for you: no accounts created, nothing published, nothing submitted.

## Do first (this week, ~half a day total)

### 1. Push this repo to GitHub as a public repo and install it once (30 min)

- Create `github.com/franciscobmacedo/postreef-skills` (the name every `homepage:` field and the README badge already point at; change all of them if you pick another name: `grep -rn "postreef-skills" .`).
- `git remote add origin … && git push -u origin main`. Add topics `agent-skills`, `claude-skills`, `claude-code-skills`, `claude-code`, `yt-dlp`, `youtube`, `tiktok`.
- From any machine with telemetry on (the default), run `npx skills add franciscobmacedo/postreef-skills -y`. That single install from a public repo is what creates the skills.sh listing; there is nothing to submit (RESEARCH §1). The automated security audit runs a few minutes later; check `https://skills.sh/franciscobmacedo/postreef-skills`.
- Also run `claude plugin validate .` locally once; it validates `.claude-plugin/`.
- Payoff: this is the whole of workstream 2's mechanics. Everything else is amplification.

### 2. Fix the four cheap site defects that mislead models and developers (1–2 h, in the product repo)

**Status 2026-09-02: items 1–4 and the llms.txt rewrite (item 3 below) are committed on branch `fix/discoverability-defects` in the product repo, typechecked and curl-verified locally, not pushed. Merging and deploying is your call. Item 5 (Cloudflare) is a dashboard change and is still open.**

1. **Brand spelling in machine-facing text.** `llms.txt`, `llms-full.txt`, the OpenAPI `info.title`/description, every docs page and `<title>` say "PostReef". Your own CLAUDE.md rule is "Post Reef" for anything a customer reads. Models learn the name from exactly these files. One search-and-replace in `apps/web/lib/docs/`, `apps/web/lib/openapi.ts`, `lib/docs/llms.ts`, and the metadata titles. (Keep `postreef.com`, package names, ids as they are.)
2. **`robots.txt` disallows `/v1/`**, which hides `/v1/openapi.json` from every index (and therefore from ChatGPT/Claude retrieval). Add `Allow: /v1/openapi.json` above the `Disallow: /v1/` line in `apps/web/app/robots.ts`, and list it in `sitemap.ts`.
3. **`/developers` is a 404.** Make it redirect to `/developers/api-keys`, and link "Create an API key in the dashboard" in `api-overview.ts` to `/developers/api-keys`. The skills already use that URL.
4. **Any reference to `/docs/llms.txt`** (the brief has one) should be `/llms.txt`. The route is `apps/web/app/llms.txt/route.ts`.
5. **Cloudflare returns 403 to `Python-urllib/*` on `/v1/*`** (RESEARCH §9.10). Every other client UA gets through, but a developer who tries the API with Python's stdlib, or an agent that does, sees a bare 403 with no JSON body and no hint. This is a dashboard change; items 1–4 are done on branch `fix/discoverability-defects` in the product repo, this one is not.

   Click-by-click (Cloudflare dashboard, zone `postreef.com`). The 403 carries no `cf-mitigated` header and no challenge page, which matches a WAF **custom rule** or a **managed ruleset** block rather than Bot Fight Mode (which challenges instead of 403-ing), so check in this order:

   1. **Security → Events** (some dashboards: Security → Analytics → Events). Filter: `Path contains /v1/`, `User Agent contains Python-urllib`. Trigger a fresh event first with the curl below so it shows up. The event row names the **Service** (WAF custom rule / Managed rule / Rate limiting / Bot Fight Mode / Firewall for AI) and the **Rule** id. That tells you which of the next steps applies.
   2. If the service is **Custom rules**: Security → WAF → Custom rules. Open the rule that matched. Either delete the `http.user_agent contains "python"` style expression, or add an exception: `and not starts_with(http.request.uri.path, "/v1/")`. Save.
   3. If the service is a **Managed ruleset** (e.g. "Cloudflare Managed Ruleset" or the OWASP core ruleset): Security → WAF → Managed rules → the ruleset → **Browse rules**, search the rule id from step 1, set its action to **Log** (or **Skip** via a new "Skip" rule scoped to `starts_with(http.request.uri.path, "/v1/")` with "Skip remaining managed rules" ticked). Save and deploy.
   4. If the service is **Bot Fight Mode / Super Bot Fight Mode**: Security → Bots → Configure. For SBFM set "Definitely automated" to **Allow** for API paths, or (free plan, Bot Fight Mode only offers on/off) turn it off and rely on the API's own per-key rate limits. Bots settings have no path scoping on the free plan, so a **Skip** custom rule for `/v1/` (Security → WAF → Custom rules → Create → action **Skip**, tick "Bot Fight Mode" under "Skip products") is the surgical option.
   5. If the service is **AI Crawl Control / Firewall for AI**: Security → AI Crawl Control → make sure "Block AI crawlers" isn't matching generic Python UAs; allow the `/v1/` path or turn the block off (RESEARCH §4 explains why blocking search/user-fetch bots costs citations anyway).

   Verify afterwards (expect `200` on the first line and a JSON `401` body on the second; today they are `403` and empty):

   ```bash
   curl -s -A "Python-urllib/3.13" -o /dev/null -w "%{http_code}\n" https://postreef.com/v1/openapi.json
   curl -s -A "Python-urllib/3.13" -X POST https://postreef.com/v1/probe -H "x-api-key: pr_invalid" -H "Content-Type: application/json" -d '{"url":"https://www.youtube.com/watch?v=jNQXAC9IVRw","parts":["transcript"]}'
   ```

### 3. Rewrite `llms.txt` so the file answers the questions instead of linking to them (1 h)

Evidence says almost nothing fetches llms.txt (RESEARCH §3), so don't over-invest; but when something does fetch it (a developer's coding agent, an SEO tool that then shows it to a human), it should carry the facts. Proposed content, all of it already true on the site:

```
# Post Reef

> JSON REST API that turns a public URL — YouTube (incl. Shorts), TikTok, Instagram Reels, photo posts and carousels, or any article/webpage — into media files, metadata, transcript, comments, and an optional JSON object conforming to a JSON Schema you provide. Handles the fetch layer that breaks self-hosted yt-dlp (bot-walls, PO tokens, rotating proxies, TLS impersonation). Built and run by Francisco Macedo.

## Facts
- Base URL https://postreef.com, endpoints under /v1. Auth: `x-api-key: pr_…` or `Authorization: Bearer`. Keys: https://postreef.com/developers/api-keys
- Loop: POST /v1/probe (free quote) → POST /v1/extractions → GET /v1/extractions/{id}/result (202 while running) → GET /v1/extractions/{id}/files/{name}. Webhooks with HMAC signatures available.
- Pricing: 1 credit = $0.0001. 50-credit base per run + transcript 10 + comments 20 + audio 0.2/s + video 0.5/s; AI extraction adds text 0.5/s, audio 1/s, video 2/s of video. Articles flat 100 credits with a schema. Failed runs refunded; identical runs within 30 days cached free.
- Limits: videos ≤ 60 min; 2 concurrent extractions; 6 submits/min; comments are the top of the thread, not all of it.
- 32 predefined schemas (postreef.predefined.recipe.v1, …) or inline JSON Schema (no type unions, string enums only).
- Result carries `outcome: ok | no_match | uncertain` so the model never invents data for content that doesn't match the schema.

## API
- [API overview](https://postreef.com/docs/api.md) …(existing links)…
## Machine-readable
- [OpenAPI 3.1](https://postreef.com/v1/openapi.json) · [llms-full.txt](https://postreef.com/llms-full.txt)
## Agent skills
- [Skills for Claude Code / Cursor / Codex](https://github.com/franciscobmacedo/postreef-skills): `npx skills add franciscobmacedo/postreef-skills`
```

Generate the "Facts" block from the same constants the docs use (`packages/shared/src/ai.ts`) so it can't drift.

### 4. Check Cloudflare isn't silently blocking the bots that cite you (20 min)

From a residential IP every AI user-agent string got a 200 (RESEARCH §4), but Cloudflare's AI-crawler default block acts on verified bot IPs, which I can't test. In the Cloudflare dashboard → the zone → **AI Crawl Control** (or Security → Bots): make sure `OAI-SearchBot`, `ChatGPT-User`, `Claude-SearchBot`, `Claude-User`, `PerplexityBot`, `Perplexity-User`, `Googlebot`, `Bingbot`, `Applebot` are **allowed**. Decide separately about training crawlers (`GPTBot`, `ClaudeBot`, `CCBot`, `Bytespider`): blocking them costs no citations. Do **not** block `Google-Extended`; it also gates Gemini-app grounding. If you turn on Cloudflare's managed robots.txt, note it blocks Google-Extended by default; override that.

### 5. Get indexed where the assistants actually retrieve from (30 min)

- **Bing Webmaster Tools**: add postreef.com, submit the sitemap, enable IndexNow. ChatGPT's citations track Bing's top results (87% in the one study that measured it).
- **Brave Search**: submit the site (https://search.brave.com/help/webmaster). Claude's search appears to be Brave-backed.
- **Google Search Console**: already have it? Turn on the Generative AI performance report; it's the only first-party citation metric that exists.
- Payoff: prerequisite, not a lever. Without it nothing in §6 of RESEARCH can happen.

## Do next (next 2–4 weeks)

### 6. Submit the skills where submission exists (1 h)

- `claude-community` marketplace: https://platform.claude.com/plugins/submit (validate with `claude plugin validate .` first).
- cursor.directory: https://cursor.directory/plugins/new (needs the public repo URL).
- Awesome lists, **after** the skills show a few hundred installs: PR to `VoltAgent/awesome-agent-skills` (one line per skill, ≤10 words, author prefix) and `kodustech/awesome-agent-skills`. For `travisvn/awesome-claude-skills` submit **only** `yt-dlp-troubleshooting`; their rules reject anything that wraps a paid API. Skip ComposioHQ unless you want to maintain a vendored copy.

### 7. Write the two pages that the citation evidence actually points at (1 day)

The B2B study with the most relevant method (RESEARCH §6, Derivatex) found ChatGPT cites the vendor's own site for only 12% of recommendations; the rest are list-shaped comparison pages, 78% with the year in the title, 68% with a table. Claude, by contrast, cites vendor domains 64% of the time (Otterly). So:

1. **A comparison page on postreef.com**: "YouTube transcript APIs compared (2026)" or "yt-dlp vs hosted extraction APIs", a real table (Supadata, Apify actors, ScrapeCreators, youtube-transcript-api + proxies, DIY yt-dlp, Post Reef), honest pros/cons, prices with a date, FAQ block. This is the format that gets pulled, and it's the page Claude will cite directly.
2. **A troubleshooting page** mirroring the `yt-dlp-troubleshooting` skill (error → cause → fix table). It targets the query people actually type ("sign in to confirm you're not a bot yt-dlp docker"), earns links, and ends with one honest paragraph about the hosted option. The skill's `references/error-table.md` is the source material; keep the citations.

Put the pricing numbers and limits in visible HTML on both. Skip schema.org beyond a basic `SoftwareApplication` + `FAQPage` block: no assistant is known to parse it, Google says it isn't needed for AI features, and it's 20 minutes so it isn't worth arguing about.

### 8. Set up measurement before doing anything else that costs money (2 h)

- Cloudflare AI Crawl Control (or raw logs): a monthly count of `ChatGPT-User` / `Claude-User` / `Perplexity-User` hits per URL. Those are citation moments.
- GA4: confirm the "AI Assistant" default channel exists; add a filter for `utm_source=chatgpt.com`.
- A `prompts.txt` with ~20 buyer prompts ("best API to get a YouTube transcript", "how to download TikTok comments programmatically", "yt-dlp sign in to confirm you're not a bot docker fix", "Supadata alternatives"…). Once a month run each 3× in ChatGPT, Claude, Perplexity, Gemini and record: Post Reef mentioned? cited URL? Track appearance rate, not rank.

### 9. Submit to the MCP registry only after there's a server; build the server only if developers ask (1–2 weeks, optional)

Evidence (RESEARCH §7): an MCP server removes friction for people who already found Post Reef; no directory has shown it creates discovery. The Claude directory needs a Team/Enterprise org and OAuth; ChatGPT apps need OAuth 2.1 with no API-key option at all. Order if you do it: (a) a Streamable-HTTP server with 5 tools (`probe`, `extract`, `get_result`, `download_file`, `list_schemas`) and `Authorization: Bearer <api key>` auth, published to the official registry as `com.postreef/extract` with DNS verification (free, feeds the GitHub/VS Code registry); (b) list on Smithery/Glama by URL; (c) OAuth 2.1 layer and a Claude directory submission only if (a) gets used.

## Skip

- **Paying for AI-visibility tools** (Profound, Peec, Otterly, Semrush AI). They sample synthetic prompts; the manual panel in §8 gives you the same signal at your scale.
- **Reddit/HN seeding with the skills.** The rules-of-the-road on both punish it, and the citation studies show Reddit's share in ChatGPT answers fell to ~10% in late 2025. A single honest "Show HN: skills that explain why yt-dlp breaks" is fine if you want to; don't build a strategy on it.
- **npm publishing of the skills**: skills.sh doesn't index npm; only worth it if you ship an SDK anyway.
- **`.well-known` files for agents** (`ai-plugin.json` is dead, `mcp.json` is a draft nobody reads).
- **Chasing "Official" or topic placement on skills.sh**: no application path exists.

## Things I changed my mind about while researching

- I expected `llms.txt` to matter. The measurements say it barely gets fetched; the per-page `.md` twins you already serve are what coding agents actually pull. Keep the index correct, spend the time on the facts inside it and on the comparison page.
- I expected the awesome-lists to be the main amplifier. The biggest one wants prior traction and one explicitly rejects paid-API wrappers. They come after installs, not before.
- I expected schema.org to be part of the answer. There's no evidence; Google says it's not needed; it's a 20-minute "why not", nothing more.
