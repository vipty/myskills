# 企业微信机器人 API 参考

> 官方文档：https://developer.work.weixin.qq.com/document/path/99110  
> 最后整理：2026-04-03

---

## 基础信息

- **Webhook 地址格式**：`https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=KEY`
- **文件上传地址**：`https://qyapi.weixin.qq.com/cgi-bin/webhook/upload_media?key=KEY&type=TYPE`
- **发送频率限制**：每个机器人每分钟最多 **20 条**消息
- **所有请求**：POST，Content-Type: application/json（文件上传用 multipart/form-data）

---

## 消息类型速查

| msgtype | 说明 | 大小限制 |
|---------|------|---------|
| `text` | 纯文本，可 @成员 | ≤ 2048 字节 |
| `markdown` | Markdown（支持颜色/@） | — |
| `markdown_v2` | Markdown v2（支持表格，需新版客户端） | — |
| `image` | 图片（base64） | ≤ 2MB，JPG/PNG |
| `news` | 图文卡片（1-8 条） | — |
| `file` | 文件附件（需先上传） | ≤ 20MB |
| `voice` | 语音（需先上传） | ≤ 2MB，≤60s，AMR |
| `template_card` | 模板卡片（文本通知/图文展示） | — |

---

## 各类型消息格式

### 1. 文本消息

```json
{
  "msgtype": "text",
  "text": {
    "content": "消息内容，最长 2048 字节",
    "mentioned_list": ["userid1", "@all"],
    "mentioned_mobile_list": ["13800001111", "@all"]
  }
}
```

- `mentioned_list`：按 userid 提醒，`@all` 提醒所有人
- `mentioned_mobile_list`：按手机号提醒

---

### 2. Markdown 消息

```json
{
  "msgtype": "markdown",
  "markdown": {
    "content": "## 标题\n**加粗** `代码` [链接](http://example.com)\n<font color=\"warning\">警告色文字</font>"
  }
}
```

**支持的语法子集：**
- 标题：`#`（一级）、`##`（二级）
- 加粗：`**text**`
- 链接：`[title](url)`
- 行内代码：`` `code` ``
- 引用：`> text`
- 字体颜色：`<font color="info|warning|comment">text</font>`

---

### 3. Markdown v2 消息

```json
{
  "msgtype": "markdown_v2",
  "markdown_v2": {
    "content": "## 标题\n| 列1 | 列2 |\n|---|---|\n| A | B |"
  }
}
```

- 支持完整 Markdown（表格、分割线等）
- **不支持** 字体颜色和 @群成员
- 需要客户端版本 ≥ 4.1.36（安卓 ≥ 4.1.38），旧版降级为纯文本

---

### 4. 图片消息

```json
{
  "msgtype": "image",
  "image": {
    "base64": "图片Base64编码",
    "md5": "图片MD5值"
  }
}
```

- 图片先转 base64，md5 用于校验
- 仅支持 JPG / PNG，≤ 2MB

---

### 5. 图文消息

```json
{
  "msgtype": "news",
  "news": {
    "articles": [
      {
        "title": "标题（必填）",
        "description": "描述（可选）",
        "url": "点击跳转链接（必填）",
        "picurl": "封面图片链接（可选，建议 1068×455）"
      }
    ]
  }
}
```

- 1 到 8 条图文

---

### 6. 文件消息

**步骤一：上传文件**

```http
POST https://qyapi.weixin.qq.com/cgi-bin/webhook/upload_media?key=KEY&type=file
Content-Type: multipart/form-data

表单字段: media = <文件内容>
```

返回：
```json
{
  "errcode": 0,
  "errmsg": "ok",
  "type": "file",
  "media_id": "MEDIA_ID",
  "created_at": "1380000000"
}
```

**步骤二：发送文件**

```json
{
  "msgtype": "file",
  "file": {
    "media_id": "上传后的 media_id"
  }
}
```

- `media_id` 有效期 **3 天**
- 文件大小 ≤ **20MB**

---

### 7. 语音消息

- 同文件上传流程，但 `type=voice`
- 仅支持 **AMR** 格式
- 大小 ≤ 2MB，时长 ≤ 60 秒

```json
{
  "msgtype": "voice",
  "voice": {
    "media_id": "MEDIA_ID"
  }
}
```

---

### 8. 模板卡片 - 文本通知

```json
{
  "msgtype": "template_card",
  "template_card": {
    "card_type": "text_notice",
    "source": {
      "icon_url": "图标URL",
      "desc": "来源描述",
      "desc_color": 0
    },
    "main_title": {
      "title": "主标题",
      "desc": "副标题"
    },
    "emphasis_content": {
      "title": "重点数据",
      "desc": "数据说明"
    },
    "quote_area": {
      "type": 1,
      "url": "链接",
      "title": "引用标题",
      "quote_text": "引用内容"
    },
    "sub_title_text": "正文内容",
    "horizontal_content_list": [
      {"keyname": "关键词", "value": "值"}
    ],
    "jump_list": [
      {"type": 1, "url": "链接", "title": "跳转文字"}
    ],
    "card_action": {
      "type": 1,
      "url": "整体点击跳转链接"
    }
  }
}
```

---

## 返回码说明

| errcode | 说明 |
|---------|------|
| 0 | 成功 |
| 93000 | 机器人已停用 |
| 93004 | 机器人webhook地址不合法 |
| 93008 | 超过消息发送频率限制 |

---

## 注意事项

1. **Webhook Key 需保密**，泄露后立即在企业微信后台重置
2. 发送频率超过 20 条/分钟会被限流（errcode: 93008）
3. `media_id` 只有 3 天有效期，不要长期保存
4. Markdown v2 建议先检测客户端版本再使用
