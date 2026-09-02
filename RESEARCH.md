# Research: skills.sh mechanics and LLM discoverability for Post Reef

Date of research: 2026-09-02. Every claim carries one of three tags:

- **CONFIRMED**: read on a primary source (official docs, the CLI's source code, a study with disclosed methodology), or directly tested against postreef.com.
- **REPORTED**: a credible secondary source or a single-site measurement.
- **UNCONFIRMED / FOLKLORE**: could not verify, or vendor marketing with no data.

Sections: 1 skills.sh · 2 other skill/plugin distribution surfaces · 3 llms.txt · 4 robots.txt and AI crawlers · 5 structured data and machine-readable endpoints · 6 what assistants actually cite · 7 MCP as a channel · 8 measurement · 9 Post Reef-specific audit findings.

---

## 1. How skills.sh works

**What it is.** A directory and leaderboard for Agent Skills, run by Vercel ("Made with love by Vercel"; CLI repo `vercel-labs/skills`, MIT, ~30k stars). Skills are installed with `npx skills add <owner/repo>` into 20+ agents (Claude Code, Cursor, Codex, Copilot, Gemini CLI, Windsurf...). CONFIRMED: https://skills.sh, https://github.com/vercel-labs/skills, https://vercel.com/changelog/introducing-skills-the-open-agent-skills-ecosystem

**There is no submission form and no registry PR. Listing happens through install telemetry.** CONFIRMED, verbatim from the FAQ: "How do I get my skill listed on the leaderboard? → Skills appear on the leaderboard automatically through anonymous telemetry." https://www.skills.sh/docs/faq. Vercel's KB guide: "There's no special publish command for skills.sh." https://vercel.com/kb/guide/agent-skills-creating-installing-and-sharing-reusable-agent-context

**The precise trigger** (CONFIRMED from the CLI source): telemetry is sent only when the GitHub API reports the repo as public (`isRepoPrivate()` in `src/source-parser.ts`; `src/add.ts`: "Only send telemetry if repo is public... If we can't determine (null), err on the side of caution and skip telemetry"). So the first listing requires **at least one telemetry-enabled `npx skills add` from a public GitHub repo**. Telemetry endpoint `https://add-skill.vercel.sh/t`; opt-out `DISABLE_TELEMETRY=1` / `DO_NOT_TRACK=1`. https://github.com/vercel-labs/skills/blob/main/src/telemetry.ts. Security audits "are generated automatically after a skill is installed for the first time — there may be a delay of a few minutes." https://www.skills.sh/docs/api

**Required layout.** CONFIRMED (CLI README "Skill Discovery"): the CLI walks `skills/<name>/SKILL.md`, `skills/<category>/<name>/SKILL.md`, repo-root `SKILL.md`, `.claude/skills/`, `.agents/skills/`, and 30+ agent-specific directories, up to three levels deep. No manifest is required. An optional `skills.sh.json` at the repo root only changes display grouping on the repo's skills.sh page ("does not change how the skills CLI installs skills"). https://github.com/vercel-labs/skills#skill-discovery, https://www.skills.sh/docs/customize

**Frontmatter.** CONFIRMED from the Agent Skills spec (https://agentskills.io/specification): required `name` (≤64 chars, lowercase letters/digits/hyphens, no leading/trailing/double hyphens, must match the directory name) and `description` (≤1024 chars, non-empty); optional `license`, `compatibility` (≤500 chars), `metadata` (string→string map), `allowed-tools` (experimental). Keep `SKILL.md` under 500 lines. Claude Code accepts many extra fields (`when_to_use`, `argument-hint`, `context`, `model`...) but claude.ai uploads and the Skills API **reject** anything outside the six spec fields with "Unexpected key(s) in SKILL.md frontmatter". https://code.claude.com/docs/en/skills. **Consequence: stick to the six fields.** This repo does.

**Ranking.** CONFIRMED: install counts are aggregated CLI telemetry events; views are all-time, trending ("recent growth"), and hot (last hour vs same hour yesterday). Skill pages show all-time installs, first-seen date, per-agent breakdown. `isDuplicate: true` marks detected forks. https://www.skills.sh/docs/api. UNCONFIRMED: whether repeat installs by the same machine are deduplicated. Leaderboard top at time of research: find-skills 3.2M, grill-me 1.0M, frontend-design 845K, agent-browser 773K.

**Featured / Official / topics.** CONFIRMED that an "Official" section exists ("skills from the companies and organizations that build the technology") and topic pages exist (React, Next.js, Design & UI, Databases, Testing, Marketing...). COULD NOT CONFIRM any way to apply for Official status, request topic assignment, or get featured; there is no tag field in the spec and the topic pages look hand-curated. https://www.skills.sh/official, https://www.skills.sh/topic/react

**Review and content rules.** CONFIRMED: no editorial review and no anti-promotional rule in any skills.sh doc. Automated security scans (Gen Agent Trust Hub, Socket, Snyk) flag malicious content; flagged skills are hidden from leaderboard and search. https://www.skills.sh/docs, https://vercel.com/changelog/automated-security-audits-now-available-for-skills-sh. Dispute process: COULD NOT CONFIRM.

**What popular listings look like** (CONFIRMED by reading the repos): `mattpocock/skills`, `anthropics/skills`, `vercel-labs/agent-skills`, `obra/superpowers`, `getsentry/skills` all use `skills/<name>/SKILL.md` (sometimes with a category level), ship a `.claude-plugin/marketplace.json` so the same repo installs via `/plugin marketplace add`, have a README with a skill table of one-line "what + when" descriptions and the `npx skills add` command, and use MIT/Apache. `vercel-labs/agent-skills` adds `scripts/` and `references/` per skill and a `skills.sh.json`. This repo follows that pattern.

**Badge**: `[![skills.sh](https://skills.sh/b/owner/repo)](https://skills.sh/owner/repo)`. CONFIRMED https://www.skills.sh/docs

---

## 2. Other distribution surfaces for skills

| Surface | Mechanics | Worth it? |
|---|---|---|
| **Claude Code plugin marketplace (own repo)** | Add `.claude-plugin/marketplace.json` (`name`, `owner`, `plugins[{name, source}]`) and `.claude-plugin/plugin.json`; users run `/plugin marketplace add owner/repo` then `/plugin install`. CONFIRMED https://code.claude.com/docs/en/plugin-marketplaces | **Yes**, ~20 lines, done in this repo. |
| **`claude-community` marketplace** (`anthropics/claude-plugins-community`) | Submit at https://platform.claude.com/plugins/submit; `claude plugin validate` + automated safety screening; pinned to a commit SHA; catalog syncs nightly; users must add the marketplace manually. CONFIRMED https://code.claude.com/docs/en/plugins#submit-your-plugin-to-the-community-marketplace | **Yes**, one form. |
| **`claude-plugins-official`** | "inclusion is at Anthropic's discretion... There is no application process." CONFIRMED same page | Not obtainable by application. |
| **cursor.directory/plugins** | Web form (`cursor.directory/plugins/new`), auto-detects `skills/*/SKILL.md`, reviewed by a Cursor agent (safe/suspicious/malicious). CONFIRMED https://github.com/cursor/community-plugins | Yes if Cursor users matter; same layout, no code changes. |
| **VoltAgent/awesome-agent-skills** (33k stars) | PR adding one README line `- **[author/skill](url)** - ≤10-word description`; requires "real community usage" (brand-new skills rejected). CONFIRMED https://github.com/VoltAgent/awesome-agent-skills/blob/main/CONTRIBUTING.md | Yes, **after** the skills have installs. |
| **kodustech/awesome-agent-skills** | PR, category-based, entry format includes "Use when… Trigger with…". CONFIRMED https://github.com/kodustech/awesome-agent-skills | Yes. |
| **travisvn/awesome-claude-skills** | Explicitly rejects "Skills that merely wrap commercial APIs or require paid subscriptions" and "conversion funnels for paid products"; wants ~10+ stars. CONFIRMED https://github.com/travisvn/awesome-claude-skills/blob/main/CONTRIBUTING.md | Only `yt-dlp-troubleshooting` would qualify; submit that one alone. |
| **ComposioHQ/awesome-claude-skills** (74k stars) | Skills are vendored into the repo by PR; must be tested with examples. CONFIRMED https://github.com/ComposioHQ/awesome-claude-skills/blob/master/CONTRIBUTING.md | Maybe, for the troubleshooting skill; vendoring means a copy to keep in sync. |
| **GitHub topics** | Add `agent-skills` (20.6k repos), `claude-skills` (7.8k), `claude-code-skills` (1.7k), `claude-code` (68k). CONFIRMED counts on github.com/topics | Free; low discovery value; do it. |
| **npm** | skills.sh does not index npm (CONFIRMED absence in the CLI). `antfu/skills-npm` proposal: ship `skills/<name>/SKILL.md` inside an npm package; consumers run `npx skills-npm`. REPORTED https://github.com/antfu/skills-npm/blob/main/PROPOSAL.md | Only if a Post Reef SDK is ever published to npm; then it's free to include. |
| **Aggregators** (agenticskills.io, lobehub.com/skills, mcpservers.org/agent-skills...) | Scrape skills.sh/GitHub. REPORTED | No action needed. |

---

## 3. `llms.txt`

**The spec** (CONFIRMED, https://llmstxt.org/): Markdown at `/llms.txt`, H1 + blockquote summary + H2 link lists to Markdown page versions. `llms-full.txt` is a docs-tooling convention (Mintlify: "combines your entire documentation site into a single file"), not part of the spec. https://www.mintlify.com/docs/ai/llmstxt

**Does any assistant consume it? No primary source says so.**

- Google's John Mueller, 2025-06-17: "FWIW no AI system currently uses llms.txt." REPORTED via https://www.seroundtable.com/google-ai-llms-txt-39607.html (original on Bluesky).
- Google Search Central, CONFIRMED: "You don't need to create new machine readable files, AI text files, or markup to appear in these features." https://developers.google.com/search/docs/appearance/ai-features
- OpenAI crawler docs never mention it (https://developers.openai.com/api/docs/bots). Anthropic publishes one for its own docs and its crawler doc doesn't mention reading others'. Perplexity's bot docs don't mention it. COULD NOT CONFIRM consumption by any of them.
- Measurements: Ahrefs (137,210 domains, May 2026 logs): 28% publish llms.txt, **97% of those files got zero requests**, and of requests that did occur only 1.1% were AI retrieval bots; SEO audit tools were the largest requester. REPORTED https://ahrefs.com/blog/llmstxt-study/. Evil Martians (single site, May–July 2026): ~660 fetches of llms.txt, only 37 from named AI assistants; separately **ChatGPT-User was 73% of all agent traffic** and Claude Code negotiated `Accept: text/markdown` 76% of the time. REPORTED https://evilmartians.com/chronicles/which-ai-actually-reads-your-site-two-months-of-llm-traffic-measured

**Verdict.** llms.txt is cheap, harmless, and there is no evidence it changes citations. The one real consumer is a developer pointing an agentic coding tool at your docs, which then fetches the Markdown. "llms.txt boosts AI visibility" is FOLKLORE. Keep it, don't invest in it. The Markdown-per-page endpoints (`/docs/*.md`) matter more than the index, because that's what Claude Code style agents actually fetch.

---

## 4. `robots.txt` and AI crawlers

CONFIRMED from each operator's own docs unless marked.

| User agent | Purpose (official) | What blocking it costs you | Source |
|---|---|---|---|
| `GPTBot` | Training crawl | Training only | https://developers.openai.com/api/docs/bots |
| `OAI-SearchBot` | ChatGPT search index | "Sites that are opted out of OAI-SearchBot will not be shown in ChatGPT search answers" | same |
| `ChatGPT-User` | User-initiated fetches | Live page reads during an answer; robots rules "may not apply" | same |
| `ClaudeBot` | Training crawl | Training only | https://support.claude.com/en/articles/8896518 |
| `Claude-User` | User-initiated fetches | "prevents our system from retrieving your content in response to a user query" | same |
| `Claude-SearchBot` | Search index | "prevents our system from indexing your content for search optimization" | same |
| `Google-Extended` | Gemini training **and** "Grounding in Gemini Apps" | Removes you from Gemini-app grounding/citations; no effect on Search or AI Overviews | https://developers.google.com/search/docs/crawling-indexing/google-common-crawlers |
| `Googlebot` | Search, incl. AI Overviews / AI Mode | Everything. Use `nosnippet`/`max-snippet` or the Search Console generative-AI toggle to leave AI features without leaving Search | https://developers.google.com/search/docs/appearance/ai-features |
| `PerplexityBot` | Perplexity search index; "not used to crawl content for AI foundation models" | Perplexity citations | https://docs.perplexity.ai/guides/bots |
| `Perplexity-User` | User-initiated fetches; "generally ignores robots.txt" | Live reads | same |
| `Bingbot` | Bing index, which grounds Copilot | No separate AI token; `NOARCHIVE` meta removes you from Bing Chat answers | https://blogs.bing.com/webmaster/september-2023/Announcing-new-options-for-webmasters-to-control-usage-of-their-content-in-Bing-Chat |
| `Applebot-Extended` | Apple training opt-out; "does not crawl webpages" | Training only | https://support.apple.com/en-us/119829 |
| `CCBot` | Common Crawl corpus (used for training datasets) | Training | https://commoncrawl.org/ccbot |
| `Amazonbot` | Amazon products, "may be used to train Amazon AI models" | Training + Alexa-type features | https://developer.amazon.com/amazonbot |
| `Meta-ExternalAgent` / `Meta-ExternalFetcher` | Training/indexing vs user-requested fetch ("may bypass robots.txt") | Training vs live reads | https://developers.facebook.com/docs/sharing/webmasters/web-crawlers/ |
| `Bytespider` | ByteDance; no official doc found | UNCONFIRMED | https://datadome.co/bots/bytespider/ (REPORTED) |

**Policy that follows from this for a product that wants to be cited:** allow every search-index and user-fetch agent (OAI-SearchBot, ChatGPT-User, Claude-SearchBot, Claude-User, PerplexityBot, Perplexity-User, Googlebot, Bingbot, Applebot, Meta-ExternalFetcher). Blocking training-only agents (GPTBot, ClaudeBot, CCBot, Bytespider, Applebot-Extended) is a values call with no citation cost, **except Google-Extended, which also controls Gemini-app grounding**: blocking it removes a citation surface.

**Cloudflare.** Post Reef is served through Cloudflare (Tunnel). Cloudflare's managed robots.txt, when enabled, prepends disallows for Amazonbot, Applebot-Extended, Bytespider, CCBot, ClaudeBot, Google-Extended, GPTBot, meta-externalagent plus a `Content-Signal: search=yes, ai-train=no` line; it does **not** block the search/user-fetch agents. CONFIRMED https://developers.cloudflare.com/bots/additional-configurations/managed-robots-txt/. Since 2025-07-01 new Cloudflare zones may **default to blocking AI crawlers at the WAF**, which is invisible in robots.txt. CONFIRMED that the default exists (https://blog.cloudflare.com/content-independence-day-no-ai-crawl-without-compensation/); COULD NOT CONFIRM from docs exactly which agents it covers. Google's own guidance: make sure crawling is allowed "by any CDN or hosting infrastructure". https://developers.google.com/search/docs/appearance/ai-features

**Tested on postreef.com (CONFIRMED, 2026-09-02):** requests with the user-agent strings of GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, Claude-User, Claude-SearchBot, PerplexityBot, Google-Extended, Googlebot, bingbot and CCBot all returned **200** on `/docs/api` with no `cf-mitigated` header, from a residential IP. That rules out a UA-based block but not an IP-verified-bot rule; the only way to be sure is the Cloudflare dashboard (AI Crawl Control / Bots) and the server logs. The live `robots.txt` contains only the app's rules (allow `/`, disallow account/billing/api/v1 paths); the Cloudflare managed block is **not** currently prepended, despite the comment in `apps/web/app/robots.ts` saying it is.

---

## 5. Structured data, OpenAPI, `.well-known`

- **Google**, CONFIRMED: "There's also no special schema.org structured data that you need to add" for AI Overviews/AI Mode; "Structured data isn't required for generative AI search." Standard structured data still helps ordinary rich results. https://developers.google.com/search/docs/appearance/ai-features, https://developers.google.com/search/docs/fundamentals/ai-optimization-guide
- **OpenAI, Anthropic, Perplexity**: no published statement on schema.org. COULD NOT CONFIRM. Claims like "ChatGPT values FAQPage schema" are FOLKLORE.
- One informal test (Mark Williams-Cook, 2026-02): ChatGPT and Perplexity pick up JSON-LD content as page text and don't care whether it validates. REPORTED https://www.seroundtable.com/chatgpt-perplexity-structured-data-text-40862.html
- **Implication:** `SoftwareApplication` / `WebAPI` / `FAQPage` JSON-LD is harmless, useful for Bing/Google rich results (which are the retrieval layers behind ChatGPT and AI Overviews), and there is no evidence any assistant parses it as a graph. The same facts in **visible HTML** (pricing numbers, endpoint list, limits) matter more. Post Reef's homepage currently has no JSON-LD (CONFIRMED by fetching it).
- `/.well-known/ai-plugin.json`: dead since OpenAI ended plugins (2024-04-09). REPORTED https://community.openai.com/t/error-plugins-are-no-longer-supported/715523. GPT Actions still consume an OpenAPI spec with API-key or OAuth auth. CONFIRMED https://developers.openai.com/api/docs/actions/authentication
- `/.well-known/mcp.json` "server cards": a draft SEP, not in the spec, no client support. CONFIRMED draft status https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2127. What is live for MCP is `/.well-known/oauth-protected-resource` (RFC 9728). CONFIRMED https://claude.com/docs/connectors/building/authentication
- "Agent Plugins 1.0.0" (2026-08-06, OpenAI/Amazon/Cursor/GitHub/Microsoft/Vercel): a packaging format (`plugin.json` + optional `skills/` + `mcp.json`), not a distribution channel. REPORTED https://thenextweb.com/news/openai-agent-plugins-open-standard-skills-mcp
- **OpenAPI at `/v1/openapi.json`** is the one machine-readable asset with a proven consumer: GPT Actions, Postman/Insomnia importers, codegen, and any agent a developer points at it. It is already public and unauthenticated on Post Reef (CONFIRMED). It is disallowed for crawlers by robots.txt (`Disallow: /v1/`), which also hides the spec from search indexes; see ACTIONS.

---

## 6. What assistants actually cite (and which index feeds them)

**Retrieval backends.**
- ChatGPT search "leverages third-party search providers" and "may share disassociated search queries with the Bing search engine". CONFIRMED (OpenAI help center) https://help.openai.com/en/articles/10093903. Seer Interactive (100 queries, 500+ citations, 2025-02): **87% of ChatGPT citations matched Bing's top organic results** vs 56% for Google. REPORTED https://www.seerinteractive.com/insights/87-percent-of-searchgpt-citations-match-bings-top-results. **Consequence: Bing indexing (Bing Webmaster Tools, IndexNow) is a prerequisite for ChatGPT citations.**
- Google AI Overviews / AI Mode / Gemini grounding: the Google index; the Gemini API's grounding tool exposes the fan-out queries. CONFIRMED https://ai.google.dev/gemini-api/docs/google-search
- Claude web search: Anthropic hasn't named its provider; Brave Search is on Anthropic's subprocessor list and a small Profound test found 87% overlap with Brave results. REPORTED https://www.tryprofound.com/blog/what-is-claude-web-search-explained. **Consequence: make sure Brave indexes the site** (it has its own crawler and a webmaster submission form).
- Copilot: Bing. CONFIRMED (Microsoft docs, §4).

**Citation studies with numbers** (all REPORTED; vendor-run, methodology disclosed):
- Profound, 680M citations (Aug 2024–Jun 2025): ChatGPT's top source Wikipedia 7.8%, Reddit 1.8%; Perplexity Reddit 6.6%; AI Overviews Reddit 2.2%, YouTube 1.9%. https://www.tryprofound.com/blog/ai-platform-citation-patterns
- Semrush, 230K prompts (Jul–Oct 2025): ChatGPT's Reddit share fell from ~60% of responses to ~10% after mid-Sept 2025. https://www.semrush.com/blog/most-cited-domains-ai/
- Ahrefs Brand Radar (3M+ US queries, updated 2026-09): AI Overviews mention share YouTube 22.9%, Reddit 18.5%, Facebook 10.1%; **no GitHub, Stack Overflow or vendor-docs domain in the top 50**. https://ahrefs.com/blog/most-cited-domains-ai-overviews/
- **Otterly, Claude only, 379K citations, SaaS/tech queries, June 2026: company/product domains are 64% of citations; community/forums 1.3%; Reddit 0.** The long tail is huge (top 10 domains = 9.5%). https://otterly.ai/blog/claude-ai-citation-study/ **This is the most relevant study for Post Reef: Claude cites vendor sites directly; ChatGPT and Perplexity don't.**
- Derivatex, B2B SaaS, ChatGPT with search (40 categories × 10 runs, 2026): ChatGPT cited a source for 92% of tools it recommended, but **only 11.6% of those citations were the vendor's own site**; 82% went to independent/niche blogs and comparison posts; review aggregators (G2/Capterra) got 0.9%. Cited pages: 100% list-structured, 78% had the year in the title, 68% had comparison tables, 56% FAQ sections. REPORTED https://derivatex.agency/report/b2b-saas-ai-citation-study/
- Semrush + Kevin Indig "ghost citations" (June 2026): 61.7% of citations don't name the brand in the answer; comparative queries get 2.4× more brand mentions than informational ones. REPORTED https://www.semrush.com/blog/the-ghost-citations-study/
- SparkToro (2,961 runs, 600 volunteers, Nov–Dec 2025): <1-in-100 chance two runs return the same brand list; but leaders appear in 55–97% of runs. **Measure appearance rate over many runs, never single-run rank.** REPORTED https://sparktoro.com/blog/new-research-ais-are-highly-inconsistent-when-recommending-brands-or-products-marketers-should-take-care-when-tracking-ai-visibility/

**For "what API should I use to get a YouTube transcript / TikTok video" prompts specifically:** COULD NOT CONFIRM any study isolating GitHub READMEs, PyPI/npm, Stack Overflow, Hacker News or dev.to as citation sources. The inference (labelled as inference): ChatGPT will pull Bing's top results for that query, which are listicles ("best YouTube transcript APIs 2026"), comparison posts, and docs pages; Claude will pull Brave's results and is willing to cite the vendor's docs directly. So the levers are (a) a crawlable docs/pricing page with the facts in plain HTML, (b) being present on the comparison pages that already rank (others' and your own), (c) Bing + Brave indexing. Vendor claims like "310% citation lift in 4 weeks" are FOLKLORE.

---

## 7. MCP as a distribution channel

- **Official MCP Registry** (registry.modelcontextprotocol.io): still "preview"; metadata-only `server.json` with a reverse-DNS name (`com.postreef/...` via DNS or HTTP verification, or `io.github.<user>/...`); publish with `mcp-publisher`; explicitly meant for downstream aggregators, not for host apps to read directly. ~9.6k servers (May 2026, REPORTED). No install/usage data exists. CONFIRMED https://modelcontextprotocol.io/registry/about. It feeds the GitHub MCP Registry (github.com/mcp), which is where VS Code's MCP page redirects. REPORTED https://github.blog/ai-and-ml/github-copilot/meet-the-github-mcp-registry-the-fastest-way-to-discover-mcp-servers/
- **Claude Connectors Directory**: submission requires a **Team or Enterprise Claude organization** (Owner role), an HTTPS Streamable-HTTP server, tool annotations, privacy policy + docs URLs, a test account for reviewers, and "Use OAuth 2.0 for authenticated services". After listing you get usage metrics. CONFIRMED https://claude.com/docs/connectors/building/submission. Auth options Claude supports for remote MCP: OAuth (DCR/CIMD), `static_headers` (API key in `authorization`/`x-api-key`, Beta, org-admin enters it once), `none`. Client-credentials M2M is not supported. CONFIRMED https://claude.com/docs/connectors/building/authentication. Desktop extensions (`.mcpb`) are for local servers; Anthropic says public APIs should be remote MCP. CONFIRMED https://claude.com/docs/connectors/custom/desktop-extensions
- **ChatGPT apps**: OAuth 2.1 with DCR or CIMD is mandatory; "ChatGPT does not support machine-to-machine OAuth grants such as client credentials... nor can it present custom API keys". CONFIRMED https://developers.openai.com/apps-sdk/build/auth. Submissions via platform.openai.com with annotations and a demo account. CONFIRMED https://developers.openai.com/apps-sdk/app-submission-guidelines
- **Cursor / VS Code**: both accept remote MCP servers with an `Authorization` header or OAuth in their config. CONFIRMED https://cursor.com/docs/mcp, https://code.visualstudio.com/docs/agents/reference/mcp-configuration. Cursor's `mcp-servers` repo is archived; listing is via cursor.directory/plugins. CONFIRMED https://github.com/cursor/mcp-servers
- **Aggregators** (Smithery, Glama, PulseMCP, mcp.so): publish by URL; Smithery shows per-server call volume. CONFIRMED https://smithery.ai/docs/build. Install-driving evidence: none. COULD NOT CONFIRM.

**Is an MCP server a real channel for Post Reef?** Partly. What it certainly does: lets a developer already using Claude/Cursor/VS Code call `extract(url, schema)` without writing a client, which removes friction *after* they've found Post Reef. What it does not do on the evidence: make Post Reef get *found*; no directory publishes discovery numbers, and the Claude directory needs a Team/Enterprise org plus OAuth. What it would take: one Streamable-HTTP server exposing `probe`, `extract`, `get_result`, `download_file`, and `list_schemas` tools; `Authorization: Bearer <api key>` for Cursor/VS Code/Claude `static_headers` today; an OAuth 2.1 layer (PKCE, DCR or CIMD, `/.well-known/oauth-protected-resource`) later if a Claude-directory or ChatGPT-apps listing is wanted. Effort: server with API-key auth ~2 days; OAuth layer ~1 week; directory submissions each need a reviewer test account with credits.

---

## 8. Measurement

What is actually observable, best to worst (CONFIRMED semantics from §4 docs):

1. **Server logs for `ChatGPT-User`, `Claude-User`, `Perplexity-User`, `Meta-ExternalFetcher`**: each hit is a page being read *while an answer is being composed*, i.e. a citation moment. Verify against published IP lists (openai.com/chatgpt-user.json, claude.com/crawling/bots.json, perplexity.com/perplexity-user.json). `OAI-SearchBot`/`Claude-SearchBot`/`PerplexityBot` hits = index building (precondition). `GPTBot`/`ClaudeBot`/`CCBot` = training crawl. Post Reef runs behind Cloudflare; Cloudflare's AI Crawl Control dashboard classifies these UAs. CONFIRMED https://developers.cloudflare.com/ai-crawl-control/
2. **`utm_source=chatgpt.com`**: ChatGPT appends it to cited links (observed since 2025-06; no official OpenAI doc). REPORTED https://www.seroundtable.com/openai-chatgpt-analytics-update-39590.html
3. **Referrers**: only ~25–35% of desktop ChatGPT visits carry a referrer; ~70% land as Direct. REPORTED https://attrifast.com/blog/chatgpt-referral-traffic-not-showing-in-analytics. GA4 added a default "AI Assistant" channel (2026-05). CONFIRMED (Google changelog) via https://www.searchenginejournal.com/google-analytics-adds-ai-assistant-as-default-channel-group/574974/. Claude reportedly strips referrers: UNCONFIRMED.
4. **Search Console "Generative AI" performance report**: impressions and cited pages in AI Overviews/AI Mode, no clicks, data from 2026-05-18. CONFIRMED https://developers.google.com/search/blog/2026/06/gen-ai-performance-reports
5. **A fixed prompt panel** run monthly: ~20 buyer prompts × 5 runs × (ChatGPT, Claude, Perplexity, Gemini), recording *whether Post Reef appears and which URL is cited*. Rank is noise; appearance rate is stable (SparkToro, §6).
6. **Paid tools** (Profound, Peec, Otterly, Semrush AI Toolkit): synthetic prompt sampling at scale; useful for competitor share-of-voice, overkill for a solo product. CONFIRMED that's what they do https://help.tryprofound.com/articles/3443229936-answer-engine-insights-overview

---

## 9. Post Reef-specific findings (CONFIRMED by reading the repo and fetching the live site, 2026-09-02)

1. **`/docs/llms.txt` is a 404.** The brief says llms.txt lives at `/docs/llms.txt`; the code (`apps/web/app/llms.txt/route.ts`) serves it at **`/llms.txt`** (200, 1,924 bytes) and `/llms-full.txt` (200, 67 KB). Any link or doc pointing at `/docs/llms.txt` is wrong.
2. **The brand is "PostReef" everywhere machine-facing.** `llms.txt` opens with `# PostReef`, the OpenAPI `info.title` is "PostReef API", `<title>` tags read "PostReef · …", and every docs page says "PostReef". The repo's own CLAUDE.md says customer-facing text must be "Post Reef". Models learn the name from these files; the split spelling will show up in answers.
3. **`llms.txt` content audit.** It's a correct index (spec-compliant: H1, blockquote, H2 sections, links to `.md` pages, OpenAPI link, llms-full link). It lacks: the pricing numbers themselves (a model answering "how much does it cost" has to fetch a second page), the platform list, the "what makes it different" sentence (bot-walls/PO tokens/proxies handled), the API key URL, the 60-minute/2-concurrent limits, and the 32 predefined schema ids. See ACTIONS for a proposed rewrite.
4. **`robots.txt` disallows `/v1/`**, which includes `/v1/openapi.json`, the most useful machine-readable file on the site. Search engines (and thus ChatGPT/Claude retrieval) can't index it.
5. **No JSON-LD** on the homepage or docs.
6. **`/developers` returns 404**; API keys live at `/developers/api-keys` (redirects to login). The API overview says "Create an API key in the dashboard" without a link.
7. **Cloudflare edge does not block AI user agents** on a UA basis (all tested UAs got 200). The managed robots.txt block is not active. The dashboard-level "block AI crawlers" default could still apply to verified bot IPs; only the Cloudflare dashboard can confirm.
8. **The docs pages are excellent raw material**: each has a Markdown twin at `/docs/<path>.md` (200, `text/markdown`), which is exactly what agentic tools fetch. Pricing, limits, error codes and the content-match verdict are all stated in plain text. That is the asset; the index file is decoration.
9. **Comment cap**: comments are capped to the top of the thread and the cap is not stated in the public docs; developers will assume "comments" means the whole thread. The skills say "the top comments, not the full thread".
10. **The edge returns 403 to Python's default user agent on `/v1/*`.** Tested 2026-09-02 with `POST /v1/probe` and `GET /v1/openapi.json`: `User-Agent: Python-urllib/3.13` → **403** (no `cf-mitigated` header, no error body); `python-requests/2.32.3`, `node`, `undici`, `Go-http-client/2.0`, `axios/1.7.2`, `curl/8.7.1`, `okhttp/4.12.0`, an empty UA, and a named UA all → 401 with the normal JSON envelope. Nothing in `apps/web` matches on "urllib", so this is a Cloudflare rule (a WAF managed rule or Bot Fight Mode's "definitely automated" list). Any developer or agent using Python's stdlib `urllib` against the API gets an opaque 403; the bundled client now sends `postreef-skills/0.1 (+repo url)`. The docs pages themselves (`/docs/api`) return 200 to the same UA.
11. **Description artifact naming** differs between the docs (`description.txt`) and what the API returns. The skills point at `summary.descriptionFile` instead of a hard-coded name.
