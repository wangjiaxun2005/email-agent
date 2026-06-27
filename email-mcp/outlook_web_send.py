"""
outlook_web_send.py — Send emails via Outlook Web App (OWA) browser automation.

Uses Playwright to control a Chromium browser and automate Outlook Web's
compose → fill → send flow. This works even when IMAP/SMTP/Graph API are
all blocked by the university — as long as you can log in to Outlook Web.

Setup (one-time):
    python setup_outlook_web.py
    → Browser opens, log in to your HKU account, press Enter in terminal.
    → Auth state saved to outlook_auth.json.

Usage:
    from outlook_web_send import OutlookWebSender

    sender = OutlookWebSender()
    result = sender.send_email(
        to="professor@hku.hk",
        subject="About the assignment",
        body="Dear Professor, ...",
    )
"""

import json
import logging
import urllib.parse
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

HERE = Path(__file__).parent
AUTH_FILE = HERE / "outlook_auth.json"
OUTLOOK_URL = "https://outlook.office.com/mail/"


class OutlookWebSender:
    """Send emails by automating the Outlook Web App in a browser."""

    def is_configured(self) -> bool:
        """Return True if auth state has been set up."""
        return AUTH_FILE.exists()

    def send_email(self, to: str, subject: str, body: str) -> dict:
        """Open Outlook Web, compose an email, and send it.

        Returns a dict with 'success' (bool) and 'message' or 'error'.
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": (
                    "Outlook Web not configured. Run: "
                    "cd email-mcp && python setup_outlook_web.py"
                ),
            }

        try:
            from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout
        except ImportError:
            return {
                "success": False,
                "error": (
                    "Playwright is not installed. Run:\n"
                    "  pip install playwright && playwright install chromium"
                ),
            }

        # URL-encode subject and body for the compose deep-link.
        # Outlook Web deeplink: /mail/deeplink/compose?to=...&subject=...&body=...
        compose_params = {"to": to, "subject": subject, "body": body}

        # Navigate to a minimal page first to restore cookies, then jump to compose
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                    ],
                )

                context = browser.new_context(
                    storage_state=str(AUTH_FILE),
                    viewport={"width": 1280, "height": 900},
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/130.0.0.0 Safari/537.36"
                    ),
                )

                page = context.new_page()

                # Hide automation traces
                page.add_init_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
                )

                # Step 1: Go to inbox first to restore session
                logger.info("Opening Outlook Web inbox...")
                page.goto(OUTLOOK_URL, wait_until="domcontentloaded", timeout=30000)

                # Microsoft may redirect a few times; give it a moment
                page.wait_for_timeout(3000)

                # If we land on a login page, the session expired
                current_url = page.url.lower()
                if "login" in current_url or "microsoftonline" in current_url:
                    return {
                        "success": False,
                        "error": (
                            "Outlook Web session expired. "
                            "Re-run: cd email-mcp && python setup_outlook_web.py"
                        ),
                    }

                # Step 2: Navigate to compose via deep link
                compose_url = (
                    f"{OUTLOOK_URL}deeplink/compose?"
                    f"to={urllib.parse.quote(to)}&"
                    f"subject={urllib.parse.quote(subject)}&"
                    f"body={urllib.parse.quote(body)}"
                )
                logger.info("Opening compose window: %s", compose_url[:120])
                page.goto(compose_url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(2000)

                # Step 3: Click the Send button
                # Outlook Web's send button can appear in a few forms:
                #   <button aria-label="Send">  or  <button title="Send">
                # Try multiple selectors
                send_selectors = [
                    'button[aria-label="Send"]',
                    'button[title="Send"]',
                    'button[aria-label*="发送"]',
                    'button[aria-label*="send" i]',
                    'button.ms-Button--primary[title*="Send"]',
                    # Fallback: look for any button containing "Send" text
                    'button:has-text("Send")',
                    'button:has-text("发送")',
                ]

                sent = False
                for sel in send_selectors:
                    try:
                        btn = page.wait_for_selector(sel, timeout=5000)
                        if btn and btn.is_visible():
                            btn.click()
                            sent = True
                            logger.info("Clicked send button: %s", sel)
                            break
                    except PwTimeout:
                        continue
                    except Exception:
                        continue

                if not sent:
                    # Last resort: try keyboard shortcut Ctrl+Enter
                    page.keyboard.press("Control+Enter")
                    logger.info("Tried Ctrl+Enter as fallback")
                    page.wait_for_timeout(2000)

                # Step 4: Wait for the compose window to close (means send succeeded)
                page.wait_for_timeout(3000)

                # Check for error toasts
                error_text = None
                try:
                    error_el = page.wait_for_selector(
                        '[role="alert"], .ms-MessageBar--error, [data-automation-id="errorMessage"]',
                        timeout=2000,
                    )
                    if error_el:
                        error_text = error_el.inner_text()
                except PwTimeout:
                    pass  # no error = good

                context.close()
                browser.close()

                if error_text:
                    return {"success": False, "error": f"Outlook Web error: {error_text}"}

                return {
                    "success": True,
                    "message": f"Email sent to {to} via Outlook Web (HKU)",
                }

        except ImportError:
            return {
                "success": False,
                "error": "Playwright not installed. Run: pip install playwright && playwright install chromium",
            }
        except Exception as e:
            logger.exception("Outlook Web send failed")
            return {"success": False, "error": str(e)}
