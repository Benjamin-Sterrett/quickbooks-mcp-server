# 🧾 QuickBooks MCP Server

> A secure, local-first Model Context Protocol (MCP) server to query QuickBooks data using natural language inside Claude Desktop.

--- 

## ✅ MCP Review Certification

This MCP Server is **[certified by MCP Review](https://mcpreview.com/mcp-servers/nikhilgy/quickbooks-mcp-server)**.

Being listed and certified on MCP Review ensures this server adheres to MCP standards and best practices, and is trusted by the developer community.

---

## Requirements:
1. Python 3.10 or higher

## Environment Setup
For local development, create a `.env` file in the project root with your QuickBooks credentials:

```bash
# Copy the template and fill in your actual credentials
cp env_template.txt .env
```

Then edit the `.env` file with your actual QuickBooks API credentials:
```
QUICKBOOKS_CLIENT_ID=your_actual_client_id
QUICKBOOKS_CLIENT_SECRET=your_actual_client_secret
QUICKBOOKS_REFRESH_TOKEN=your_actual_refresh_token
QUICKBOOKS_COMPANY_ID=your_actual_company_id
QUICKBOOKS_ENV='sandbox' or 'production'
```

**Note:** The `.env` file is automatically ignored by git for security reasons.

### Token Persistence (macOS)

QuickBooks rotates refresh tokens on every OAuth token exchange. This server automatically persists rotated tokens to **Apple Keychain** so they survive process restarts.

- **Primary:** Reads from Keychain (service: `claude-workflow`, account: `quickbooks-refresh-token`)
- **Fallback:** `QUICKBOOKS_REFRESH_TOKEN` env var (used only if Keychain entry is missing)
- **On rotation:** New refresh token is written to Keychain automatically

**Initial setup — seed the Keychain once:**
```bash
security add-generic-password -s claude-workflow -a quickbooks-refresh-token -w "YOUR_REFRESH_TOKEN" -U
```

After seeding, the server handles all future token rotations automatically. You should never need to manually update the token again.

**Verify the stored token:**
```bash
security find-generic-password -s claude-workflow -a quickbooks-refresh-token -w
```

**Self-healing session:** the server builds its QuickBooks session lazily and retries on every tool call until one succeeds. If you re-seed the Keychain with a valid token while the server is running, it recovers on the next call — no restart required.

### Re-authorizing after token expiry

Intuit refresh tokens expire after ~100 days of inactivity. Once expired, the token endpoint returns `400 invalid_grant` and there is **no programmatic recovery** — you must re-consent in a browser. Runbook:

1. Open the [OAuth 2.0 Playground](https://developer.intuit.com/app/developer/playground) (sign in to the Intuit Developer account).
2. **Select workspace/app** = the production app; check the **`com.intuit.quickbooks.accounting`** scope.
3. **Get authorization code** → authorize the correct company. Confirm the returned `realmId` matches `QUICKBOOKS_COMPANY_ID` in `.env`.
4. **Get tokens** → copy the new `refreshToken`.
5. Re-seed the Keychain:
   ```bash
   security add-generic-password -s claude-workflow -a quickbooks-refresh-token -w "NEW_REFRESH_TOKEN" -U
   ```
6. The running server picks it up on the next call (self-healing). If you use Claude Desktop, reconnecting the MCP server also works.

**Interim fallback:** until the server is re-authed, pull financials (NOI, P&L) directly from the QuickBooks Online web UI via **Reports → export**.

### Reports API modernization (Intuit, July 2026)

Intuit migrated the Reports API (Group 1, incl. ProfitAndLoss) to a modernized backend, reaching 100% by 2026-07-16. **Verified:** the modernized ProfitAndLoss payload is structurally identical to the legacy one (same `Header`/`Columns`/`Rows`); the only difference is a `v3modernResponse: true` response header. Because this server returns the raw report JSON unchanged (passthrough), **no parser change is required** — it works before and after the cutover. Pass `testing_migration=true` to opt a request into the modernized backend early (do **not** pass it on `TaxSummary`, which is not yet modernized). ProfitAndLoss is currently the only report this server exposes.

### `qb` terminal helper

`qb_cli.py` is a direct client (no `mcp-cli` dependency):

```bash
qb Account                    # show the Account entity schema
qb Account "Active = true"    # SELECT * FROM Account WHERE Active = true
```

Wire it into your shell (adjust the repo path):
```bash
qb() {
  uv run --directory /path/to/quickbooks-mcp qb_cli.py "$@"
}
```

## Step 1. Install uv:
   - MacOS/Linux: curl -LsSf https://astral.sh/uv/install.sh | sh
   - Windows: powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

## Step 2. Configure Claude Desktop
1. Download [Claude Desktop](https://claude.ai/download).
2. Launch Claude and go to Settings > Developer > Edit Config.
3. Modify `claude_desktop_config.json` with:
```json
{
  "mcpServers": {
    "QuickBooks": {
      "command": "uv",
      "args": [
        "--directory",
        "<absolute_path_to_quickbooks_mcp_folder>",
        "run",
        "main_quickbooks_mcp.py"
      ]
    }
  }
}
```
4. Relaunch Claude Desktop.

The first time you open Claude Desktop with these setting it may take
10-20 seconds before the QuickBooks tools appear in the interface due to
the installation of the required packages and the download of the most 
recent QuickBooks API documentation.

Everytime you launch Claude Desktop, the most recent QuickBooks API tools are made available 
to your AI assistant.

## Step 3. Launch Claude Desktop and let your assistant help you
### Examples
**Query Accounts**
```text
Get all accounts from QuickBooks.
```

**Query Bills**
```text
Get all bills from QuickBooks created after 2024-01-01.
```

**Query Customers**
```text
Get all customers from QuickBooks.
``` 
