# 📧 Email Agent — 用户指南

## 架构

```
手机微信 ↔ cc-connect ↔ Claude Code + email-mcp
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
       查邮件 (IMAP)   发 Gmail (SMTP)   发 HKU (Graph API)
            │               │               │
       @gmail.com        @gmail.com      @connect.hku.hk
```

## 启动

**开机自动启动**，不需要手动操作。

## 微信内控制命令

| 命令 | 作用 |
|------|------|
| `/restart` | 切新 session |
| `/compress` | 压缩上下文 |
| `/status` | 查看 session 状态 |
| `/quiet` | 开关静默 |
| `/whoami` | 查看用户 ID |

---

## AI 怎么判断邮件重要性

AI 根据你的身份（HKU CDS 学生）和邮件内容自动五层分级：

| 级别 | 判断规则 | 举例 |
|------|----------|------|
| 🚨 紧急 | 真人直接找你、安全告警、扣费异常、24h截止 | Si Chen 回复TA申请、Google 安全提醒 |
| 📌 重要 | 需要回复、TA/RA/实习机会（含群发）、学校行政需操作 | CEDARS STEM 实习、学分转换 |
| 📋 留意 | CDS 相关讲座、LinkedIn 工作推荐、服务更新、退款追踪 | CDS Seminar、Jobro 推荐 |
| 📎 普通 | 非 CDS 学院群发、系统通知、日常消费提醒 | 医学院讲座、麦当劳刷卡 |
| 🗑️ 广告 | 商业推广、HKU 社团招募 | Klook、空手道招新 |

### HKU 邮件特殊处理
虽然是 @hku.hk 域名一发一大堆，但 AI 会按内容区分：
- 📌 TA/RA/实习机会自动升级（比如 CEDARS STEM、学院 TA 招募）
- 📋 CDS 相关的讲座活动
- 📎 其他学院的你不管
- 🗑️ 社团招募直接忽略

---

## 待办清单系统

AI 自动把邮件整理成两区展示：

| 区域 | 内容 | 持久化 |
|------|------|--------|
| 🆕 本轮新增 | **所有**新邮件，五级全列 | 只有 🚨📌📋 入文件 |
| 📋 待办清单 | 需要你行动的追踪项 | 全部入文件 |

### 交互方式

| 你说 | AI 做 |
|------|------|
| `checke` / `查邮件` | 全量查邮件 + 两区展示 |
| `a` `看a` `读a` | 读那封邮件全文 |
| `a搞定` `a done` | 划掉这条 |
| `加一个🚨：周四回张教授` | 手动加待办，可指定等级 |
| `清单` `待办` | 只列 📋 待办清单 |
| `清理` | 清空已处理记录 |
| `rearrange` `重排` | 合并两区 + 按等级重排 + 从 a 重新编号 |
| `状态` `心跳` | 查心跳是否正常 |

### checke 推送示例

```
🆕 本轮新增

🚨 d) Google — 账户安全告警，需立即确认

📌 e) CEDARS — 新实习机会，6/30截止
📌 f) AWS — 本月扣费$14.20

📋 CDS Seminar — 7/3 下午 AI 讲座
📋 LinkedIn — 3 个新工作推荐

📎 医学院 — 研究讲座通知
📎 Google — 隐私政策更新

🗑️ Klook — 暑期优惠
🗑️ 空手道社 — 招募新成员

──────────────

📋 待办清单
🚨 0 件 · 📌 2 件 · 📋 1 件

📌 a) CEDARS — ITC STEM实习，6/29截止
📌 b) HKU-SAAS — MS/Nomura 实习活动
📋 c) Figma — 退款$40等入账

说字母看详情，「搞定+字母」划掉
```

### 文件位置
`~/.cc-connect/tasks.md` — 重启/切 session 不丢

---

## 微信 AI 功能

### 查邮件

| 你说 | AI 做什么 |
|------|----------|
| `嗨` `在吗` | 主动检查 + 更新待办清单 |
| `checke` `查邮件` | 全量展示，🆕区 + 📋区 |
| `搜 实习` `找 Amazon` | 搜索邮件 |

### 发邮件

| 你说 | AI 做什么 |
|------|------|
| `帮我回这封` | 念内容让你确认 → 发送 |
| `用 Gmail 发给 xxx` | 从 @gmail.com 发出 |
| `用 HKU 发给 xxx` | 从 @connect.hku.hk 发出 |
| 回复 HKU 的邮件 | AI 自动选 HKU 发信 |

### AI 的风格
- 🇨🇳 中文口语化，像朋友在聊天
- 📱 手机一屏能看完
- 🎯 直接说事，不追问「要不要看」
- 🤫 没事就说「没有新邮件，也没有待办 👌」

### 主动检查
你每次发消息，AI 先扫一眼新邮件：
- 新邮件 → 🆕 区全量展示（五级都列）
- 旧待办 → 📋 区列出追踪项
- 都没有 → 简短说一声

---

## MCP 工具

| 工具 | 功能 | 发信方 |
|------|------|--------|
| `email-list` | 列出邮件 | — |
| `email-read` | 读全文 | — |
| `email-send` | 发邮件 | @gmail.com |
| `email-search` | 搜索 | — |
| `email-digest` | 今日摘要 | — |
| `email-send-microsoft` | 发邮件（Graph API） | @connect.hku.hk |

---

## 终端命令（出问题时用）

```bash
cc-connect daemon restart    # 重启 daemon
cc-connect daemon logs -f    # 实时日志
cc-connect weixin setup      # iLink 过期 → 重新扫码
```

---

## 配置文件

| 文件 | 作用 |
|------|------|
| `~/.cc-connect/config.toml` | cc-connect 主配置 |
| `~/.cc-connect/system-prompt.md` | AI 行为规则 |
| `~/.cc-connect/tasks.md` | 待办清单（持久化） |
| `~/ME/email-mcp/.env` | 邮箱配置 |

---

## 故障排查

### AI 没回复
微信发 `/restart`

### ret=-2 错误
```bash
cc-connect weixin setup --project email-agent
```

### 连不上 Gmail
Shadowrocket → 规则 → 加 `DOMAIN,gmail.com,DIRECT` 和 `DOMAIN,google.com,DIRECT`
