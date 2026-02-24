# -*- coding: utf-8 -*-
"""
涮涮AI - Gradio Web 界面
部署条件：Gradio。运行后可在浏览器中使用智能火锅助手。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 加载 .env（与 app.py 相同逻辑，便于直接运行 python app_gradio.py）
_root = os.path.dirname(os.path.abspath(__file__))
_env_path = os.path.join(_root, ".env")
if os.path.isfile(_env_path):
    with open(_env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip("'\"")
                if k and os.environ.get(k) is None:
                    os.environ[k] = v

import time
import base64
import struct
import io
import gradio as gr
from api import HotpotAssistantAPI
from services.llm_service import recognize_ingredients_from_image as vlm_recognize_ingredients
from data.ingredients_db import search_ingredient

# 全局 API 实例（避免每次点击都重建）
api = HotpotAssistantAPI(use_mock=True)

# 锅底 / 口感 / 模式 选项（展示用中文）
BROTH_CHOICES = [
    ("麻辣红汤", "SPICY"),
    ("清汤", "CLEAR"),
    ("番茄锅", "TOMATO"),
    ("菌汤", "MUSHROOM"),
    ("骨汤", "BONE"),
]
TEXTURE_CHOICES = [
    ("标准", "STANDARD"),
    ("脆嫩", "CRISPY"),
    ("软嫩", "TENDER"),
    ("软烂", "SOFT"),
]
MODE_CHOICES = [
    ("普通", "NORMAL"),
    ("老人模式", "ELDERLY"),
    ("儿童模式", "CHILD"),
    ("快手模式", "QUICK"),
]


def parse_ingredients_from_text(text: str):
    """从文本框解析食材列表，供生成方案使用。"""
    if not text or not text.strip():
        return []
    # 支持中文顿号、逗号、空格、换行分隔
    raw = text.replace("，", ",").replace("、", ",").replace("\n", ",")
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return parts


def _parse_allergens(text: str):
    """从「过敏原」文本框解析为列表。"""
    if not text or not text.strip():
        return []
    raw = text.replace("，", ",").replace("、", ",").replace("\n", ",")
    return [p.strip() for p in raw.split(",") if p.strip()]


def _parse_custom_ingredients(text: str):
    """
    解析「特色/自定义食材」文本框。
    每行一条：名称 + 时间。时间可为秒数（90）、"1分钟"、"2分30秒"、"1.5min"、"2h" 等；
    内部统一转换为秒。对于缺省或无法解析的时间，尝试：
      1）根据食材库中相似食材估计；
      2）根据名称中的类别关键词估计；
      3）最后退回到默认 120 秒。

    同时会过滤明显不像食材的干扰输入，并返回提示信息。

    示例：
        田鸡 90
        蛇段 2分钟
        牛蛙, 120

    返回:
        items, message
        items: [{"name": "田鸡", "cooking_seconds": 90, "warning": "...(可选)..." }, ...]
        message: 额外提醒（如估计时间/被忽略的行），可用于界面展示。
    """
    import re

    def _normalize_time_to_seconds(raw_time: str):
        """将各种时间格式统一解析为秒；无法解析则返回 None。"""
        s = raw_time.strip().lower()
        if not s:
            return None
        # 纯数字：直接视为秒
        if s.isdigit():
            return int(s)
        # 形如 "2:30" -> 2分30秒
        m = re.match(r"^(\d+):(\d+)$", s)
        if m:
            return int(m.group(1)) * 60 + int(m.group(2))
        # X小时 / h
        m = re.search(r"(\d+(?:\.\d+)?)\s*(小时|hour|hours|h)", s)
        if m:
            hours = float(m.group(1))
            return int(hours * 3600)
        # X分Y秒
        m = re.search(r"(\d+)\s*分(?:\s*(\d+)\s*秒)?", s)
        if m:
            minutes = int(m.group(1))
            sec = int(m.group(2)) if m.group(2) else 0
            return minutes * 60 + sec
        # X分钟 / min
        m = re.search(r"(\d+(?:\.\d+)?)\s*(分钟|分|min|mins|m)", s)
        if m:
            minutes = float(m.group(1))
            return int(minutes * 60)
        # X秒 / s
        m = re.search(r"(\d+(?:\.\d+)?)\s*(秒|sec|secs|second|seconds|s)", s)
        if m:
            seconds = float(m.group(1))
            return int(seconds)
        return None

    if not text or not text.strip():
        return [], ""

    items = []
    ignored_lines = []
    estimated_lines = []

    for raw_line in text.strip().split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        # 支持 "名称 时间" 或 "名称, 时间" 或 "名称，时间"
        parts = re.split(r"[\s,，]+", line, maxsplit=1)
        name = (parts[0] or "").strip()
        if not name:
            continue

        # 粗略判断是否像食材名：排除明显口语/指令
        lowered = name.lower()
        if lowered in {"谢谢", "好的", "可以", "多一点", "少一点", "不要辣", "不辣", "微辣"}:
            ignored_lines.append(name)
            continue
        # 过短又无中文/字母的内容视为噪声
        if len(name) <= 1 and not re.search(r"[a-zA-Z\u4e00-\u9fff]", name):
            ignored_lines.append(name)
            continue

        seconds = None
        used_estimate = False
        estimate_reason = ""

        if len(parts) > 1 and parts[1].strip():
            raw_time = parts[1].strip()
            seconds = _normalize_time_to_seconds(raw_time)

        # 时间缺失或解析失败：尝试估计
        if seconds is None:
            # 1) 先从食材库中找相似项
            matched = search_ingredient(name)
            if matched:
                ref = matched[0]
                seconds = ref.cooking_rule.base_seconds
                used_estimate = True
                estimate_reason = f"时间参考常见食材「{ref.name}」的标准涮煮时间估算，实际请根据熟度微调。"
            else:
                # 2) 根据关键词进行大致估计
                kw = name
                if any(k in kw for k in ["牛", "羊", "猪", "肉", "排", "肠", "肚", "串"]):
                    seconds = 180
                elif any(k in kw for k in ["虾", "蟹", "鱼", "贝", "蛙"]):
                    seconds = 150
                elif any(k in kw for k in ["丸", "滑"]):
                    seconds = 150
                elif any(k in kw for k in ["菜", "生菜", "青菜", "菠菜", "蔬", "笋", "瓜", "藕", "萝卜"]):
                    seconds = 90
                elif any(k in kw for k in ["面", "粉", "米线", "粉丝", "年糕", "饭"]):
                    seconds = 210
                else:
                    # 3) 保底默认
                    seconds = 120
                used_estimate = True
                if not estimate_reason:
                    estimate_reason = "时间为根据名称大致估计值，存在不确定性，请留意熟度并适当调整。"

        # 统一裁剪范围，避免异常值
        seconds = int(seconds)
        seconds = min(999 * 60, max(10, seconds))

        item = {"name": name, "cooking_seconds": seconds}
        if used_estimate and estimate_reason:
            # 将不确定性提示写入 warning，供后续方案展示
            item["warning"] = f"⏱️ {estimate_reason}"
            estimated_lines.append(f"- {name}: 约 {seconds} 秒（估计值）")
        items.append(item)

    # 汇总提示信息
    messages = []
    if ignored_lines:
        messages.append(f"⚠️ 已忽略以下疑似非食材输入：{', '.join(sorted(set(ignored_lines)))}")
    if estimated_lines:
        messages.append("⚠️ 以下特色食材的涮煮时间为估计值，存在不确定性，请根据实际熟度调整：\n" + "\n".join(estimated_lines))

    return items, ("\n\n".join(messages) if messages else "")


def _parse_portions(text: str) -> dict:
    """解析「各菜品份数」文本框，返回 { 食材名: 份数 }，未出现的默认 1。"""
    if not text or not text.strip():
        return {}
    out = {}
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.replace("，", ",").replace("、", " ").split()
        if not parts:
            continue
        name = parts[0].strip()
        if not name:
            continue
        try:
            n = int(parts[1].strip()) if len(parts) > 1 else 1
            n = max(1, min(99, n))
        except (ValueError, IndexError):
            n = 1
        out[name] = n
    return out


def generate_plan_ui(
    ingredient_text: str,
    custom_ingredient_text: str,
    broth_label: str,
    texture_label: str,
    mode_label: str,
    allergen_text: str,
    num_people: int = 2,
    portions_text: str = "",
):
    """
    Gradio 回调：根据界面输入生成涮煮方案并返回 Markdown。
    支持人数与各菜品份数，大模型 API Key 由系统预设。
    """
    # 从展示标签反查枚举值
    broth_value = next((v for t, v in BROTH_CHOICES if t == broth_label), "SPICY")
    texture_value = next((v for t, v in TEXTURE_CHOICES if t == texture_label), "STANDARD")
    mode_value = next((v for t, v in MODE_CHOICES if t == mode_label), "NORMAL")
    allergens = _parse_allergens(allergen_text)
    custom_ingredients, custom_msg = _parse_custom_ingredients(custom_ingredient_text or "")
    num_people = max(1, min(99, int(num_people) if num_people is not None else 2))
    portions = _parse_portions(portions_text or "")

    names = parse_ingredients_from_text(ingredient_text)
    if not names and not custom_ingredients:
        return "⚠️ 请至少输入「常见食材」或「特色/自定义食材」其一。", 1, None  # 留在步骤1

    result = api.generate_cooking_plan(
        ingredient_names=names or [],
        broth_type=broth_value,
        texture=texture_value,
        user_mode=mode_value,
        allergens_to_avoid=allergens,
        use_llm_sort=True,
        llm_api_key=None,
        custom_ingredients=custom_ingredients if custom_ingredients else None,
    )

    if not result.success:
        return f"❌ 生成失败：{result.error}", 1, None

    plan = result.data
    timeline = plan["timeline"]
    items = timeline["items"]
    events = timeline["events"]
    total_display = timeline["total_duration_display"]

    lines = []
    # 如果有关于特色食材解析的提示（估计时间/忽略干扰输入），放在方案最前面
    if custom_msg:
        lines.append(custom_msg)
        lines.append("")
    lines.append("## 🍲 涮煮方案")
    lines.append("")
    lines.append(f"**适合 {num_people} 人** · **总时长** {total_display} · **锅底** {timeline['broth_type']} · **模式** {timeline['user_mode']}（大模型智能排序）")
    lines.append("")
    lines.append("### 📋 涮煮顺序（按下锅顺序）")
    lines.append("")
    for i, item in enumerate(items, 1):
        tag = " *(特色)*" if (item.get("ingredient_id") or "").startswith("custom_") else ""
        portion = portions.get(item["ingredient_name"], 1)
        portion_str = f" x{portion}" if portion > 1 else ""
        line = f"{i}. **{item['ingredient_name']}**{portion_str}{tag} — {item['cooking_display']}"
        if item.get("technique"):
            line += f" — {item['technique']}"
        lines.append(line)
        if item.get("warning"):
            lines.append(f"   ⚠️ {item['warning']}")
        if item.get("dipping_sauce"):
            lines.append(f"   🥢 蘸料：{', '.join(item['dipping_sauce'])}")
        lines.append("")
    lines.append("---")
    lines.append("### ⏱️ 时间线（前 20 条）")
    lines.append("")
    for e in events[:20]:
        t = e["time_seconds"]
        time_str = f"{t // 60}分{t % 60}秒"
        icon = "⬇️" if e["action"] == "下锅" else "⬆️"
        lines.append(f"- **{time_str}** {icon} {e['message']}")
    lines.append("")
    lines.append("---")
    lines.append("### 🚨 安全提醒")
    for w in plan["safety_warnings"]:
        lines.append(f"- {w}")
    lines.append("")
    lines.append("### 💚 健康贴士")
    for t in plan["health_tips"]:
        lines.append(f"- {t}")
    lines.append("")
    lines.append("### 🥢 蘸料推荐")
    for food, sauces in plan["sauce_recommendations"].items():
        lines.append(f"- **{food}**：{' / '.join(sauces)}")

    plan["num_people"] = num_people
    plan["portions"] = portions
    return "\n".join(lines), 2, plan  # 成功则跳到步骤 2（结果页），并带上方案数据供「开始吃饭」使用


def voice_to_ingredients(audio_path, current_ingredient_text):
    """
    语音识别并填入食材：读取音频文件，调用 API 识别食材，将结果追加到当前食材列表。
    audio_path: Gradio Audio 返回的 filepath（可为 None）
    返回 (新食材列表文案, 状态提示)
    """
    if not audio_path or not os.path.isfile(audio_path):
        return current_ingredient_text or "", "请先录制或上传一段语音（说菜名即可）。"
    try:
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
    except Exception as e:
        return current_ingredient_text or "", f"读取音频失败：{e}"
    result = api.input_from_voice(audio_data=audio_bytes)
    if not result.success:
        return current_ingredient_text or "", f"语音识别失败：{result.error}"
    names = result.data.get("ingredient_names") or []
    transcript = result.data.get("transcript") or ""
    if not names:
        return current_ingredient_text or "", f"未识别到食材。转写：「{(transcript[:50] + '…') if len(transcript) > 50 else transcript}」"
    new_part = "、".join(names)
    existing = (current_ingredient_text or "").strip()
    if existing:
        new_text = existing.rstrip("，、, ") + "、" + new_part
    else:
        new_text = new_part
    short_transcript = (transcript[:30] + "…") if len(transcript) > 30 else transcript
    return new_text, f"已识别：{new_part}（转写：{short_transcript}）"


def image_to_ingredients(image, current_ingredient_text):
    """
    上传图片用 VLM 识别食材并填入：读取图片文件，调用硅基流动 Qwen3-VL，将识别结果追加到食材列表。
    image: Gradio Image 返回值（filepath 或 None）
    返回 (新食材列表文案, 状态提示)
    """
    if image is None:
        return current_ingredient_text or "", "请先上传一张图片（菜单、菜品或餐桌均可）。"
    if isinstance(image, str):
        path = image
    elif isinstance(image, dict):
        path = image.get("path") or image.get("name")
    else:
        path = getattr(image, "name", None) or getattr(image, "path", None)
    if not path or not os.path.isfile(path):
        return current_ingredient_text or "", "无法读取图片文件，请重新上传。"
    try:
        with open(path, "rb") as f:
            image_data = f.read()
    except Exception as e:
        return current_ingredient_text or "", f"读取图片失败：{e}"
    ext = os.path.splitext(path)[1].lower()
    mime = "image/png" if ext == ".png" else "image/jpeg"
    try:
        names = vlm_recognize_ingredients(image_data, mime_type=mime)
    except Exception as e:
        return current_ingredient_text or "", f"VLM 识别失败：{e}"
    if not names:
        return current_ingredient_text or "", "图中未识别到火锅食材，请换一张图片试试。"
    new_part = "、".join(names)
    existing = (current_ingredient_text or "").strip()
    if existing:
        new_text = existing.rstrip("，、, ") + "、" + new_part
    else:
        new_text = new_part
    return new_text, f"已识别：{new_part}"


def build_ingredient_placeholder():
    """获取示例食材列表，用于占位提示。"""
    r = api.get_available_ingredients()
    if not r.success or not r.data:
        return "肥牛、毛肚、鸭肠、虾滑、土豆、金针菇、菠菜"
    names = [x["name"] for x in r.data["ingredients"][:10]]
    return "、".join(names)


def load_preference_ui():
    """加载已保存的用户偏好，返回用于填充下拉框和过敏原框的值。"""
    r = api.get_user_preferences()
    if not r.success:
        return "麻辣红汤", "标准", "普通", "", f"❌ {r.error}"
    prefs = r.data
    # 枚举值 -> 界面标签
    broth_label = next((t for t, v in BROTH_CHOICES if v == prefs.get("broth_type", "SPICY")), "麻辣红汤")
    texture_label = next((t for t, v in TEXTURE_CHOICES if v == prefs.get("texture", "STANDARD")), "标准")
    mode_label = next((t for t, v in MODE_CHOICES if v == prefs.get("user_mode", "NORMAL")), "普通")
    allergens = prefs.get("allergens_to_avoid") or []
    allergen_str = "，".join(allergens) if isinstance(allergens, list) else str(allergens)
    return broth_label, texture_label, mode_label, allergen_str, "✅ 已加载您的偏好"


def save_preference_ui(broth_label: str, texture_label: str, mode_label: str, allergen_text: str):
    """将当前界面设置保存为用户偏好。"""
    broth_value = next((v for t, v in BROTH_CHOICES if t == broth_label), "SPICY")
    texture_value = next((v for t, v in TEXTURE_CHOICES if t == texture_label), "STANDARD")
    mode_value = next((v for t, v in MODE_CHOICES if t == mode_label), "NORMAL")
    allergens = _parse_allergens(allergen_text)
    r = api.save_user_preferences(
        broth_type=broth_value,
        texture=texture_value,
        user_mode=mode_value,
        allergens_to_avoid=allergens,
    )
    if r.success:
        return "✅ 偏好已保存，下次点击「加载我的偏好」即可恢复"
    return f"❌ {r.error}"


def build_ingredient_library_md():
    """生成食材库说明 Markdown（按分类）。"""
    r = api.get_available_ingredients()
    if not r.success or not r.data:
        return "暂无食材数据。"
    from collections import defaultdict
    by_cat = defaultdict(list)
    for ing in r.data["ingredients"]:
        by_cat[ing["category"]].append(ing["name"])
    lines = ["## 📚 支持的食材一览\n"]
    for cat in ["肉类", "内脏类", "海鲜类", "丸滑类", "蔬菜类", "豆制品", "菌菇类", "主食类", "其他"]:
        if cat in by_cat:
            lines.append(f"**{cat}**：{', '.join(by_cat[cat])}\n")
    lines.append("\n在「生成方案」页输入上述名称（或别名）即可参与排序；店内特色可在「特色食材」中手动填写。")
    return "\n".join(lines)


def _make_beep_wav_base64(duration_sec=0.15, sample_rate=44100, freq=880):
    """生成短促提示音 WAV 的 base64，用于 HTML audio。"""
    n = int(sample_rate * duration_sec)
    buf = io.BytesIO()
    with io.BytesIO() as raw:
        for i in range(n):
            t = i / sample_rate
            v = int(32767 * 0.3 * (1 - i / n) * __import__("math").sin(2 * 3.14159265 * freq * t))
            raw.write(struct.pack("<h", max(-32768, min(32767, v))))
        pcm = raw.getvalue()
    # 最小 WAV 头
    with io.BytesIO() as wav:
        wav.write(b"RIFF")
        wav.write(struct.pack("<I", 36 + len(pcm)))
        wav.write(b"WAVEfmt ")
        wav.write(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
        wav.write(b"data")
        wav.write(struct.pack("<I", len(pcm)))
        wav.write(pcm)
        wav.seek(0)
        return base64.b64encode(wav.read()).decode("ascii")


# 模块加载时生成一次，供计时页提示音使用
_BEEP_B64 = _make_beep_wav_base64()


def _nav_next(step):
    """下一步：步骤 0 -> 1"""
    return 1, gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)


def _nav_prev(step):
    """上一步：步骤 1 -> 0"""
    return 0, gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)


def _nav_restart(step):
    """重新开始：步骤 2 -> 0"""
    return 0, gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)


def _nav_restart_from_timer(step):
    """从计时页返回：步骤 3 -> 0"""
    return 0, gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)


def _show_generating():
    """点击生成后立即显示加载提示并切换到结果页，给用户即时反馈。"""
    loading_md = (
        "## ⏳ 正在生成方案\n\n"
        "**请等待一下，方案即将生成…**\n\n"
        "正在调用大模型智能排序，请稍候。\n\n"
        "*（通常需要 10～30 秒）*"
    )
    return (
        loading_md,
        2,
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=False),
        "",
    )


def _generate_and_go(ingredient_text, custom_ingredient_text, broth_label, texture_label, mode_label, allergen_text, num_people, portions_text):
    """生成方案并返回 (markdown, new_step, v0,v1,v2,v3, step1_message, plan_data)。失败时在步骤1显示错误。"""
    md, step, plan_data = generate_plan_ui(
        ingredient_text, custom_ingredient_text, broth_label, texture_label, mode_label, allergen_text,
        num_people=num_people, portions_text=portions_text,
    )
    if step == 2:
        return md, 2, gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), "", plan_data
    return md, step, gr.update(visible=True), gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), md, None


def _start_eating(plan_data):
    """点击「开始吃饭」：进入步骤 3，记录开始时间，并返回步骤 3 底部文案（安全/健康/蘸料）及初始提醒。"""
    if not plan_data or not plan_data.get("timeline"):
        return 0, 2, gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), "暂无方案数据，请先生成方案。", -1, -1, "⏱️ 已进行 **0 分 0 秒**\n\n暂无提醒。", ""
    start_time = time.time()
    num_people = plan_data.get("num_people") or 0
    head = f"**适合 {num_people} 人**\n\n" if num_people else ""
    lines = []
    for w in plan_data.get("safety_warnings") or []:
        lines.append(f"- {w}")
    safety = "\n".join(lines) if lines else "无"
    lines = []
    for t in plan_data.get("health_tips") or []:
        lines.append(f"- {t}")
    health = "\n".join(lines) if lines else "无"
    sauce_lines = []
    for food, sauces in (plan_data.get("sauce_recommendations") or {}).items():
        sauce_lines.append(f"- **{food}**：{' / '.join(sauces)}")
    sauce = "\n".join(sauce_lines) if sauce_lines else "无"
    bottom_md = head + f"### 🚨 安全提醒\n{safety}\n\n### 💚 健康贴士\n{health}\n\n### 🥢 蘸料推荐\n{sauce}"
    initial_reminder = "⏱️ 已进行 **0 分 0 秒**\n\n请按方案顺序开始下锅，计时已启动。"
    return start_time, 3, gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), bottom_md, -1, -1, initial_reminder, ""


def _timer_tick(plan_data, start_time, last_put_sec, last_take_sec):
    """每秒调用：根据已过时间生成「应下锅/应捞出」提醒，并在新事件时触发提示音。"""
    if not plan_data or not start_time or start_time <= 0:
        return "等待开始…", last_put_sec or -1, last_take_sec or -1, ""
    elapsed = int(time.time() - start_time)
    events = (plan_data.get("timeline") or {}).get("events") or []
    put_events = [e for e in events if e.get("action") == "下锅"]
    take_events = [e for e in events if e.get("action") in ("捞出", "捞起")]
    put_due = [e for e in put_events if e["time_seconds"] <= elapsed]
    take_due = [e for e in take_events if e["time_seconds"] <= elapsed]
    next_put = next((e for e in put_events if e["time_seconds"] > elapsed), None)
    next_take = next((e for e in take_events if e["time_seconds"] > elapsed), None)
    cur_put = put_due[-1] if put_due else None
    cur_take = take_due[-1] if take_due else None
    new_put_sec = (cur_put["time_seconds"] if cur_put else (last_put_sec if last_put_sec is not None else -1))
    new_take_sec = (cur_take["time_seconds"] if cur_take else (last_take_sec if last_take_sec is not None else -1))
    last_put_sec = last_put_sec if last_put_sec is not None else -1
    last_take_sec = last_take_sec if last_take_sec is not None else -1
    play_beep = False
    if cur_put and cur_put["time_seconds"] > last_put_sec:
        play_beep = True
    if cur_take and cur_take["time_seconds"] > last_take_sec:
        play_beep = True
    m = int(elapsed // 60)
    s = int(elapsed % 60)
    time_str = f"⏱️ 已进行 **{m} 分 {s} 秒**"
    reminder_lines = [time_str, ""]
    def _ingredient_from_msg(msg):
        if not msg:
            return ""
        import re
        m = re.search(r"【([^】]+)】", msg)
        return m.group(1) if m else msg
    if cur_put:
        name = _ingredient_from_msg(cur_put.get("message")) or cur_put.get("item_name") or cur_put.get("message", "")
        reminder_lines.append(f"## ⬇️ 现在请下锅：**{name}**")
    if cur_take:
        name = _ingredient_from_msg(cur_take.get("message")) or cur_take.get("item_name") or cur_take.get("message", "")
        reminder_lines.append(f"## ⬆️ 现在请捞出：**{name}**")
    if not cur_put and not cur_take:
        reminder_lines.append("暂无提醒，请按方案顺序操作。")
    if next_put:
        sec = next_put["time_seconds"] - elapsed
        name = _ingredient_from_msg(next_put.get("message")) or next_put.get("item_name") or next_put.get("message", "")
        reminder_lines.append(f"\n*即将下锅：{name}（约 {sec} 秒后）*")
    if next_take:
        sec = next_take["time_seconds"] - elapsed
        name = _ingredient_from_msg(next_take.get("message")) or next_take.get("item_name") or next_take.get("message", "")
        reminder_lines.append(f"*即将捞出：{name}（约 {sec} 秒后）*")
    beep_html = ""
    if play_beep and _BEEP_B64:
        beep_html = f'<audio autoplay><source src="data:audio/wav;base64,{_BEEP_B64}" type="audio/wav"></audio>'
    return "\n".join(reminder_lines), new_put_sec, new_take_sec, beep_html


def create_ui():
    """构建 Gradio 界面：步骤1 食材 → 步骤2 锅底/偏好 → 步骤3 方案结果 → 步骤4 吃饭计时。"""
    placeholder = build_ingredient_placeholder()
    with gr.Blocks(
        title="涮涮AI - 智能火锅助手",
        theme=gr.themes.Soft(primary_hue="orange"),
        css="""
        .main-header { font-size: 1.4em; margin-bottom: 0.5em; }
        .gr-markdown { font-size: 0.95em; }
        .timer-reminder { font-size: 1.2em; }
        """
    ) as demo:
        gr.Markdown("# 🍲 涮涮AI — 智能火锅助手")
        step_state = gr.State(0)
        plan_data_state = gr.State(None)
        start_time_state = gr.State(0)
        last_beeped_put = gr.State(-1)
        last_beeped_take = gr.State(-1)

        # 步骤 0：输入食材
        step0 = gr.Column(visible=True)
        with step0:
            gr.Markdown("### 步骤 1/3：输入食材")
            ingredient_input = gr.Textbox(
                label="食材列表",
                placeholder=placeholder,
                lines=4,
                info="用逗号、顿号或换行分隔",
            )
            custom_ingredient_input = gr.Textbox(
                label="特色/自定义食材（店内特有）",
                placeholder="每行：名称 时间，如 田鸡 90、蛇段 2分钟",
                lines=2,
            )
            gr.Markdown("**或上传图片识别食材**")
            image_input = gr.Image(
                label="上传菜单/菜品图",
                type="filepath",
                sources=["upload"],
            )
            image_status = gr.Markdown(value="", visible=True)
            btn_image = gr.Button("识别图片并填入食材", size="sm")
            gr.Markdown("**或使用语音输入**")
            voice_input = gr.Audio(
                label="语音输入食材",
                sources=["microphone", "upload"],
                type="filepath",
            )
            voice_status = gr.Markdown(value="", visible=True)
            btn_voice = gr.Button("识别语音并填入食材", size="sm")
            btn_next = gr.Button("下一步：选择锅底与偏好", variant="primary")

        # 步骤 1：锅底与偏好
        step1 = gr.Column(visible=False)
        with step1:
            gr.Markdown("### 步骤 2/3：锅底与偏好")
            broth_dd = gr.Dropdown(
                label="锅底类型",
                choices=[t for t, _ in BROTH_CHOICES],
                value="麻辣红汤",
            )
            texture_dd = gr.Dropdown(
                label="口感偏好",
                choices=[t for t, _ in TEXTURE_CHOICES],
                value="标准",
            )
            mode_dd = gr.Dropdown(
                label="用户模式",
                choices=[t for t, _ in MODE_CHOICES],
                value="普通",
            )
            allergen_input = gr.Textbox(
                label="需避免的过敏原（可选）",
                placeholder="如：虾、鱼",
                lines=1,
            )
            num_people_input = gr.Number(
                label="就餐人数",
                value=2,
                minimum=1,
                maximum=99,
                step=1,
                precision=0,
                info="一起吃饭的人数",
            )
            portions_input = gr.Textbox(
                label="各菜品份数（可选）",
                placeholder="每行：食材名 份数\n如：肥牛 2\n毛肚 1\n土豆 3\n未填的默认 1 份",
                lines=3,
                info="与上方食材列表对应，可只填需要多份的",
            )
            load_pref_btn = gr.Button("加载我的偏好", size="sm")
            pref_status = gr.Markdown(value="", elem_id="pref_status")
            result_status = gr.Markdown(value="", elem_id="result_status")
            with gr.Row():
                btn_prev = gr.Button("上一步")
                btn_generate = gr.Button("生成涮煮方案", variant="primary")

        # 步骤 2：方案结果
        step2 = gr.Column(visible=False)
        with step2:
            gr.Markdown("### 步骤 3/3：涮煮方案")
            output_md = gr.Markdown(value="方案将显示在此。", label="方案结果")
            with gr.Row():
                btn_restart = gr.Button("重新开始")
                btn_start_eating = gr.Button("开始吃饭", variant="primary")

        # 步骤 3：吃饭计时页（第四页）
        step3 = gr.Column(visible=False)
        with step3:
            gr.Markdown("### 🍲 吃饭计时 — 按提示下锅/捞出")
            timer_reminder_md = gr.Markdown(value="⏱️ 已进行 **0 分 0 秒**\n\n暂无提醒。", elem_classes=["timer-reminder"])
            timer_beep_html = gr.HTML(value="")
            timer_bottom_md = gr.Markdown(value="")
            btn_back_from_timer = gr.Button("结束计时，返回首页")

        btn_image.click(
            fn=image_to_ingredients,
            inputs=[image_input, ingredient_input],
            outputs=[ingredient_input, image_status],
        )
        btn_voice.click(
            fn=voice_to_ingredients,
            inputs=[voice_input, ingredient_input],
            outputs=[ingredient_input, voice_status],
        )
        # 导航：下一步 / 上一步 / 重新开始
        btn_next.click(
            fn=_nav_next,
            inputs=[step_state],
            outputs=[step_state, step0, step1, step2, step3],
        )
        btn_prev.click(
            fn=_nav_prev,
            inputs=[step_state],
            outputs=[step_state, step0, step1, step2, step3],
        )
        btn_restart.click(
            fn=_nav_restart,
            inputs=[step_state],
            outputs=[step_state, step0, step1, step2, step3],
        )
        btn_back_from_timer.click(
            fn=_nav_restart_from_timer,
            inputs=[step_state],
            outputs=[step_state, step0, step1, step2, step3],
        )
        load_pref_btn.click(
            fn=load_preference_ui,
            inputs=[],
            outputs=[broth_dd, texture_dd, mode_dd, allergen_input, pref_status],
        )
        # 先显示「请等待…」并跳到结果页，再执行生成（.then），避免长时间无反馈
        btn_generate.click(
            fn=_show_generating,
            inputs=[],
            outputs=[output_md, step_state, step0, step1, step2, step3, result_status],
        ).then(
            fn=_generate_and_go,
            inputs=[
                ingredient_input,
                custom_ingredient_input,
                broth_dd,
                texture_dd,
                mode_dd,
                allergen_input,
                num_people_input,
                portions_input,
            ],
            outputs=[output_md, step_state, step0, step1, step2, step3, result_status, plan_data_state],
        )
        btn_start_eating.click(
            fn=_start_eating,
            inputs=[plan_data_state],
            outputs=[
                start_time_state,
                step_state,
                step0,
                step1,
                step2,
                step3,
                timer_bottom_md,
                last_beeped_put,
                last_beeped_take,
                timer_reminder_md,
                timer_beep_html,
            ],
        )
        # 计时器：仅在步骤 3 时每秒更新提醒（通过 Timer 驱动）
        timer = gr.Timer(value=1)
        timer.tick(
            fn=_timer_tick,
            inputs=[plan_data_state, start_time_state, last_beeped_put, last_beeped_take],
            outputs=[timer_reminder_md, last_beeped_put, last_beeped_take, timer_beep_html],
        )

        gr.Markdown("---\n💡 按步骤操作：输入食材 → 选择锅底与偏好 → 生成方案 → 可「重新开始」或「开始吃饭」进入计时提醒。")
    return demo


if __name__ == "__main__":
    demo = create_ui()
    demo.launch(
        server_name="0.0.0.0",  # 开放访问：允许局域网/外网通过 IP 访问
        server_port=7860,
        share=True,  # 生成临时公网链接（gradio.live），方便分享
    )
