"""
server.py — MCP (Model Context Protocol) server for the AI Email Agent.

Provides 5 tools that let Claude Code interact with email via natural
language.  This server does NO AI work — it only returns raw email data.

Tools
-----
email-list              List recent emails in a folder
email-read              Read full content of a specific email
email-send              Send an email via SMTP (Gmail)
email-search            Search emails by subject/from/body
email-digest            Digest of today's unread emails for Claude to summarize
email-send-microsoft    Send via Microsoft Graph API (if configured)
email-send-hku          Send via Outlook Web automation (for HKU)

Usage
-----
    # Run with stdio transport (default for Claude Code)
    python -m email_mcp.server

    # Or register with Claude Code:
    claude mcp add email-agent -- python /path/to/server.py
"""

import os
import sys
import logging

from mcp.server.fastmcp import FastMCP

# Ensure the parent directory is on sys.path so we can import sibling modules
# when run as `python server.py` directly.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

# Auto-load .env from this directory so credentials don't need to be
# passed via .mcp.json env. Falls back to environment variables if
# python-dotenv is not installed or .env is missing.
try:
    from dotenv import load_dotenv
    _ENV_FILE = os.path.join(_THIS_DIR, ".env")
    if os.path.isfile(_ENV_FILE):
        load_dotenv(_ENV_FILE, override=True)
except ImportError:
    pass

from email_client import EmailClient, load_config
from microsoft_graph import MicrosoftGraphClient, MicrosoftGraphConfig
from outlook_web_send import OutlookWebSender

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("email-mcp-server")

# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

mcp = FastMCP("email-agent", instructions="Email Agent MCP server — read, send, and search emails. Supports Gmail SMTP and Microsoft Graph API.")

# We initialise clients lazily because env vars must be available at runtime.
_email_client: EmailClient | None = None
_ms_client: MicrosoftGraphClient | None = None
_outlook_client: OutlookWebSender | None = None


def get_client() -> EmailClient:
    """Return a singleton EmailClient (Gmail IMAP/SMTP), validating config on first call."""
    global _email_client
    if _email_client is None:
        try:
            config = load_config()
            _email_client = EmailClient(config)
        except ValueError as e:
            logger.error("Failed to initialise EmailClient: %s", e)
            raise
    return _email_client


def get_ms_client() -> MicrosoftGraphClient | None:
    """Return a singleton MicrosoftGraphClient, or None if not configured."""
    global _ms_client
    if _ms_client is None:
        config = MicrosoftGraphConfig()
        err = config.validate()
        if err:
            logger.warning("Microsoft Graph not configured: %s", err)
            return None
        _ms_client = MicrosoftGraphClient(config)
    return _ms_client


def get_outlook_client() -> OutlookWebSender | None:
    """Return a singleton OutlookWebSender, or None if auth state not set up."""
    global _outlook_client
    if _outlook_client is None:
        sender = OutlookWebSender()
        if not sender.is_configured():
            logger.warning("Outlook Web not configured. Run setup_outlook_web.py first.")
            return None
        _outlook_client = sender
    return _outlook_client


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@mcp.tool(
    annotations={
        "title": "List Emails",
        "readOnlyHint": True,
    }
)
async def email_list(
    folder: str = "INBOX",
    limit: int = 20,
    unread_only: bool = False,
) -> list[dict]:
    """List recent emails from a folder.

    Parameters
    ----------
    folder : str, optional
        IMAP folder name (default "INBOX").
    limit : int, optional
        Maximum number of emails to return (default 20).
    unread_only : bool, optional
        If True, only return unread messages (default False).

    Returns
    -------
    list[dict]
        Each dict contains: id, from, subject, date, unread.
    """
    client = get_client()
    try:
        return client.list_emails(
            folder=folder,
            limit=limit,
            unread_only=unread_only,
        )
    except Exception as e:
        logger.exception("email-list failed")
        return [{"error": str(e)}]


@mcp.tool(
    annotations={
        "title": "Read Email",
        "readOnlyHint": True,
    }
)
async def email_read(email_id: str, folder: str = "INBOX") -> dict:
    """Read the full content of a specific email by its IMAP UID or sequence number.

    Parameters
    ----------
    email_id : str
        The IMAP UID or sequence number of the email.
    folder : str, optional
        IMAP folder name (default "INBOX").

    Returns
    -------
    dict
        Contains: id, from, to, cc, subject, date, unread, body.
    """
    client = get_client()
    try:
        result = client.read_email(email_id=email_id, folder=folder)
        if result is None:
            return {"error": f"Email with id '{email_id}' not found in folder '{folder}'."}
        return result
    except Exception as e:
        logger.exception("email-read failed")
        return {"error": str(e)}


@mcp.tool(
    annotations={
        "title": "Send Email",
    }
)
async def email_send(to: str, subject: str, body: str) -> dict:
    """Send an email via SMTP.

    Parameters
    ----------
    to : str
        Recipient email address.
    subject : str
        Subject line of the email.
    body : str
        Plain-text body of the email.

    Returns
    -------
    dict
        Status dict with 'success' (bool) and 'message' or 'error'.
    """
    client = get_client()
    try:
        return client.send_email(to=to, subject=subject, body=body)
    except Exception as e:
        logger.exception("email-send failed")
        return {"success": False, "error": str(e)}


@mcp.tool(
    annotations={
        "title": "Search Emails",
        "readOnlyHint": True,
    }
)
async def email_search(query: str, folder: str = "INBOX") -> list[dict]:
    """Search emails by subject, sender, or body content using IMAP SEARCH.

    Parameters
    ----------
    query : str
        Search term to match against subject, from, and body fields.
    folder : str, optional
        IMAP folder name (default "INBOX").

    Returns
    -------
    list[dict]
        Matching emails, each containing: id, from, subject, date.
    """
    client = get_client()
    try:
        return client.search_emails(query=query, folder=folder)
    except Exception as e:
        logger.exception("email-search failed")
        return [{"error": str(e)}]


@mcp.tool(
    annotations={
        "title": "Email Digest",
        "readOnlyHint": True,
    }
)
async def email_digest(limit: int = 20, days: int = 1) -> list[dict]:
    """Get a digest of unread emails from the inbox.

    Returns the from, subject, and date for each unread email received
    in the last N days. Designed for Claude to then summarise into a briefing.

    Parameters
    ----------
    limit : int, optional
        Maximum number of digest entries (default 20).
    days : int, optional
        Number of days to look back (default 1 = today only).
        Use 7 for last week, 3 for last 3 days, etc.

    Returns
    -------
    list[dict]
        Each dict contains: id, from, subject, date.
    """
    client = get_client()
    try:
        return client.digest(limit=limit, days=days)
    except Exception as e:
        logger.exception("email-digest failed")
        return [{"error": str(e)}]


@mcp.tool(
    annotations={
        "title": "Send Email via Microsoft Graph (HKU/Office 365)",
    }
)
async def email_send_microsoft(to: str, subject: str, body: str) -> dict:
    """Send an email via Microsoft Graph API (e.g. from @connect.hku.hk).

    Use this tool when the email should be sent from a Microsoft/Office 365
    account (like @connect.hku.hk) instead of Gmail. The sender address is
    determined by the configured Microsoft account.

    Parameters
    ----------
    to : str
        Recipient email address.
    subject : str
        Subject line of the email.
    body : str
        Plain-text body of the email.

    Returns
    -------
    dict
        Status dict with 'success' (bool) and 'message' or 'error'.
    """
    client = get_ms_client()
    if client is None:
        return {"success": False, "error": "Microsoft Graph API is not configured. Run setup_microsoft.py first."}
    try:
        return client.send_email(to=to, subject=subject, body=body)
    except Exception as e:
        logger.exception("email-send-microsoft failed")
        return {"success": False, "error": str(e)}


@mcp.tool(
    annotations={
        "title": "Send Email via HKU Outlook Web",
    }
)
async def email_send_hku(to: str, subject: str, body: str) -> dict:
    """Send an email from your HKU account (@connect.hku.hk) via Outlook Web.

    Use this tool when you need to send email from the HKU address.
    It automates the Outlook Web App in a browser — no API access needed.
    Works when Graph API / SMTP are blocked by the university.

    Before first use, run: cd email-mcp && python setup_outlook_web.py

    Parameters
    ----------
    to : str
        Recipient email address.
    subject : str
        Subject line of the email.
    body : str
        Plain-text body of the email.

    Returns
    -------
    dict
        Status dict with 'success' (bool) and 'message' or 'error'.
    """
    client = get_outlook_client()
    if client is None:
        return {
            "success": False,
            "error": (
                "Outlook Web not set up. Run: "
                "cd email-mcp && python setup_outlook_web.py"
            ),
        }
    try:
        return client.send_email(to=to, subject=subject, body=body)
    except Exception as e:
        logger.exception("email-send-hku failed")
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    """Run the MCP server using stdio transport (default for Claude Code)."""
    # Validate config on startup so we fail fast.
    try:
        load_config()
        logger.info("Configuration validated successfully.")
    except ValueError as e:
        logger.error("Invalid configuration: %s", e)
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
