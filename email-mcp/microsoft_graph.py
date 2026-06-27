"""
microsoft_graph.py — Microsoft Graph API email client.

Sends emails via Microsoft 365 / Office 365 Graph API (e.g. @connect.hku.hk).
Uses OAuth refresh token to obtain access tokens automatically.
Zero extra dependencies — pure Python stdlib.
"""

import json
import os
import time
import logging
import urllib.request
import urllib.error
import urllib.parse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GRAPH_URL = "https://graph.microsoft.com/v1.0/"
AUTHORITY = "https://login.microsoftonline.com/common"
SCOPES = ["Mail.Send", "offline_access"]

# Token storage: same directory as this file
_TOKEN_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(_TOKEN_DIR, "microsoft_token.json")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class MicrosoftGraphConfig:
    """Holds Microsoft OAuth parameters, populated from env vars."""

    def __init__(self):
        self.client_id: str = os.getenv("MICROSOFT_CLIENT_ID", "")
        self.client_secret: str = os.getenv("MICROSOFT_CLIENT_SECRET", "")
        self.refresh_token: str = ""

        # Load refresh token from token file (preferred) or env var (fallback)
        token_data = _load_token_file()
        if token_data and "refresh_token" in token_data:
            self.refresh_token = token_data["refresh_token"]
        elif os.getenv("MICROSOFT_REFRESH_TOKEN"):
            self.refresh_token = os.getenv("MICROSOFT_REFRESH_TOKEN")

    def validate(self):
        """Return an error string if required config is missing, else None."""
        missing = []
        if not self.client_id:
            missing.append("MICROSOFT_CLIENT_ID")
        if not self.client_secret:
            missing.append("MICROSOFT_CLIENT_SECRET")
        if not self.refresh_token:
            missing.append("MICROSOFT_REFRESH_TOKEN")
        if missing:
            return f"Missing Microsoft Graph config: {', '.join(missing)}. Run setup_microsoft.py first."
        return None


# ---------------------------------------------------------------------------
# Token storage helpers
# ---------------------------------------------------------------------------

def _load_token_file():
    """Load tokens from the JSON token file. Returns dict or None."""
    try:
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _save_token_file(data):
    """Save tokens to the JSON token file."""
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        json.dump(data, f, indent=2)
    logger.info("Token file updated: %s", TOKEN_FILE)


# ---------------------------------------------------------------------------
# Microsoft Graph Client
# ---------------------------------------------------------------------------

class MicrosoftGraphClient:
    """Sends emails via Microsoft Graph API with automatic OAuth token refresh."""

    def __init__(self, config=None):
        self.config = config or MicrosoftGraphConfig()
        self._access_token: str = ""
        self._token_expiry: float = 0  # epoch seconds

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    def _get_access_token(self):
        """Return a valid access token, refreshing via refresh_token if needed."""
        if self._access_token and time.time() < self._token_expiry - 60:
            return self._access_token

        logger.info("Refreshing Microsoft access token...")

        data = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": self.config.refresh_token,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "scope": " ".join(SCOPES),
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{AUTHORITY}/oauth2/v2.0/token",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            logger.error("Token refresh HTTP %s: %s", e.code, error_body)
            raise RuntimeError(
                f"Microsoft token refresh failed (HTTP {e.code}). "
                f"Your refresh token may have expired. Run setup_microsoft.py again.\n"
                f"Details: {error_body}"
            )

        self._access_token = result.get("access_token", "")
        self._token_expiry = time.time() + result.get("expires_in", 3600)

        # Microsoft rotates refresh tokens — save the new one
        if "refresh_token" in result:
            self.config.refresh_token = result["refresh_token"]
            _save_token_file({"refresh_token": result["refresh_token"]})
            logger.info("Refresh token rotated and saved.")

        if not self._access_token:
            raise RuntimeError("Token response did not contain access_token.")

        return self._access_token

    # ------------------------------------------------------------------
    # Send email
    # ------------------------------------------------------------------

    def send_email(self, to: str, subject: str, body: str, content_type: str = "Text") -> dict:
        """Send an email via Microsoft Graph API.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            body: Email body content.
            content_type: "Text" for plain text, "HTML" for HTML body.

        Returns:
            dict with 'success' (bool) and 'message' or 'error'.
        """
        try:
            access_token = self._get_access_token()
        except RuntimeError as e:
            return {"success": False, "error": str(e)}

        email_payload = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": content_type,
                    "content": body,
                },
                "toRecipients": [
                    {"emailAddress": {"address": to}}
                ],
            }
        }

        req = urllib.request.Request(
            f"{GRAPH_URL}me/sendMail",
            data=json.dumps(email_payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req) as resp:
                if resp.status == 202:
                    return {"success": True, "message": f"Email sent to {to} via Microsoft Graph"}
                else:
                    return {"success": False, "error": f"Unexpected status: {resp.status}"}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            logger.error("Graph API send failed (HTTP %s): %s", e.code, error_body)
            return {"success": False, "error": f"Graph API error: {e.code} — {error_body}"}

    # ------------------------------------------------------------------
    # Who am I? (for debugging)
    # ------------------------------------------------------------------

    def whoami(self) -> dict:
        """Return the authenticated user's profile (mail, displayName, etc.)."""
        try:
            access_token = self._get_access_token()
        except RuntimeError as e:
            return {"success": False, "error": str(e)}

        req = urllib.request.Request(
            f"{GRAPH_URL}me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        try:
            with urllib.request.urlopen(req) as resp:
                profile = json.loads(resp.read().decode("utf-8"))
                return {
                    "success": True,
                    "email": profile.get("mail") or profile.get("userPrincipalName", ""),
                    "display_name": profile.get("displayName", ""),
                }
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            return {"success": False, "error": f"Graph API whoami failed: {e.code} — {error_body}"}
