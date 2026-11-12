# Post Reef

The `postreef` MCP server turns a social or video URL (YouTube, Shorts, TikTok, Instagram, Facebook, X, Vimeo, or any article) into its transcript, comments, metadata, media files and, when you pass a JSON Schema, a typed JSON object extracted from the content.

- Call `quote` first when cost matters: it prices a request without running it.
- `extract` starts a run and debits credits; `get_extraction` returns the result once it finishes; `list_extractions` shows recent runs.
- `list_schemas` shows the predefined schemas (for example `Recipe`) and the user's own.
- Signing in happens through OAuth the first time a tool is called; `get_profile` shows the account and its credit balance. Credits are topped up at https://postreef.com.

The skills in `skills/` explain the free do-it-yourself routes (yt-dlp, Whisper) and when the hosted API is worth it.
