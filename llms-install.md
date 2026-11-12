# Installing the Post Reef MCP server

Post Reef is a remote MCP server. There is nothing to clone, build or run locally.

- URL: `https://postreef.com/mcp`
- Transport: Streamable HTTP
- Auth: OAuth 2.1 with dynamic client registration (the client opens a browser to sign in), or an API key from https://postreef.com/developers/api-keys sent as `Authorization: Bearer pr_...`

## Cline

Add this to `cline_mcp_settings.json`:

```json
{
  "mcpServers": {
    "postreef": {
      "type": "streamableHttp",
      "url": "https://postreef.com/mcp",
      "headers": { "Authorization": "Bearer ${POSTREEF_API_KEY}" }
    }
  }
}
```

Ask the user for their Post Reef API key and put it in place of `${POSTREEF_API_KEY}`. If the client supports OAuth for remote servers, the `headers` block can be left out and the user signs in in the browser instead.

## Check it works

Call `get_profile`: it returns the account name and credit balance. Then `quote` with a YouTube URL prices a run without spending anything.

Docs: https://postreef.com/docs/api/mcp
