# Email Agent — AI Email Assistant

Your AI email secretary inside WeChat. Check emails, read full content, sort by priority, track todos — no need to open your inbox after reading WeChat.

## Architecture

```
Phone (WeChat) ←→ cc-connect ←→ Claude Code + email-mcp
                                    │
                ┌───────────────────┼───────────────────┐
                ▼                   ▼                   ▼
         Read (IMAP)       Send Gmail (SMTP)    Send HKU (Graph API)
```

## Project Structure

| Path | Description |
|------|-------------|
| `email-mcp/` | Python MCP server with email tools (read, search, send) |
| `email-mcp/examples/` | Templates: system prompt, user profile, task list |
| `email.sh` | HKU email setup & test script |
| `.mcp.json.template` | MCP config template — copy to `.mcp.json` and fill in credentials |

## Quick Start

### 1. Install dependencies

```bash
cd email-mcp
pip install -r requirements.txt
playwright install chromium   # Required for HKU Outlook Web send
```

### 2. Configure credentials

```bash
cp .mcp.json.template .mcp.json
# Edit .mcp.json with your IMAP/SMTP credentials
# Or create a .env file inside email-mcp/
```

### 3. Register MCP server

Claude Code auto-detects `.mcp.json` in the workspace root. Verify with `claude mcp list` — you should see `email-agent`.

### 4. Configure cc-connect (WeChat bridge)

```bash
npm install -g @atticux/cc-connect
```

In `~/.cc-connect/config.toml`, point to this workspace:

```toml
[projects.agent]
type = "claudecode"
system_prompt_file = "email-mcp/examples/system-prompt.md"

[projects.agent.options]
work_dir = "/path/to/email-agent"
mode = "auto"
```

Start: `cc-connect daemon start`

## MCP Tools

| Tool | Description |
|------|-------------|
| `email_digest` | Get unread email digest (sender, subject, date) |
| `email_list` | List emails in a folder |
| `email_read` | Read full email content |
| `email_search` | Search emails by query |
| `email_send` | Send via Gmail SMTP |
| `email_send_microsoft` | Send via Microsoft Graph API (HKU) |
| `email_send_hku` | Send via Outlook Web (HKU fallback) |

## Email Priority Tiers

| Tier | Meaning | Examples |
|------|---------|----------|
| 🚨 Urgent | Action required now | Account security alert, deadline within 24h, personal email directly to you |
| 📌 Important | Needs attention | TA/RA/internship opportunities, emails requiring reply, university admin |
| 📋 Noteworthy | Possibly useful | CDS/CS seminars, job recommendations, credit card statements |
| 📎 Casual | FYI only | Unrelated faculty newsletters, system notifications |
| 🗑️ Spam | Skip | Marketing emails, club recruitments |

## WeChat Commands

| Command | Action |
|---------|--------|
| `checke` / `查邮件` | Scan unread emails and update todo list |
| `a` / `看a` | View email details for task labeled `a` |
| `a搞定` | Mark task `a` as done |
| `加一个🚨：xxx` | Manually add a todo item |
| `清单` / `待办` | Show todo list only |
| `rearrange` / `重排` | Re-sort and re-label all todos |

## Sister Project

- **[ultimate-bar](https://github.com/wangjiaxun2005/ultimate-bar)** — macOS menu bar console for managing the cc-connect daemon

## License

MIT
