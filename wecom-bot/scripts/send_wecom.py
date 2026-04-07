#!/usr/bin/env python3
"""
企业微信机器人消息发送工具（多机器人版）

支持通过 config.json 配置多个机器人，
自动读取默认机器人，也可用 --bot 参数指定。
支持斜杠命令：/qw-robot config ...
"""

import argparse
import base64
import hashlib
import json
import os
import re
import ssl
import sys
import urllib.request
import urllib.error
from pathlib import Path

# macOS Python SSL 证书修复
try:
    import certifi
    ssl_context = ssl.create_default_context(cafile=certifi.where())
except Exception:
    ssl_context = None  # 降级：不指定 cafile


BASE_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook"
SKILL_DIR = Path(__file__).parent.parent.resolve()
CONFIG_FILE = SKILL_DIR / "config.json"
SLASH_CMD = "/qw-robot"


# ─── Key 解析工具 ─────────────────────────────────────────────────────────────

def extract_key(raw: str) -> str:
    """
    从 URL 或 Key 字符串中提取 Webhook Key。
    - URL 格式：https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=XXX
    - 直接传入 Key：返回原值
    """
    raw = raw.strip()
    if raw.startswith("https://"):
        match = re.search(r"key=([a-zA-Z0-9-]+)", raw)
        if not match:
            raise ValueError(f"URL 中未找到 key 参数：{raw}")
        return match.group(1)
    if len(raw) >= 20 and "-" in raw:
        return raw
    raise ValueError(f"无法识别为有效的 Webhook Key 或 URL：{raw}")


# ─── 配置管理 ────────────────────────────────────────────────────────────────

def load_config() -> dict:
    """加载配置文件，不存在时自动创建默认配置。"""
    if not CONFIG_FILE.exists():
        default_cfg = {"default": "default", "bots": {}}
        CONFIG_FILE.write_text(json.dumps(default_cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\033[93m配置文件不存在，已创建默认配置：{CONFIG_FILE}\033[0m", file=sys.stderr)
        print(f"\033[93m请使用 /qw-robot config add <名称> <key> 添加机器人\033[0m\n", file=sys.stderr)
        return default_cfg
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_config(config: dict) -> None:
    """保存配置到文件。"""
    CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def list_bots(config: dict) -> None:
    """列出所有已配置的机器人。"""
    default = config.get("default", "")
    default_key = config.get("default-key", "")
    bots = config.get("bots", {})
    print(f"\n配置文件：{CONFIG_FILE}")
    print(f"{'─' * 52}")
    if not bots and not default_key:
        print("  （尚无机器人配置）")
        print(f"  使用 /qw-robot config add <名称> <key> 添加第一个机器人")
    if default_key:
        key_display = default_key[:6] + "****" + default_key[-4:]
        print(f"  \033[93m[透传]\033[0m  [当前默认]  key: {key_display}")
        print(f"           \033[3m（通过 /qw-robot config default <key> 设置，可用 /qw-robot config add 保存为命名机器人）\033[0m")
        if bots:
            print()
    for name, cfg in bots.items():
        tag = " [默认]" if name == default else ""
        desc = cfg.get("description", "")
        key = cfg.get("key", "")
        if len(key) > 12:
            key_display = key[:6] + "****" + key[-4:]
        else:
            key_display = "****"
        print(f"  \033[92m{name}\033[0m{tag}  {desc}")
        print(f"      key: {key_display}")
    print(f"{'─' * 52}")
    print(f"斜杠命令用法：")
    print(f"  /qw-robot config list                  # 查看所有机器人")
    print(f"  /qw-robot config add <名称> <key>      # 添加机器人")
    print(f"  /qw-robot config default <名称>         # 设置默认机器人")
    print(f"  /qw-robot config remove <名称>          # 删除机器人")


# ─── 斜杠命令处理器 ──────────────────────────────────────────────────────────

def handle_slash_command(args: list[str]) -> bool:
    """
    处理 /qw-robot 斜杠命令，返回 True 表示已处理（退出），False 继续。
    """
    if not args:
        return False

    first = args[0].lstrip("/")
    if first != SLASH_CMD.lstrip("/"):
        return False

    # 去掉前缀 /qw-robot
    raw = args[1:]
    if not raw:
        _print_slash_help()
        return  # never reached

    cmd = raw[0].lower()
    rest = raw[1:]

    try:
        if cmd in ("config", "cfg"):
            _handle_config(raw[1:])
        elif cmd in ("send", "text", "md", "markdown", "file", "image"):
            # 透传到普通模式
            return False
        else:
            print(f"\033[91m未知命令：{cmd}\033[0m")
            _print_slash_help()
    except Exception as e:
        print(f"\033[91m错误：{e}\033[0m", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)
    return True  # never reached


def _handle_config(args: list[str]) -> None:
    """处理 config 子命令。"""
    if not args:
        _print_slash_help()
        return
    sub = args[0].lower()
    config = load_config()

    if sub == "list":
        list_bots(config)
        return

    if sub == "add":
        if len(args) < 3:
            print("\033[91m用法：/qw-robot config add <名称> <key>\033[0m")
            print("示例：/qw-robot config add main https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx")
            print("示例：/qw-robot config add alert ***REMOVED***")
            sys.exit(1)
        name = args[1]
        raw_key = args[2]
        key = extract_key(raw_key)
        config.setdefault("bots", {})
        if name not in config["bots"]:
            config["bots"][name] = {"description": ""}
        config["bots"][name]["key"] = key
        # 如果是第一个机器人，自动设为默认
        if len(config["bots"]) == 1:
            config["default"] = name
            print(f"\033[93m（已自动设为默认机器人）\033[0m")
        save_config(config)
        print(f"\033[92m✓ 机器人 '{name}' 添加/更新成功\033[0m")
        if name == config.get("default"):
            print(f"  当前默认机器人：{name}")
        return

    if sub in ("set", "default"):
        # set <名称> <key>  或  default <名称>  或  default <raw_key>
        if sub == "set" and len(args) >= 3:
            name = args[1]
            raw_key = args[2]
            key = extract_key(raw_key)
            config.setdefault("bots", {})
            config["bots"][name] = config["bots"].get(name, {})
            config["bots"][name]["key"] = key
            save_config(config)
            print(f"\033[92m✓ 机器人 '{name}' 更新成功\033[0m")
            return
        if sub == "default":
            if len(args) < 2:
                print(f"\n当前默认机器人：\033[92m{config.get('default', '(未设置)')}\033[0m\n")
                list_bots(config)
                return
            name_or_key = args[1]
            # 判断是 raw_key 还是已配置的名称
            if name_or_key.startswith("http") or (len(name_or_key) >= 20 and "-" in name_or_key):
                # URL 或 raw key：直接设为默认（存入 default-key slot）
                key = extract_key(name_or_key)
                config["default-key"] = key
                config["default"] = config.get("default", "default")
                save_config(config)
                print(f"\033[92m✓ 默认机器人 Key 已更新（透传模式，不保存名称）\033[0m")
                print(f"\033[93m  建议使用 /qw-robot config add <名称> {name_or_key} 保存为命名机器人\033[0m")
                return
            name = name_or_key
            if name not in config.get("bots", {}):
                print(f"\033[91m错误：未找到名为 '{name}' 的机器人\033[0m")
                list_bots(config)
                sys.exit(1)
            config["default"] = name
            save_config(config)
            print(f"\033[92m✓ 默认机器人已设为：{name}\033[0m")
            return
        # set 无参数 → 显示帮助
        print("\033[91m用法：/qw-robot config set <名称> <key>\033[0m")
        sys.exit(1)

    if sub in ("remove", "rm", "del", "delete"):
        if len(args) < 2:
            print("\033[91m用法：/qw-robot config remove <名称>\033[0m")
            sys.exit(1)
        name = args[1]
        if name not in config.get("bots", {}):
            print(f"\033[91m错误：未找到名为 '{name}' 的机器人\033[0m")
            sys.exit(1)
        del config["bots"][name]
        if config.get("default") == name:
            # 设为下一个或清空
            config["default"] = next(iter(config["bots"]), "")
        save_config(config)
        print(f"\033[92m✓ 机器人 '{name}' 已删除\033[0m")
        if config["bots"]:
            print(f"  当前默认机器人：{config.get('default', '(未设置)')}")
        return

    if sub == "info":
        if len(args) < 2:
            # 显示默认机器人详情
            name = config.get("default", "")
        else:
            name = args[1]
        if name not in config.get("bots", {}):
            print(f"\033[91m错误：未找到名为 '{name}' 的机器人\033[0m")
            sys.exit(1)
        cfg = config["bots"][name]
        key = cfg.get("key", "")
        print(f"\n机器人信息：")
        print(f"  名称：\033[92m{name}\033[0m")
        if name == config.get("default"):
            print(f"  状态：\033[94m默认机器人\033[0m")
        print(f"  Key：\033[93m{key}\033[0m")
        print(f"  描述：{cfg.get('description', '(无)')}")
        return

    # 未知子命令
    _print_slash_help()


def _print_slash_help() -> None:
    print(f"""
\033[1m/qw-robot 斜杠命令帮助\033[0m

\033[94m配置管理：\033[0m
  /qw-robot config list                          查看所有机器人
  /qw-robot config add <名称> <key>              添加机器人（支持 URL 或纯 Key）
  /qw-robot config set <名称> <key>              更新已有机器人的 Key
  /qw-robot config default <名称>                设置默认机器人
  /qw-robot config remove <名称>                 删除机器人
  /qw-robot config info [名称]                   查看机器人详情

\033[94m快速配置（设置默认机器人）：\033[0m
  /qw-robot config default https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
  /qw-robot config default ***REMOVED***

\033[94m说明：\033[0m
  key 可以是完整的 Webhook URL，也可以是纯 Key 字符串。
  config.json 位于：{CONFIG_FILE}
""")
    sys.exit(0)


# ─── API 请求 ────────────────────────────────────────────────────────────────

def build_url(key: str, endpoint: str = "send") -> str:
    return f"{BASE_URL}/{endpoint}?key={key}"


def post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30, context=ssl_context) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        raise RuntimeError(f"HTTP {e.code}: {body}") from e


def upload_media(key: str, file_path: str, media_type: str = "file") -> str:
    """上传文件，返回 media_id（有效期 3 天）。"""
    upload_url = build_url(key, "upload_media") + f"&type={media_type}"
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    filename = file_path.name
    file_size = file_path.stat().st_size
    limits = {"file": 20 * 1024 * 1024, "voice": 2 * 1024 * 1024}
    if file_size > limits.get(media_type, 20 * 1024 * 1024):
        raise ValueError(f"文件超过大小限制: {file_size / 1024 / 1024:.1f}MB")

    boundary = "----WeComBotBoundary"
    with open(file_path, "rb") as f:
        file_data = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="media"; filename="{filename}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8") + file_data + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        upload_url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60, context=ssl_context) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"上传失败 HTTP {e.code}: {e.read().decode()}") from e

    if result.get("errcode") != 0:
        raise RuntimeError(f"上传失败: {result}")
    return result["media_id"]


# ─── 消息发送函数 ───────────────────────────────────────────────────────────

def send_text(key: str, content: str, mentioned_list=None, mentioned_mobile_list=None) -> dict:
    payload = {
        "msgtype": "text",
        "text": {
            "content": content,
            "mentioned_list": mentioned_list or [],
            "mentioned_mobile_list": mentioned_mobile_list or [],
        },
    }
    return post_json(build_url(key), payload)


def send_markdown(key: str, content: str) -> dict:
    payload = {"msgtype": "markdown", "markdown": {"content": content}}
    return post_json(build_url(key), payload)


def send_markdown_v2(key: str, content: str) -> dict:
    payload = {"msgtype": "markdown_v2", "markdown_v2": {"content": content}}
    return post_json(build_url(key), payload)


def send_image(key: str, image_path: str) -> dict:
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"图片不存在: {image_path}")
    with open(image_path, "rb") as f:
        data = f.read()
    if len(data) > 2 * 1024 * 1024:
        raise ValueError("图片超过 2MB 限制")
    b64 = base64.b64encode(data).decode("utf-8")
    md5v = hashlib.md5(data).hexdigest()
    payload = {"msgtype": "image", "image": {"base64": b64, "md5": md5v}}
    return post_json(build_url(key), payload)


def send_news(key: str, articles: list) -> dict:
    if not 1 <= len(articles) <= 8:
        raise ValueError("图文消息需 1-8 条")
    payload = {"msgtype": "news", "news": {"articles": articles}}
    return post_json(build_url(key), payload)


def send_file(key: str, file_path: str) -> dict:
    media_id = upload_media(key, file_path, media_type="file")
    payload = {"msgtype": "file", "file": {"media_id": media_id}}
    return post_json(build_url(key), payload)


def send_voice(key: str, file_path: str) -> dict:
    media_id = upload_media(key, file_path, media_type="voice")
    payload = {"msgtype": "voice", "voice": {"media_id": media_id}}
    return post_json(build_url(key), payload)


def send_template_card(key: str, card: dict) -> dict:
    payload = {"msgtype": "template_card", "template_card": card}
    return post_json(build_url(key), payload)


# ─── 自动 Markdown 美化 ──────────────────────────────────────────────────────

def auto_markdown_beautify(content: str, at_all: bool = False, at_users: list = None) -> str:
    """
    将纯文本消息自动美化为企业微信 Markdown 格式。
    规则：
    - 以「通知」「公告」「提醒」「告警」「警告」「部署」「上线」「重启」开头/包含 → 加粗标题
    - 包含冒号分隔的键值对 → 自动格式化为列表
    - 包含时间关键词 → 时间高亮
    - @所有人 → 末尾追加 <@all>
    - @指定用户 → 末尾追加 <@userid>
    """
    import re as _re

    lines = content.strip().splitlines()
    result_lines = []

    # 关键词映射：触发词 → emoji + 标题样式
    TITLE_KEYWORDS = {
        "通知": "📢", "公告": "📣", "提醒": "⏰", "告警": "🚨",
        "警告": "⚠️", "部署": "🚀", "上线": "🟢", "重启": "🔄",
        "开会": "📅", "会议": "📅", "完成": "✅", "失败": "❌",
        "成功": "✅", "错误": "❌", "更新": "🔧",
    }

    # 时间模式：优先匹配复合时间「今天下午3点」，再匹配单独时间词
    TIME_PATTERN = _re.compile(
        r'((?:今天|明天|后天|周[一二三四五六日天]|大后天)'
        r'(?:\s*(?:[上下]午\s*\d{1,2}\s*[点时半]?))?'
        r'|[上下]午\s*\d{1,2}\s*[点时半]?'
        r'|\d{1,2}[：:]\d{2}'
        r'|\d{4}[-/]\d{1,2}[-/]\d{1,2})'
    )

    first_line = lines[0] if lines else content

    # 检测标题关键词
    matched_emoji = ""
    matched_kw = ""
    for kw, emoji in TITLE_KEYWORDS.items():
        if kw in content:
            matched_emoji = emoji
            matched_kw = kw
            break

    # 构造标题行（第一行）
    if matched_emoji:
        title = f"{matched_emoji} **{first_line}**"
    else:
        title = f"**{first_line}**"
    result_lines.append(title)

    # 处理剩余行
    for line in lines[1:]:
        line = line.strip()
        if not line:
            result_lines.append("")
            continue
        # 键值对检测：「xxx：yyy」或「xxx: yyy」
        kv_match = _re.match(r'^([^：:]{1,12})[：:]\s*(.+)$', line)
        if kv_match:
            k, v = kv_match.group(1), kv_match.group(2)
            result_lines.append(f"> **{k}**：{v}")
        else:
            result_lines.append(f"> {line}")

    # 时间高亮（在整个内容中替换，仅在非标题行）
    body = "\n".join(result_lines[1:]) if len(result_lines) > 1 else ""
    if body:
        body = TIME_PATTERN.sub(lambda m: f"`{m.group(0)}`", body)
        result_lines = [result_lines[0]] + body.splitlines()
    else:
        # 标题行也做时间高亮（保留粗体标记）
        pass

    # 对标题行做时间高亮（替换不在 ** 内的时间）
    result_lines[0] = TIME_PATTERN.sub(lambda m: f"`{m.group(0)}`", result_lines[0])

    # @提及
    mention_parts = []
    if at_all:
        mention_parts.append("<@all>")
    if at_users:
        for u in at_users:
            mention_parts.append(f"<@{u}>")
    if mention_parts:
        result_lines.append("")
        result_lines.append(" ".join(mention_parts))

    return "\n".join(result_lines)


# ─── 机器人 Key 解析 ─────────────────────────────────────────────────────────

def resolve_bot_key(config: dict, bot_name: str | None) -> tuple[str, str]:
    """
    解析机器人名称或 Key，返回 (actual_key, label)。
    label 用于日志显示。
    """
    if not bot_name:
        default_name = config.get("default")
        bots = config.get("bots", {})
        # 优先检查 default-key（透传模式，直接存的 raw key）
        default_key = config.get("default-key")
        if default_key:
            return default_key, "default"
        if not default_name or default_name not in bots:
            print(
                f"\n\033[91m错误：未指定机器人，且没有设置默认机器人\033[0m\n"
                f"可用机器人：{', '.join(bots.keys()) or '（无）'}\n"
                f"请先配置：/qw-robot config add <名称> <key>\n",
                file=sys.stderr,
            )
            sys.exit(1)
        return bots[default_name]["key"], default_name

    try:
        # 优先尝试从 URL/Key 提取（用户可能直接传了 Key）
        return extract_key(bot_name), "custom"
    except ValueError:
        pass

    bots = config.get("bots", {})
    if bot_name not in bots:
        print(
            f"\n\033[91m错误：未找到名为 '{bot_name}' 的机器人\033[0m\n"
            f"可用机器人：{', '.join(bots.keys()) or '（无）'}\n"
            f"添加机器人：/qw-robot config add {bot_name} <key>\n",
            file=sys.stderr,
        )
        sys.exit(1)
    return bots[bot_name]["key"], bot_name


# ─── CLI ──────────────────────────────────────────────────────────────────

def main():
    argv = sys.argv[1:]

    # 拦截斜杠命令
    if argv and argv[0].lstrip("/") == SLASH_CMD.lstrip("/"):
        handle_slash_command(argv)
        return  # never reached

    parser = argparse.ArgumentParser(
        description="企业微信机器人消息发送工具（多机器人版）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 发送文本（使用默认机器人）
  python send_wecom.py text "Hello"

  # 指定机器人发送
  python send_wecom.py --bot alert text "告警内容"

  # 直接使用 Key 或 URL 发送（无需配置）
  python send_wecom.py --bot a0b5a761-b4bb-4986... text "Hello"
  python send_wecom.py --bot https://qyapi.weixin.qq.com/... text "Hello"

  # 发送 Markdown 文件
  python send_wecom.py markdown --file report.md

  # 发送文件
  python send_wecom.py --bot report file /path/to/doc.pdf

斜杠命令（配置管理）:
  /qw-robot config list                   查看所有机器人
  /qw-robot config add main https://...   添加机器人
  /qw-robot config default main           设置默认机器人
  /qw-robot config remove alert           删除机器人
        """,
    )

    parser.add_argument(
        "--bot", dest="bot_name",
        help="机器人名称（从 config.json 读取）、Key、或完整 Webhook URL"
    )
    parser.add_argument(
        "--list-bots", dest="list_bots", action="store_true",
        help="列出所有已配置的机器人并退出"
    )

    subparsers = parser.add_subparsers(dest="msgtype", required=False)

    p_text = subparsers.add_parser("text", help="发送文本消息（默认自动美化为 Markdown）")
    p_text.add_argument("content", nargs="?", help="文本内容")
    p_text.add_argument("--file", help="从文件读取内容")
    p_text.add_argument("--at-all", action="store_true", help="@所有人")
    p_text.add_argument("--at-users", nargs="*", help="@指定成员 userid")
    p_text.add_argument("--at-mobiles", nargs="*", help="@指定成员手机号")
    p_text.add_argument("--no-md", dest="no_markdown", action="store_true", help="禁用自动 Markdown 美化，发送纯文本")

    p_md = subparsers.add_parser("markdown", help="发送 Markdown 消息")
    p_md.add_argument("content", nargs="?", help="Markdown 内容")
    p_md.add_argument("--file", help="从文件读取 Markdown 内容")

    p_md2 = subparsers.add_parser("markdown_v2", help="发送 Markdown v2")
    p_md2.add_argument("content", nargs="?", help="内容")
    p_md2.add_argument("--file", help="从文件读取内容")

    p_img = subparsers.add_parser("image", help="发送图片（≤2MB）")
    p_img.add_argument("path", help="图片文件路径")

    p_file = subparsers.add_parser("file", help="发送文件（≤20MB）")
    p_file.add_argument("path", help="文件路径")

    p_voice = subparsers.add_parser("voice", help="发送语音（≤2MB，AMR）")
    p_voice.add_argument("path", help="语音文件路径")

    p_news = subparsers.add_parser("news", help="发送图文消息")
    p_news.add_argument("articles_json", help="图文数组 JSON 或 JSON 文件路径")

    args = parser.parse_args()

    # --list-bots
    if getattr(args, "list_bots", False):
        list_bots(load_config())
        sys.exit(0)

    if not getattr(args, "msgtype", None):
        parser.print_help()
        print()
        list_bots(load_config())
        sys.exit(0)

    config = load_config()
    _, bot_label = resolve_bot_key(config, getattr(args, "bot_name", None))

    def resolve_key() -> str:
        return resolve_bot_key(config, getattr(args, "bot_name", None))[0]

    try:
        if args.msgtype == "text":
            content = args.content
            if args.file:
                content = Path(args.file).read_text(encoding="utf-8")
            if not content:
                parser.error("请提供文本内容或 --file")
            no_md = getattr(args, "no_markdown", False)
            if no_md:
                # 纯文本模式
                mentioned = ["@all"] if args.at_all else (args.at_users or [])
                mobiles = ["@all"] if args.at_all else (args.at_mobiles or [])
                result = send_text(resolve_key(), content, mentioned, mobiles)
                print(f"\033[94m[{bot_label}]\033[0m 纯文本模式")
            else:
                # 自动 Markdown 美化模式
                md_content = auto_markdown_beautify(
                    content,
                    at_all=args.at_all,
                    at_users=args.at_users or [],
                )
                result = send_markdown(resolve_key(), md_content)
                print(f"\033[94m[{bot_label}]\033[0m 已自动美化为 Markdown")

        elif args.msgtype == "markdown":
            content = args.content
            if args.file:
                content = Path(args.file).read_text(encoding="utf-8")
            if not content:
                parser.error("请提供 Markdown 内容或 --file")
            result = send_markdown(resolve_key(), content)

        elif args.msgtype == "markdown_v2":
            content = args.content
            if args.file:
                content = Path(args.file).read_text(encoding="utf-8")
            if not content:
                parser.error("请提供内容或 --file")
            result = send_markdown_v2(resolve_key(), content)

        elif args.msgtype == "image":
            result = send_image(resolve_key(), args.path)

        elif args.msgtype == "file":
            print(f"\033[94m[{bot_label}]\033[0m 正在上传: {args.path}")
            result = send_file(resolve_key(), args.path)

        elif args.msgtype == "voice":
            print(f"\033[94m[{bot_label}]\033[0m 正在上传: {args.path}")
            result = send_voice(resolve_key(), args.path)

        elif args.msgtype == "news":
            src = args.articles_json
            if os.path.isfile(src):
                articles = json.loads(Path(src).read_text(encoding="utf-8"))
            else:
                articles = json.loads(src)
            result = send_news(resolve_key(), articles)

        if result.get("errcode") == 0:
            print(f"\033[92m[{bot_label}] 发送成功\033[0m")
        else:
            print(f"\033[91m[{bot_label}] 发送失败: {result}\033[0m", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"\033[91m[{bot_label}] 错误: {e}\033[0m", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
