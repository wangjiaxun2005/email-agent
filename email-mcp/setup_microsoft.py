#!/usr/bin/env python3
"""
setup_microsoft.py — One-time OAuth setup for Microsoft Graph API.

Uses Device Code Flow: prints a URL + code, you visit it on your phone/PC,
sign in with your Microsoft account (@connect.hku.hk), and it saves a
refresh token that email-mcp uses to send emails via Graph API.

Prerequisites (do these BEFORE running this script):
  1. Go to https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade
  2. Click "New registration"
  3. Name: "Email Agent" (or anything)
  4. Supported account types: "Accounts in any organizational directory"
  5. Redirect URI: Skip for now (not needed for device flow)
  6. Click "Register"
  7. Copy "Application (client) ID" → this is MICROSOFT_CLIENT_ID
  8. Go to "Certificates & secrets" → "New client secret"
  9. Copy the secret VALUE → this is MICROSOFT_CLIENT_SECRET
  10. Go to "API permissions" → "Add a permission" → "Microsoft Graph"
      → "Delegated permissions" → check "Mail.Send" → "Add permissions"

Usage:
    python setup_microsoft.py
    # Follow prompts, enter client ID and secret when asked
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error
import urllib.parse

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AUTHORITY = "https://login.microsoftonline.com/common"
SCOPES = ["Mail.Send", "offline_access"]
TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "microsoft_token.json")
ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

BANNER = """
╔══════════════════════════════════════════════════════╗
║     Microsoft Graph API — Email Agent Setup         ║
║     让 AI 通过你的 @connect.hku.hk 发邮件           ║
╚══════════════════════════════════════════════════════╝
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_input(prompt: str, env_var: str = "") -> str:
    """Get user input, optionally checking env var first."""
    if env_var:
        existing = os.getenv(env_var, "")
        if existing:
            print(f"  ✓ Found {env_var} in environment")
            return existing
    return input(prompt).strip()


def device_code_flow(client_id: str, client_secret: str) -> dict:
    """Run the device code OAuth flow. Returns tokens dict."""
    # Step 1: Request device code
    print("\n📱 Requesting device code from Microsoft...")

    device_data = urllib.parse.urlencode({
        "client_id": client_id,
        "scope": " ".join(SCOPES),
    }).encode("utf-8")

    device_req = urllib.request.Request(
        f"{AUTHORITY}/oauth2/v2.0/devicecode",
        data=device_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urllib.request.urlopen(device_req) as resp:
            device_result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"\n❌ Failed to get device code: HTTP {e.code}")
        print(f"   {error_body}")
        print(f"\n   Make sure MICROSOFT_CLIENT_ID is correct.")
        print(f"   It should look like: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
        sys.exit(1)

    user_code = device_result["user_code"]
    verification_uri = device_result["verification_uri"]
    device_code = device_result["device_code"]
    interval = int(device_result.get("interval", 5))
    expires_in = int(device_result.get("expires_in", 900))

    print()
    print("┌──────────────────────────────────────────────────┐")
    print("│  👆 请在手机或浏览器上完成这一步：               │")
    print("│                                                  │")
    print(f"│  1. 打开: {verification_uri}          │")
    print(f"│  2. 输入代码: {user_code}              │")
    print("│  3. 用你的 HKU 账号登录                         │")
    print(f"│                                                  │")
    print(f"│  ⏰ 代码有效期: {expires_in // 60} 分钟                       │")
    print("└──────────────────────────────────────────────────┘")
    print()

    # Step 2: Poll for token
    print("⏳ 等待你完成登录...", end="", flush=True)
    start = time.time()
    while time.time() - start < expires_in:
        time.sleep(interval)
        print(".", end="", flush=True)

        token_data = urllib.parse.urlencode({
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "device_code": device_code,
        }).encode("utf-8")

        token_req = urllib.request.Request(
            f"{AUTHORITY}/oauth2/v2.0/token",
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        try:
            with urllib.request.urlopen(token_req) as resp:
                token_result = json.loads(resp.read().decode("utf-8"))
                print(" ✅")
                return token_result
        except urllib.error.HTTPError as e:
            error_data = json.loads(e.read().decode("utf-8", errors="replace"))
            error = error_data.get("error", "")
            if error == "authorization_pending":
                continue  # user hasn't entered the code yet
            elif error == "slow_down":
                interval += 5  # Microsoft asked us to slow down
                continue
            elif error == "expired_token":
                print(f"\n❌ 代码已过期，请重新运行 setup_microsoft.py")
                sys.exit(1)
            else:
                print(f"\n❌ Token 获取失败: {error}")
                print(f"   {error_data}")
                sys.exit(1)

    print(f"\n❌ 超时：代码已过期，请重新运行")
    sys.exit(1)


def update_env_file(client_id: str, client_secret: str):
    """Add or update MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET in .env file."""
    if not os.path.exists(ENV_FILE):
        print("⚠️  .env file not found, creating new one...")
        with open(ENV_FILE, "w") as f:
            f.write("# Email Agent — Microsoft Graph API\n")
            f.write(f"MICROSOFT_CLIENT_ID={client_id}\n")
            f.write(f"MICROSOFT_CLIENT_SECRET={client_secret}\n")
        print(f"✓ Created {ENV_FILE}")
        return

    with open(ENV_FILE, "r") as f:
        lines = f.readlines()

    updated = {"client_id": False, "client_secret": False}
    new_lines = []
    for line in lines:
        if line.startswith("MICROSOFT_CLIENT_ID="):
            new_lines.append(f"MICROSOFT_CLIENT_ID={client_id}\n")
            updated["client_id"] = True
        elif line.startswith("MICROSOFT_CLIENT_SECRET="):
            new_lines.append(f"MICROSOFT_CLIENT_SECRET={client_secret}\n")
            updated["client_secret"] = True
        else:
            new_lines.append(line)

    if not updated["client_id"]:
        new_lines.append(f"MICROSOFT_CLIENT_ID={client_id}\n")
    if not updated["client_secret"]:
        new_lines.append(f"MICROSOFT_CLIENT_SECRET={client_secret}\n")

    with open(ENV_FILE, "r+") as f:
        f.writelines(new_lines)

    print(f"✓ Updated {ENV_FILE}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(BANNER)

    # Step 1: Get client credentials
    print("📋 第一步: Azure 应用注册信息")
    print("   (如果还没注册，请看脚本开头的 Prerequisites)")
    print()

    client_id = get_input(
        "   输入 MICROSOFT_CLIENT_ID: ",
        env_var="MICROSOFT_CLIENT_ID",
    )
    client_secret = get_input(
        "   输入 MICROSOFT_CLIENT_SECRET: ",
        env_var="MICROSOFT_CLIENT_SECRET",
    )

    if not client_id or not client_secret:
        print("❌ client_id 和 client_secret 不能为空")
        sys.exit(1)

    # Step 2: Device code flow
    print("\n📋 第二步: 登录 Microsoft 账号")
    tokens = device_code_flow(client_id, client_secret)

    # Step 3: Save tokens
    refresh_token = tokens.get("refresh_token", "")
    if not refresh_token:
        print("❌ 未收到 refresh_token，请确认已勾选 offline_access scope")
        sys.exit(1)

    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        json.dump({
            "refresh_token": refresh_token,
            "created_at": time.time(),
        }, f, indent=2)

    print(f"✓ Refresh token 已保存到: {TOKEN_FILE}")

    # Step 4: Update .env
    update_env_file(client_id, client_secret)

    # Step 5: Verify
    print("\n📋 第三步: 验证配置...")
    # Add current dir to path so we can import microsoft_graph
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from microsoft_graph import MicrosoftGraphClient, MicrosoftGraphConfig

    config = MicrosoftGraphConfig()
    err = config.validate()
    if err:
        print(f"❌ 配置验证失败: {err}")
        sys.exit(1)

    client = MicrosoftGraphClient(config)
    result = client.whoami()
    if result.get("success"):
        print(f"✓ 验证成功！已连接为: {result['email']} ({result['display_name']})")
    else:
        print(f"⚠️  验证失败: {result.get('error', '')}")
        print("   Token 可能还需要一点时间生效，稍后重试即可。")

    # Step 6: Reminder about .mcp.json
    print()
    print("┌──────────────────────────────────────────────────┐")
    print("│  ✅ 设置完成！接下来需要更新 .mcp.json：         │")
    print("│                                                  │")
    print("│  在 .mcp.json 的 email-agent env 中添加：        │")
    print(f"│  MICROSOFT_CLIENT_ID={client_id}")
    print(f"│  MICROSOFT_CLIENT_SECRET={client_secret}")
    print("│                                                  │")
    print("│  还要更新 ~/.cc-connect/system-prompt.md         │")
    print("│  让 AI 知道可以用 email-send-microsoft 发 HKU 信 │")
    print("└──────────────────────────────────────────────────┘")
    print()
    print("🌈 搞定！现在 AI 可以通过你的 HKU 邮箱发信了。")


if __name__ == "__main__":
    main()
