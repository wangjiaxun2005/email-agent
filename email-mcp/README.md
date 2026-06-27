# Email Agent MCP Server

A standalone [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that lets Claude Code (and other MCP clients) interact with email servers via natural language.

**This server does NO AI work** — it only returns raw email data. Claude Code (via DeepSeek) handles all summarization, drafting, and reasoning.

## Architecture

```
┌─────────────────┐     MCP/stdio      ┌──────────────────────┐
│  Claude Code     │ ◄──────────────► │  email-mcp server     │
│  (DeepSeek)      │                   │  (imaplib + smtplib) │
└─────────────────┘                   └──────────────────────┘
                                                │
                                        ┌───────┴────────┐
                                        │  IMAP / SMTP   │
                                        │  Email Server  │
                                        └────────────────┘
```

## Features

| Tool | Description |
|------|-------------|
| `email-list` | List recent emails in a folder |
| `email-read` | Read full content of a specific email |
| `email-send` | Send an email via SMTP |
| `email-search` | Search emails by subject, sender, or body |
| `email-digest` | Get today's unread emails for Claude to summarize |

## Requirements

- Python 3.10+
- An email account with IMAP and SMTP access enabled

## Installation

```bash
# Navigate to the project
cd /path/to/email-mcp

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Set the following environment variables. You can place them in a `.env` file or export them directly.

### IMAP Settings (for reading email)

| Variable | Default | Description |
|----------|---------|-------------|
| `IMAP_HOST` | — | IMAP server hostname (e.g., `imap.gmail.com`) |
| `IMAP_PORT` | `993` | IMAP server port |
| `IMAP_USER` | — | Your full email address |
| `IMAP_PASSWORD` | — | Your email password or app password |
| `IMAP_USE_SSL` | `true` | Use SSL for IMAP connection |

### SMTP Settings (for sending email)

| Variable | Default | Description |
|----------|---------|-------------|
| `SMTP_HOST` | — | SMTP server hostname (e.g., `smtp.gmail.com`) |
| `SMTP_PORT` | `465` | SMTP server port |
| `SMTP_USER` | — | Your full email address |
| `SMTP_PASSWORD` | — | Your email password or app password |
| `SMTP_USE_SSL` | `true` | Use SSL for SMTP connection |

### Example (Gmail)

```bash
export IMAP_HOST="imap.gmail.com"
export IMAP_PORT=993
export IMAP_USER="your.email@gmail.com"
export IMAP_PASSWORD="your-app-password"
export IMAP_USE_SSL=true

export SMTP_HOST="smtp.gmail.com"
export SMTP_PORT=465
export SMTP_USER="your.email@gmail.com"
export SMTP_PASSWORD="your-app-password"
export SMTP_USE_SSL=true
```

> **Gmail users:** You need an [App Password](https://support.google.com/accounts/answer/185833) (requires 2FA enabled). Regular passwords will not work.

### Example (Outlook / Hotmail)

```bash
export IMAP_HOST="outlook.office365.com"
export IMAP_PORT=993
export IMAP_USER="your.email@outlook.com"
export IMAP_PASSWORD="your-password"
export SMTP_HOST="smtp.office365.com"
export SMTP_PORT=587
export SMTP_USE_SSL=false
```

## Usage

### Run the server directly

```bash
python server.py
```

This starts the MCP server on stdio — the default transport expected by Claude Code.

### Register with Claude Code

```bash
# From within the email-mcp directory
claude mcp add email-agent -- python /absolute/path/to/email-mcp/server.py
```

Or add to your Claude Code project configuration (`.claude/settings.json`):

```json
{
  "mcpServers": {
    "email-agent": {
      "command": "python",
      "args": ["/absolute/path/to/email-mcp/server.py"]
    }
  }
}
```

Then in Claude Code, you can say things like:

- "Show me my email inbox"
- "Read the latest email from John"
- "Send an email to alice@example.com saying I'll be late"
- "Search for emails about the quarterly report"
- "Give me a summary of today's unread emails"

### Test with MCP Inspector

```bash
mcp dev server.py
```

## Full AI Email Assistant Setup

This MCP server is just the engine. To build a complete AI email assistant like the one I use daily (WeChat-controlled, auto-grading, persistent task tracking), you need three pieces:

```
┌──────────────────────────────────────────────────────┐
│  WeChat / Terminal  ──►  cc-connect  ──►  Claude Code │
│                                    │                  │
│                     ┌──────────────┴──────────────┐   │
│                     │  .mcp.json  + .claude/       │   │
│                     │  (workspace config)          │   │
│                     └──────────────┬──────────────┘   │
│                                    │                  │
│                     ┌──────────────┴──────────────┐   │
│                     │  email-mcp (this repo)       │   │
│                     │  Python MCP server           │   │
│                     └─────────────────────────────┘   │
│                                                       │
│  macOS menu bar: email-agent-bar                      │
│  (start/stop daemon, Outlook setup)                   │
└──────────────────────────────────────────────────────┘
```

### What's in `examples/`

| File | What it is |
|------|------------|
| `system-prompt.md` | 300-line AI behavior spec: 5-level email grading, HKU-specific rules, task list management, display formats, interactive commands. This is the "brain" — give this to Claude Code. |
| `tasks.md` | Persistent task list template. The AI reads/writes this to track emails across sessions. |
| `profile.md` | User profile template (name, emails, signature). AI reads this to auto-fill sender info. |
| `mcp.json.template` | MCP config template. Copy to your workspace as `.mcp.json`, fill in credentials. |
| `../.env.example` | Environment variables template. Copy to `.env`, fill in IMAP/SMTP credentials. |

### Quick Start: Build Your Own

1. **Clone this repo** and install dependencies
2. **Copy `.env.example` → `.env`**, fill in your email credentials
3. **Install cc-connect**: `npm i -g @atticux/cc-connect`
4. **Create a workspace** directory with `.mcp.json` (use `mcp.json.template`) and `.claude/settings.json`
5. **Configure cc-connect** to point `work_dir` at your workspace, `system_prompt_file` at `examples/system-prompt.md`
6. **Build the menu bar** (optional): clone `email-agent-bar`, run `./make-app.sh`
7. Start the daemon and chat via WeChat or Terminal

See `examples/system-prompt.md` for the full AI behavior — it's the most valuable part of this project.

## Project Structure

```
email-mcp/
  __init__.py         # Package marker
  server.py           # FastMCP server with 7 tools
  email_client.py     # IMAP/SMTP operations
  microsoft_graph.py  # Microsoft Graph API (Office 365 / HKU)
  outlook_web_send.py # Outlook Web fallback (Playwright)
  requirements.txt    # Python dependencies
  .env.example        # Environment template (safe to commit)
  mcp.json.template   # MCP config template (safe to commit)
  examples/           # Full integration examples
    system-prompt.md  # AI behavior spec (the "brain")
    tasks.md          # Task list template
    profile.md        # User profile template
  README.md           # This file
```

## Design Principles

1. **No AI work** — The server returns raw email data only. Claude Code does all summarization, drafting, and reasoning.
2. **Minimal dependencies** — Uses Python stdlib (`imaplib`, `smtplib`, `email`) plus the `mcp` package.
3. **Clean errors** — Every tool returns meaningful error messages instead of crashing.
4. **Standalone** — No Django dependency. Works with any email server that supports IMAP and SMTP.

## License

MIT
