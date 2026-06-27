# Email Agent — Workspace

这是 cc-connect 的 Claude Code 工作区。包含 AI 邮件助手运行所需的配置。

## 依赖

- **[email-mcp](../email-mcp/)** — Python MCP 邮件服务器（独立仓库）
- **[email-agent-bar](../email-agent-bar/)** — macOS 菜单栏应用（独立仓库）
- **[cc-connect](https://www.npmjs.com/package/@atticux/cc-connect)** — 微信 ↔ Claude Code 桥接

## 文件说明

| 文件 | 用途 |
|------|------|
| `.mcp.json` | MCP 服务器注册配置 |
| `.claude/settings.json` | Claude Code 权限 |
| `.claude/scheduled_tasks.json` | 定时任务（自动 checke） |
| `email.sh` | HKU 邮件设置脚本 |
| `USER_GUIDE.md` | 完整使用指南 |

⚠️ 此仓库**不推远程** — `.mcp.json` 包含邮箱密码。
