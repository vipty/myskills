# myskills

个人 Claude Code 技能集。

## 技能列表

| 技能 | 说明 |
|------|------|
| [wecom-bot](./wecom-bot/) | 通过企业微信群机器人 Webhook 发送消息、文件、图片 |

---

## 安装方法

将技能目录复制到 Claude Code 的 skills 目录：

```bash
# 克隆仓库
git clone https://github.com/vipty/myskills.git

# 安装单个技能（以 wecom-bot 为例）
cp -r myskills/wecom-bot ~/.claude/skills/wecom-bot
```

安装后无需重启，Claude Code 会自动识别新技能。
