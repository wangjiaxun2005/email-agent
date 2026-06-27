# Email Agent — AI 邮件助手

微信里的 AI 邮件秘书。查邮件、读全文、分轻重缓急、帮你记住待办——看完微信就不用再看邮箱。

## 架构

```
手机微信 ←→ cc-connect ←→ Claude Code + email-mcp
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
         查邮件 (IMAP)   发 Gmail (SMTP)   发 HKU (Graph API)
```

## 项目结构

| 目录/文件 | 说明 |
|-----------|------|
| `email-mcp/` | Python MCP 服务器，提供查/搜/发邮件工具 |
| `email-mcp/examples/` | 系统模板：system prompt、用户档案、待办清单 |
| `email.sh` | HKU 邮箱设置脚本 |
| `.mcp.json.template` | MCP 配置模板，复制为 `.mcp.json` 后填入凭据 |

## 快速开始

### 1. 安装依赖

```bash
cd email-mcp
pip install -r requirements.txt
playwright install chromium   # HKU 发信需要
```

### 2. 配置凭据

```bash
cp .mcp.json.template .mcp.json
# 编辑 .mcp.json，填入 IMAP/SMTP 信息
# 或在 email-mcp/ 下创建 .env 文件
```

### 3. 注册 MCP 服务器

Claude Code 自动识别工作区根目录的 `.mcp.json`。用 `claude mcp list` 确认 `email-agent` 已注册。

### 4. 配置 cc-connect（微信接入）

```bash
npm install -g @atticux/cc-connect
```

在 `~/.cc-connect/config.toml` 中指向本工作区：

```toml
[projects.agent]
type = "claudecode"
system_prompt_file = "email-mcp/examples/system-prompt.md"

[projects.agent.options]
work_dir = "/path/to/email-agent"
mode = "auto"
```

启动：`cc-connect daemon start`

## MCP 工具

| 工具 | 功能 |
|------|------|
| `email_digest` | 获取未读邮件摘要列表 |
| `email_list` | 列出文件夹邮件 |
| `email_read` | 读取邮件全文 |
| `email_search` | 搜索邮件 |
| `email_send` | 通过 Gmail SMTP 发送 |
| `email_send_microsoft` | 通过 Microsoft Graph API 发送 (HKU) |
| `email_send_hku` | 通过 Outlook Web 发送 (HKU 备选) |

## 邮件分级系统

| 级别 | 含义 | 示例 |
|------|------|------|
| 🚨 紧急 | 需立即行动 | 账户安全告警、24h 内截止、真人直接发你 |
| 📌 重要 | 需要关注 | TA/RA/实习机会、需回复的邮件、学校行政 |
| 📋 留意 | 可能有用 | CDS/CS 讲座、工作推荐、信用卡账单 |
| 📎 普通 | 知道就行 | 非相关学院群发、系统通知 |
| 🗑️ 广告 | 跳过 | 商业推广、社团招募 |

## 微信命令

| 命令 | 作用 |
|------|------|
| `checke` / `查邮件` | 扫描未读邮件并更新待办 |
| `a` / `看a` | 查看字母编号对应的邮件详情 |
| `a搞定` | 标记待办为已完成 |
| `加一个🚨：xxx` | 手动添加待办 |
| `清单` / `待办` | 只看待办清单 |
| `rearrange` / `重排` | 重新排序待办 |

## 姊妹项目

- **[ultimate-bar](https://github.com/wangjiaxun2005/ultimate-bar)** — macOS 菜单栏控制台，管理 cc-connect 守护进程

## License

MIT
