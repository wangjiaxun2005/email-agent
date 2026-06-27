"""
email_client.py — Standalone IMAP/SMTP email client for the MCP server.

Uses Python stdlib imaplib and smtplib. No Django dependency.
Configured via environment variables (see load_config()).
"""

import imaplib
import smtplib
import ssl
import logging
import os
import datetime
import email
from email.message import EmailMessage
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import Optional

try:
    import certifi
except ImportError:
    certifi = None  # fallback to default SSL context

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class EmailConfig:
    """Holds IMAP and SMTP connection parameters, populated from env vars."""

    def __init__(self):
        # IMAP
        self.imap_host: str = os.getenv("IMAP_HOST", "")
        self.imap_port: int = int(os.getenv("IMAP_PORT", "993"))
        self.imap_user: str = os.getenv("IMAP_USER", "")
        self.imap_password: str = os.getenv("IMAP_PASSWORD", "")
        self.imap_use_ssl: bool = os.getenv("IMAP_USE_SSL", "true").lower() in ("true", "1", "yes")

        # SMTP
        self.smtp_host: str = os.getenv("SMTP_HOST", "")
        self.smtp_port: int = int(os.getenv("SMTP_PORT", "465"))
        self.smtp_user: str = os.getenv("SMTP_USER", "")
        self.smtp_password: str = os.getenv("SMTP_PASSWORD", "")
        self.smtp_use_ssl: bool = os.getenv("SMTP_USE_SSL", "true").lower() in ("true", "1", "yes")

    def validate(self) -> Optional[str]:
        """Return an error string if any required config is missing, else None."""
        missing = []
        if not self.imap_host:
            missing.append("IMAP_HOST")
        if not self.imap_user:
            missing.append("IMAP_USER")
        if not self.imap_password:
            missing.append("IMAP_PASSWORD")
        if not self.smtp_host:
            missing.append("SMTP_HOST")
        if not self.smtp_user:
            missing.append("SMTP_USER")
        if not self.smtp_password:
            missing.append("SMTP_PASSWORD")
        if missing:
            return f"Missing required environment variables: {', '.join(missing)}"
        return None


def load_config() -> EmailConfig:
    """Load and validate email configuration from environment variables."""
    config = EmailConfig()
    err = config.validate()
    if err:
        logger.error(err)
        raise ValueError(err)
    return config


# ---------------------------------------------------------------------------
# IMAP helpers
# ---------------------------------------------------------------------------

def _decode_mime_header(value: str) -> str:
    """Decode a MIME encoded-header (e.g. =?UTF-8?B?...?=) to plain text."""
    if not value:
        return ""
    parts = decode_header(value)
    decoded_parts = []
    for part, charset in parts:
        if isinstance(part, bytes):
            try:
                decoded_parts.append(part.decode(charset or "utf-8", errors="replace"))
            except (LookupError, UnicodeDecodeError):
                decoded_parts.append(part.decode("utf-8", errors="replace"))
        else:
            decoded_parts.append(part)
    return " ".join(decoded_parts)


def _parse_email_date(date_str: str) -> Optional[str]:
    """Parse an email date header into 'YYYY-MM-DD HH:MM:SS' or None."""
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return date_str  # return raw string on failure


def _fetch_email_body(msg: email.message.Message) -> str:
    """Extract the plain-text body from an email Message."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            # Skip attachments
            if "attachment" in content_disposition:
                continue
            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        body += payload.decode(charset, errors="replace")
                    except (LookupError, UnicodeDecodeError):
                        body += payload.decode("utf-8", errors="replace")
            elif content_type == "text/html" and not body:
                # Fall back to HTML only if no plain text found
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    try:
                        body += payload.decode(charset, errors="replace")
                    except (LookupError, UnicodeDecodeError):
                        body += payload.decode("utf-8", errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            try:
                body = payload.decode(charset, errors="replace")
            except (LookupError, UnicodeDecodeError):
                body = payload.decode("utf-8", errors="replace")
    return body.strip()


def _fetch_email_from(msg: email.message.Message) -> str:
    """Extract the From field, preferring the decoded name if available."""
    from_header = msg.get("From", "")
    decoded = _decode_mime_header(from_header)
    return decoded or from_header


def _fetch_email_subject(msg: email.message.Message) -> str:
    """Extract and decode the Subject header."""
    subject = msg.get("Subject", "")
    return _decode_mime_header(subject) or subject


# ---------------------------------------------------------------------------
# Email Client
# ---------------------------------------------------------------------------

class EmailClient:
    """Provides IMAP read/search and SMTP send operations."""

    def __init__(self, config: Optional[EmailConfig] = None):
        self.config = config or load_config()

    # -- IMAP connection ---------------------------------------------------

    def _connect_imap(self) -> imaplib.IMAP4:
        """Open and return an IMAP connection. Caller must close()."""
        cfg = self.config
        if cfg.imap_use_ssl:
            context = ssl.create_default_context(cafile=certifi.where() if certifi else None)
            conn = imaplib.IMAP4_SSL(cfg.imap_host, cfg.imap_port, ssl_context=context)
        else:
            conn = imaplib.IMAP4(cfg.imap_host, cfg.imap_port)
            conn.starttls()
        conn.login(cfg.imap_user, cfg.imap_password)
        return conn

    def _ensure_utf8(self, conn: imaplib.IMAP4):
        """Try to enable UTF-8 mode on the IMAP connection (RFC 6855)."""
        try:
            conn.enable("UTF8=ACCEPT")
        except imaplib.IMAP4.error:
            pass

    # -- List emails -------------------------------------------------------

    def list_emails(self, folder: str = "INBOX", limit: int = 20,
                    unread_only: bool = False) -> list[dict]:
        """Return recent emails from the given folder."""
        conn = self._connect_imap()
        try:
            self._ensure_utf8(conn)
            conn.select(folder, readonly=True)

            search_criterion = "UNSEEN" if unread_only else "ALL"
            _, message_ids = conn.uid("SEARCH", None, search_criterion)
            ids = message_ids[0].split() if message_ids[0] else []
            if not ids:
                return []

            # Fetch the most recent N messages
            recent_ids = ids[-limit:]

            emails = []
            for mid in recent_ids:
                _, msg_data = conn.uid("FETCH", mid, "(RFC822)")
                if msg_data and msg_data[0]:
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    emails.append({
                        "id": mid.decode(),
                        "from": _fetch_email_from(msg),
                        "subject": _fetch_email_subject(msg),
                        "date": _parse_email_date(msg.get("Date", "")),
                        "unread": True,  # approximate
                    })
            return list(reversed(emails))  # newest first
        finally:
            conn.close()
            conn.logout()

    # -- Read email by UID -------------------------------------------------

    def read_email(self, email_id: str, folder: str = "INBOX") -> Optional[dict]:
        """Fetch the full content of an email by its IMAP UID."""
        conn = self._connect_imap()
        try:
            conn.select(folder, readonly=True)
            # Try searching by UID first
            typ, data = conn.uid("FETCH", email_id, "(RFC822 FLAGS)")
            if typ != "OK" or not data or not data[0]:
                # Fall back to sequence number
                typ, data = conn.fetch(email_id, "(RFC822 FLAGS)")
                if typ != "OK" or not data or not data[0]:
                    return None

            raw_email = None
            flags = ""
            for part in data:
                if isinstance(part, tuple):
                    raw_email = part[1]
                elif isinstance(part, bytes):
                    flags = part.decode()
                else:
                    flags = str(part)

            if not raw_email:
                return None

            msg = email.message_from_bytes(raw_email)

            # Decode flags to determine read/unread
            is_unread = "\\Seen" not in flags.upper()

            # Get recipients
            to_header = _decode_mime_header(msg.get("To", ""))
            cc_header = _decode_mime_header(msg.get("Cc", ""))

            return {
                "id": email_id,
                "from": _fetch_email_from(msg),
                "to": to_header,
                "cc": cc_header,
                "subject": _fetch_email_subject(msg),
                "date": _parse_email_date(msg.get("Date", "")),
                "unread": is_unread,
                "body": _fetch_email_body(msg),
            }
        finally:
            conn.close()
            conn.logout()

    # -- Send email --------------------------------------------------------

    def send_email(self, to: str, subject: str, body: str) -> dict:
        """Send an email via SMTP. Returns a status dict."""
        cfg = self.config

        msg = EmailMessage()
        msg.set_content(body)
        msg["From"] = cfg.smtp_user
        msg["To"] = to
        msg["Subject"] = subject

        try:
            if cfg.smtp_use_ssl:
                context = ssl.create_default_context(cafile=certifi.where() if certifi else None)
                with smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, context=context) as server:
                    server.login(cfg.smtp_user, cfg.smtp_password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port) as server:
                    server.starttls()
                    server.login(cfg.smtp_user, cfg.smtp_password)
                    server.send_message(msg)

            return {"success": True, "message": f"Email sent to {to}"}
        except smtplib.SMTPException as e:
            logger.exception("SMTP send failed")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.exception("Unexpected send error")
            return {"success": False, "error": str(e)}

    # -- Search emails -----------------------------------------------------

    def search_emails(self, query: str, folder: str = "INBOX") -> list[dict]:
        """Search emails by subject, from, or body using IMAP SEARCH."""
        conn = self._connect_imap()
        try:
            self._ensure_utf8(conn)
            conn.select(folder, readonly=True)

            # Construct IMAP search criteria
            # We search in SUBJECT, FROM, and BODY
            criteria = f'OR OR SUBJECT "{query}" FROM "{query}" BODY "{query}"'
            _, message_ids = conn.uid("SEARCH", None, criteria)
            ids = message_ids[0].split() if message_ids[0] else []
            if not ids:
                return []

            emails = []
            for mid in ids:
                _, msg_data = conn.uid("FETCH", mid, "(RFC822)")
                if msg_data and msg_data[0]:
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    emails.append({
                        "id": mid.decode(),
                        "from": _fetch_email_from(msg),
                        "subject": _fetch_email_subject(msg),
                        "date": _parse_email_date(msg.get("Date", "")),
                    })
            return emails
        finally:
            conn.close()
            conn.logout()

    # -- Digest (today's unread) -------------------------------------------

    def digest(self, limit: int = 20, days: int = 1) -> list[dict]:
        """Return unread emails from the inbox for the last N days.

        Parameters
        ----------
        limit : int
            Maximum number of digest entries (default 20).
        days : int
            Number of days to look back (default 1 = today only).
            7 = last week. Uses IMAP SINCE which is date-based (no time).
        """
        conn = self._connect_imap()
        try:
            self._ensure_utf8(conn)
            conn.select("INBOX", readonly=True)

            since_date = (datetime.date.today() - datetime.timedelta(days=days - 1)).strftime("%d-%b-%Y")
            _, message_ids = conn.uid("SEARCH", None, f'(UNSEEN SINCE "{since_date}")')
            ids = message_ids[0].split() if message_ids[0] else []
            if not ids:
                return []

            recent_ids = ids[-limit:]

            emails = []
            for mid in recent_ids:
                _, msg_data = conn.uid("FETCH", mid, "(RFC822)")
                if msg_data and msg_data[0]:
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    emails.append({
                        "id": mid.decode(),
                        "from": _fetch_email_from(msg),
                        "subject": _fetch_email_subject(msg),
                        "date": _parse_email_date(msg.get("Date", "")),
                    })
            return list(reversed(emails))
        finally:
            conn.close()
            conn.logout()
