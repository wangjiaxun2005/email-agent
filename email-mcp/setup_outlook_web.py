#!/usr/bin/env python3
"""
setup_outlook_web.py — One-time login setup for Outlook Web automation.

Opens a Chromium browser window pointed at Outlook Web.
Log in with your HKU account (@connect.hku.hk), then come back
to this terminal and press Enter. The browser session (cookies,
localStorage) is saved so the email-mcp server can reuse it
to send emails without needing your password ever again.

Prerequisites:
    pip install playwright
    playwright install chromium

Usage:
    python setup_outlook_web.py
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
AUTH_FILE = HERE / "outlook_auth.json"
OUTLOOK_URL = "https://outlook.office.com/mail/"

BANNER = """
╔══════════════════════════════════════════════════════╗
║     Outlook Web — Email Agent 登录设置              ║
║     让 AI 通过你的 HKU 网页邮箱自动发信             ║
╚══════════════════════════════════════════════════════╝
"""


def main():
    print(BANNER)

    # Import Playwright (fail early with a clear message)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ Playwright 未安装。请先运行：")
        print("   pip install playwright")
        print("   playwright install chromium")
        sys.exit(1)

    print("📱 即将打开浏览器，请在浏览器中登录你的 HKU 邮箱")
    print("   (https://outlook.office.com)")
    print()
    print("   登录完成后，回到这里按 Enter 保存登录状态...")
    print()

    input("   准备好了就按 Enter 打开浏览器...")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-features=TranslateUI",
            ],
        )

        context = browser.new_context(
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

        print("🌐 正在打开 Outlook Web...")
        page.goto(OUTLOOK_URL, wait_until="domcontentloaded", timeout=30000)

        print()
        print("┌──────────────────────────────────────────────────┐")
        print("│  🔑 请在浏览器中完成以下步骤：                   │")
        print("│                                                  │")
        print("│  1. 用 HKU 账号登录 (xxx@connect.hku.hk)        │")
        print("│  2. 如果有 MFA，完成验证                         │")
        print("│  3. 看到收件箱页面后 → 回到这里按 Enter          │")
        print("│                                                  │")
        print("│  ⚠️  不要关闭浏览器窗口！                        │")
        print("└──────────────────────────────────────────────────┘")
        print()

        input("   登录完成后按 Enter 保存...")

        # Verify we're on the inbox page (not still on login)
        current_url = page.url.lower()
        if "login" in current_url or "microsoftonline" in current_url:
            print()
            print("⚠️  检测到你还在登录页面，还没完成登录。")
            retry = input("   重试？(y/n): ").strip().lower()
            if retry != "y":
                browser.close()
                sys.exit(1)
            input("   按 Enter 再次尝试保存...")

            current_url = page.url.lower()
            if "login" in current_url or "microsoftonline" in current_url:
                print("❌ 仍然在登录页面，请确认已成功登录后再运行此脚本。")
                browser.close()
                sys.exit(1)

        # Save auth state (cookies, localStorage, etc.)
        context.storage_state(path=str(AUTH_FILE))
        print(f"✓ 登录状态已保存到: {AUTH_FILE}")

        # Quick verify: grab user info from the page
        try:
            # Outlook Web usually shows the user's email in the top bar
            me_button = page.locator('[aria-label*="account"], [data-ogsr-primary]')
            if me_button.count() > 0:
                user_info = me_button.first.get_attribute("aria-label") or "已登录"
                print(f"✓ 检测到账号: {user_info}")
        except Exception:
            pass

        browser.close()

    print()
    print("✅ 设置完成！")
    print()
    print("   现在 email-mcp 的 email-send-hku 工具可以通过")
    print("   Outlook Web 自动发送邮件了。")
    print()
    print("   下次 AI 帮你发 HKU 邮件时，会在后台自动完成。")
    print()
    print("   ⚠️  如果发信时提示 session 过期（通常几周后），")
    print("   重新运行 python setup_outlook_web.py 即可。")
    print()


if __name__ == "__main__":
    main()
