#!/usr/bin/env bash
# ============================================================
# email.sh — Email Agent 独有功能（cc-connect 不提供的）
# ============================================================
set -euo pipefail

case "${1:-}" in
  hku-setup)
    cd /path/to/email-mcp && python3 setup_outlook_web.py
    ;;
  hku-test)
    cd /path/to/email-mcp && python3 -c "
from outlook_web_send import OutlookWebSender
r = OutlookWebSender().send_email('your-email@gmail.com', '🧪 HKU 发信测试', '测试成功！')
print(r)
"
    ;;
  *)
    echo "📧 Email Agent"
    echo ""
    echo "  ./email.sh hku-setup    重新登录 Outlook Web"
    echo "  ./email.sh hku-test     测试 HKU 发信"
    echo ""
    echo "  其他操作用 cc-connect："
    echo "    cc-connect daemon restart   重启"
    echo "    cc-connect daemon logs -f   实时日志"
    echo "    cc-connect weixin setup     重新扫码"
    echo ""
    echo "  微信里直接发：/restart /compress /status /quiet"
    ;;
esac
