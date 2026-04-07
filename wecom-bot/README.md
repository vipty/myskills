# wecom-bot

通过企业微信群机器人 Webhook，向指定群聊发送消息、文件、图片。

## 安装

```bash
cp -r wecom-bot ~/.claude/skills/wecom-bot
```

## 首次配置

安装后，在 Claude Code 中运行：

```
/qw-robot config add main <你的-Webhook-Key>
```

Webhook Key 在企业微信管理后台 → 群机器人 → 详情 中获取，格式为 UUID（如 `a0b5a761-xxxx-xxxx-xxxx-xxxxxxxxxxxx`），也可以粘贴完整的 Webhook URL。

## 使用方式

直接用自然语言描述，Claude 自动调用：

```
发条消息：今天下午 3 点开会
把这份报告发给我
发个告警：数据库连接超时
@所有人 说明天放假
```

## 多机器人

```bash
/qw-robot config add alert <key>    # 添加告警机器人
/qw-robot config add report <key>   # 添加报表机器人
/qw-robot config list               # 查看所有机器人
```

## 注意事项

- `config.json` 含有 Webhook Key，**不要提交到 git**（已在 `.gitignore` 中排除）
- 每个机器人每分钟最多发送 20 条消息
- 需要 Python 3.10+
