---
name: wecom-bot
description: "Send messages and files to a WeCom group via robot Webhook. Supports text, Markdown, images, files, voice, news cards, template cards. Triggers: 企业微信机器人, 发送到企业微信, 发给我, 推送通知, wecom bot, webhook 发消息, qyapi.weixin.qq.com, 发消息, 发文件, 发图片, 发报告, 告警通知."
---

# 企业微信机器人（WeCom Bot）技能

## 概述

通过企业微信群机器人 Webhook，向指定群聊发送各类消息和文件。支持配置**多个机器人**，通过 `--bot` 参数切换，默认机器人免参数。

> ✨ **默认启用自动 Markdown 美化**：发送文本消息时，AI 会自动将内容格式化为美观的 Markdown，无需手动排版。如需发送纯文本，在命令末尾加 `--no-md`。

---

## 🧠 自然语言交互（推荐方式）

用户**无需记住任何命令**，直接用日常语言描述意图，AI 自动判断并调用正确的发送方式。

---

### 💬 发送文本消息（自动 Markdown 美化）

AI 收到文本内容后，**自动美化为 Markdown** 再发送，包括：
- 根据关键词添加 emoji 标题（📅开会 / 🚨告警 / 📢通知 / ⏰提醒 / 🚀部署 …）
- 关键时间词高亮（今天下午3点 → `` `今天下午3点` ``）
- 键值对内容自动格式化为引用块列表
- @所有人 / @指定成员 自动追加到末尾

| 用户说 | AI 执行 | 美化效果示例 |
|--------|---------|------------|
| "发条消息：今天下午 3 点开会" | `text "今天下午 3 点开会"` | 📅 **`今天下午 3 点`开会** |
| "通知大家服务器重启了" | `text "通知：服务器重启了"` | 📢 **通知：服务器重启了** |
| "发个告警：数据库连接超时" | `text "告警：数据库连接超时"` | 🚨 **告警：数据库连接超时** |
| "提醒大家明天不上班" | `text "提醒大家明天不上班"` | ⏰ **提醒大家`明天`不上班** |
| "发通知 @所有人，今天不上班" | `text "通知：今天不上班" --at-all` | 末尾自动追加 `<@all>` |
| "@张三 说下周一开会" | `text "下周一开会" --at-users 张三` | 末尾自动追加 `<@张三>` |
| "发纯文本消息：Hello" | `text "Hello" --no-md` | 原样发送，不美化 |

**多行键值对消息**（自动格式化为结构化引用块）：

用户说：
```
发部署通知
环境：生产环境
版本：v2.1.0
时间：15:00
```

美化后发送效果：
```markdown
🚀 **部署通知**
> **环境**：生产环境
> **版本**：v2.1.0
> **时间**：`15:00`
```

---

### 📄 发送文件

| 用户说 | AI 执行 |
|--------|---------|
| "把这份报告发给我" | 查找当前上下文最近生成的文件，调用 `file` 发送 |
| "把刚才生成的文件发到企业微信" | 从最近工具输出中提取文件路径，调用 `file` 发送 |
| "发送 PDF 给我" | 查找 .pdf 文件，调用 `file` 发送 |
| "把技能手册发过来" | 查找名称匹配的 .md/.pdf 文件，调用 `file` 发送 |
| "上传这份文档" | 调用 `file` 发送文件 |

**AI 解析规则（文件指代）：**
- "这份"、"刚才"、"最新的"、"生成的" → 优先从当前对话上下文查找最近的文件路径
- 若未找到，使用 `find` 命令搜索工作区最近修改的文件
- 支持扩展名提示：提到"PDF/文档/报告/手册/表格"时对应过滤文件类型

---

### 🖼️ 发送图片

| 用户说 | AI 执行 |
|--------|---------|
| "把截图发过去" | 查找 .png/.jpg 文件，调用 `image` 发送 |
| "发送这张图片到企业微信" | `image /path/to/image.png` |
| "把生成的图表发给我" | 查找最近生成的图片文件，调用 `image` 发送 |

---

### 📋 发送 Markdown 文件

| 用户说 | AI 执行 |
|--------|---------|
| "发送 Markdown 格式的更新日志" | `markdown --file changelog.md` |
| "把 README 发到群里" | `markdown --file README.md`（内容超 4096 字节则自动改用 `file` 发送）|
| "以 Markdown 格式发周报" | `markdown --file weekly-report.md` |

> ⚠️ **重要**：Markdown 内容超过 4096 字节时，自动改用 `file` 发送附件，避免截断。

---

### ⚠️ 告警场景

| 用户说 | AI 执行 |
|--------|---------|
| "发个告警：数据库连接超时" | `text "告警：数据库连接超时"` → 自动美化为 🚨 格式 |
| "发送警告通知" | 优先使用名为 `alert` 的机器人，不存在则用默认机器人 |
| "发一条 P0 告警通知所有人" | `text "P0 告警" --at-all` |

---

### 🤖 多机器人场景

| 用户说 | AI 执行 |
|--------|---------|
| "用 alert 机器人发" | `--bot alert ...` |
| "切换到 report 机器人发报告" | `--bot report file /path/to/report` |
| "用默认机器人发" | 不加 `--bot` 参数 |
| "帮我查看有哪些机器人" | 读取 config.json，展示所有已配置机器人 |

---

## 📝 完整发送提示词参考

以下是所有可触发本技能的完整自然语言提示词，AI 会自动识别并调用对应功能：

### 文本 / 通知类
```
发条消息：[内容]
发一条通知：[内容]
在群里说：[内容]
告诉大家：[内容]
群里通知一下：[内容]
发个提醒：[内容]
发条提醒说[内容]
帮我发消息到企业微信：[内容]
推送一条消息：[内容]
发个告警：[内容]
发一条告警通知：[内容]
@所有人 说[内容]
通知所有人：[内容]
```

### 文件类
```
把这份报告发给我
把[文件名]发到企业微信
发送 PDF 给我
把刚才生成的文件发过去
把最新的文档发给我
发这份 Excel 到群里
上传这份文件到企业微信
把[xxx]文件发一下
```

### 图片类
```
把截图发过去
发这张图片到群里
把生成的图表发给我
发图片：[路径]
把图发过去
```

### Markdown / 报告类
```
发送 Markdown 格式的[内容]
把 README 发到群里
以 Markdown 格式发[内容]
发周报到企业微信
把报告以 Markdown 发出去
```

### @提及类
```
发通知 @所有人，[内容]
@all 说[内容]
@张三 通知[内容]
发消息 @[用户名] 说[内容]
通知[用户名]：[内容]
```

### 配置 / 管理类
```
帮我查看有哪些机器人
查看企业微信机器人配置
添加机器人 [名称] [key]
设置默认机器人为 [名称]
删除机器人 [名称]
用 [机器人名] 机器人发消息
```

---

## ⚙️ 机器人配置命令

通过斜杠命令管理机器人（首次使用时配置）：

| 命令 | 说明 |
|------|------|
| `/qw-robot` | 显示帮助信息 |
| `/qw-robot config list` | 查看所有已配置的机器人 |
| `/qw-robot config add <名称> <key>` | 添加机器人（支持 URL 或纯 Key） |
| `/qw-robot config default <key>` | 快速设置默认机器人 |
| `/qw-robot config default <名称>` | 按名称设置默认机器人 |
| `/qw-robot config set <名称> <key>` | 更新已有机器人的 Key |
| `/qw-robot config remove <名称>` | 删除机器人 |
| `/qw-robot config info [名称]` | 查看机器人详细信息 |

**快速配置示例：**
```bash
# 最简单：直接用 Key 配置默认机器人
/qw-robot config default xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# 添加命名机器人
/qw-robot config add alert <key>
/qw-robot config add report <key>
```

---

## 📁 配置文件

位置：`~/.workbuddy/skills/wecom-bot/config.json`

```json
{
  "default": "main",
  "bots": {
    "main": {
      "key": "your_key_here",
      "description": "默认机器人"
    },
    "alert": {
      "key": "your_key_here",
      "description": "告警通知"
    }
  }
}
```

---

## 📨 消息类型速查

| 类型 | 命令 | 限制 |
|------|------|------|
| 文本（自动 Markdown 美化） | `text "内容"` | ≤ 2048 字节（纯文本模式加 `--no-md`） |
| Markdown 文件 | `markdown --file file.md` | ≤ 4096 字节，超出自动改发文件 |
| 文件附件 | `file /path/to/doc.pdf` | ≤ 20MB |
| 图片 | `image /path/photo.png` | ≤ 2MB，JPG/PNG |
| 语音 | `voice /path/audio.amr` | ≤ 2MB，≤ 60 秒，AMR 格式 |
| 图文卡片 | `news '[{"title":"标题","url":"..."}]'` | 1-8 条 |

---

## 🔧 脚本调用方式（AI 内部使用）

> **⚠️ 路径说明**：在调用脚本前，先用以下命令确认实际安装路径：
> ```bash
> find ~/.claude/skills ~/.workbuddy/skills ~/.*skills -name "send_wecom.py" 2>/dev/null | head -1
> ```
> 将下方示例中的 `<SCRIPT>` 替换为实际路径。

```bash
SCRIPT=$(find ~/.claude/skills ~/.workbuddy/skills ~/.*skills -name "send_wecom.py" 2>/dev/null | head -1)

# 发送文本（自动美化为 Markdown）
python3 "$SCRIPT" text "今天下午 3 点开会"

# 发送纯文本（禁用美化）
python3 "$SCRIPT" text "Hello" --no-md

# 发送文件
python3 "$SCRIPT" file /path/to/file

# 发送图片
python3 "$SCRIPT" image /path/to/image.png

# 指定机器人
python3 "$SCRIPT" --bot alert text "告警内容"

# @所有人
python3 "$SCRIPT" text "通知" --at-all

# @指定用户
python3 "$SCRIPT" text "通知" --at-users zhangsan lisi
```

---

## 🎨 自动 Markdown 美化规则

AI 在发送文本消息时，自动执行以下美化逻辑：

| 规则 | 触发条件 | 效果 |
|------|---------|------|
| emoji 标题 | 内容含「开会/会议」 | 📅 **加粗标题** |
| emoji 标题 | 内容含「通知/公告」 | 📢/📣 **加粗标题** |
| emoji 标题 | 内容含「提醒」 | ⏰ **加粗标题** |
| emoji 标题 | 内容含「告警/警告」 | 🚨/⚠️ **加粗标题** |
| emoji 标题 | 内容含「部署/上线」 | 🚀/🟢 **加粗标题** |
| emoji 标题 | 内容含「完成/成功」 | ✅ **加粗标题** |
| emoji 标题 | 内容含「失败/错误」 | ❌ **加粗标题** |
| 时间高亮 | 含「今天/明天/下午X点/15:00」等 | `` `时间` `` 代码块高亮 |
| 键值对格式化 | 含「键：值」结构 | `> **键**：值` 引用块 |
| @所有人 | `--at-all` 参数 | 末尾追加 `<@all>` |
| @指定用户 | `--at-users 用户名` | 末尾追加 `<@用户名>` |
| 禁用美化 | `--no-md` 参数 | 原样发送纯文本 |

---

## ❗ 错误处理

| 错误码 | 含义 | 处理方式 |
|--------|------|---------|
| `errcode: 0` | 发送成功 | - |
| `errcode: 40058` | 内容超过限制 | Markdown 改用 `file` 发送 |
| `errcode: 93008` | 超过频率限制（每分钟 ≤20 条）| 稍后重试 |
| `errcode: 93000` | 机器人已停用 | 检查机器人状态 |
| `errcode: 93004` | Webhook 地址不合法 | 重新配置 Key |
