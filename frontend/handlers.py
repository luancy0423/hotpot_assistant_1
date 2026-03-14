# -*- coding: utf-8 -*-
"""
前端事件处理层
将用户操作翻译为 API 调用，并将结果格式化为 Gradio 组件可消费的返回值。
依赖 api.py（后端），不依赖任何 Gradio UI 组件定义。
"""

import os
import threading
import time

import gradio as gr

from config import BROTH_CHOICES, TEXTURE_CHOICES, MODE_CHOICES
from api import HotpotAssistantAPI
from frontend.parsers import parse_allergens, parse_ingredient_table
from frontend.components import (
    ingredient_table_html, ingredient_delete_choices, basket_bar_html,
    table_ensure_rows, plan_to_share_text,
)
from frontend.timer import preload_all_tts_for_plan

# 全局 API 实例（避免每次点击都重建）
api = HotpotAssistantAPI(use_mock=True)


# ── 方案生成 ─────────────────────────────────────────────────────

def generate_plan_ui(ingredient_table, broth_label: str, texture_label: str,
                     mode_label: str, allergen_text: str, num_people: int = 2):
    """
    Gradio 回调：根据食材表格等输入生成涮煮方案，返回 (markdown, step, plan_data)。
    失败时 step=1（停留在偏好页），成功时 step=2（跳到方案页）。
    """
    broth_value   = next((v for t, v in BROTH_CHOICES   if t == broth_label),   "SPICY")
    texture_value = next((v for t, v in TEXTURE_CHOICES if t == texture_label), "STANDARD")
    mode_value    = next((v for t, v in MODE_CHOICES    if t == mode_label),    "NORMAL")
    allergens     = parse_allergens(allergen_text)
    num_people    = max(1, min(99, int(num_people) if num_people is not None else 2))
    names, custom_ingredients, portions = parse_ingredient_table(ingredient_table)

    if not names and not custom_ingredients:
        return "⚠️ 请在表格中至少填写一行「食材名称」。", 1, None

    result = api.generate_cooking_plan(
        ingredient_names=names or [],
        broth_type=broth_value,
        texture=texture_value,
        user_mode=mode_value,
        allergens_to_avoid=allergens,
        use_llm_sort=bool(
            os.environ.get("HOTPOT_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
        ),
        llm_api_key=None,
        custom_ingredients=custom_ingredients if custom_ingredients else None,
    )

    if not result.success:
        return f"❌ 生成失败：{result.error}", 1, None

    plan     = result.data
    timeline = plan["timeline"]
    items    = timeline["items"]
    events   = timeline["events"]

    lines = [
        "## 🍲 涮煮方案", "",
        f"**适合 {num_people} 人** · **总时长** {timeline['total_duration_display']} · "
        f"**锅底** {timeline['broth_type']} · **模式** {timeline['user_mode']}", "",
        "### 📋 涮煮顺序（按下锅顺序）", "",
    ]
    for i, item in enumerate(items, 1):
        tag     = " *(特色)*" if (item.get("ingredient_id") or "").startswith("custom_") else ""
        portion = portions.get(item["ingredient_name"], 1)
        pstr    = f" x{portion}" if portion > 1 else ""
        line    = f"{i}. **{item['ingredient_name']}**{pstr}{tag} — {item['cooking_display']}"
        if item.get("technique"):
            line += f" — {item['technique']}"
        lines.append(line)
        if item.get("warning"):
            lines.append(f"   ⚠️ {item['warning']}")
        if item.get("dipping_sauce"):
            lines.append(f"   🥢 蘸料：{', '.join(item['dipping_sauce'])}")
        lines.append("")
    lines += ["---", "### ⏱️ 时间线（前 20 条）", ""]
    for e in events[:20]:
        t = e["time_seconds"]
        icon = "⬇️" if e["action"] == "下锅" else "⬆️"
        lines.append(f"- **{t // 60}分{t % 60}秒** {icon} {e['message']}")
    lines += ["", "---", "### 🚨 安全提醒"]
    for w in plan["safety_warnings"]:
        lines.append(f"- {w}")
    lines += ["", "### 💚 健康贴士"]
    for tip in plan["health_tips"]:
        lines.append(f"- {tip}")
    lines += ["", "### 🥢 蘸料推荐"]
    for food, sauces in plan["sauce_recommendations"].items():
        lines.append(f"- **{food}**：{' / '.join(sauces)}")

    plan["num_people"] = num_people
    plan["portions"]   = portions
    return "\n".join(lines), 2, plan


def show_generating():
    """点击「生成方案」后立即切换到结果页并显示加载提示，给用户即时反馈。"""
    loading_md = (
        "## ⏳ 正在生成方案\n\n"
        "**请等待一下，方案即将生成…**\n\n"
        "正在调用大模型智能排序，请稍候。\n\n"
        "*（通常需要 10～30 秒）*"
    )
    return (
        loading_md, 2,
        gr.update(visible=False), gr.update(visible=False),
        gr.update(visible=True),  gr.update(visible=False),
        "",
    )


def generate_and_go(ingredient_table, broth_label, texture_label,
                    mode_label, allergen_text, num_people):
    """生成方案并切换页面；失败时停留在偏好页显示错误。"""
    md, step, plan_data = generate_plan_ui(
        ingredient_table, broth_label, texture_label,
        mode_label, allergen_text, num_people=num_people,
    )
    if step == 2:
        plan_text = plan_to_share_text(plan_data) if plan_data else ""
        return (md, 2,
                gr.update(visible=False), gr.update(visible=False),
                gr.update(visible=True),  gr.update(visible=False),
                "", plan_data, plan_text)
    return (md, step,
            gr.update(visible=False), gr.update(visible=True),
            gr.update(visible=False), gr.update(visible=False),
            md, None, "")


def start_eating(plan_data):
    """点击「开始吃饭」：进入计时页，后台预加载所有 TTS。"""
    if not plan_data or not plan_data.get("timeline"):
        return (0, 2,
                gr.update(visible=False), gr.update(visible=False),
                gr.update(visible=True),  gr.update(visible=False),
                "暂无方案数据，请先生成方案。", -1, -1,
                "<p style='color:#c0392b;padding:16px'>暂无方案数据，请先生成方案。</p>", "")
    start_time = time.time()
    threading.Thread(target=preload_all_tts_for_plan, args=(start_time, plan_data), daemon=True).start()

    num_people = plan_data.get("num_people") or 0
    head       = f"**适合 {num_people} 人**\n\n" if num_people else ""
    safety     = "\n".join(f"- {w}" for w in (plan_data.get("safety_warnings") or [])) or "无"
    health     = "\n".join(f"- {t}" for t in (plan_data.get("health_tips") or []))     or "无"
    sauce      = "\n".join(f"- **{f}**：{' / '.join(s)}"
                           for f, s in (plan_data.get("sauce_recommendations") or {}).items()) or "无"
    bottom_md  = head + f"### 🚨 安全提醒\n{safety}\n\n### 💚 健康贴士\n{health}\n\n### 🥢 蘸料推荐\n{sauce}"
    initial    = "<p style='color:#aaa;text-align:center;padding:32px;font-size:.95em'>⏱ 计时已启动，请按方案顺序开始下锅。</p>"
    return (start_time, 3,
            gr.update(visible=False), gr.update(visible=False),
            gr.update(visible=False), gr.update(visible=True),
            bottom_md, -1, -1, initial, "")


# ── 食材输入辅助 ─────────────────────────────────────────────────

def voice_to_ingredients(audio_path, current_state):
    """语音识别 → 追加到食材 state，返回 (state, html, status, choices)。"""
    if not audio_path or not os.path.isfile(audio_path):
        return (current_state, ingredient_table_html(current_state or []),
                "请先录制或上传一段语音（说菜名即可）。",
                ingredient_delete_choices(current_state or []))
    try:
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
    except Exception as e:
        return (current_state, ingredient_table_html(current_state or []),
                f"读取音频失败：{e}", ingredient_delete_choices(current_state or []))
    result = api.input_from_voice(audio_data=audio_bytes)
    if not result.success:
        return (current_state, ingredient_table_html(current_state or []),
                f"语音识别失败：{result.error}", ingredient_delete_choices(current_state or []))
    names      = result.data.get("ingredient_names") or []
    transcript = result.data.get("transcript") or ""
    if not names:
        short = (transcript[:50] + "…") if len(transcript) > 50 else transcript
        return (current_state, ingredient_table_html(current_state or []),
                f"未识别到食材。转写：「{short}」", ingredient_delete_choices(current_state or []))
    rows = table_ensure_rows(current_state)
    for name in names:
        if name and name.strip():
            rows.append([name.strip(), "", 1])
    short_t = (transcript[:30] + "…") if len(transcript) > 30 else transcript
    return (rows, ingredient_table_html(rows),
            f"已识别：{'、'.join(names)}（转写：{short_t}）", ingredient_delete_choices(rows))


def image_to_ingredients(image, current_state):
    """VLM 图片识别食材 → 追加到 state，返回 (state, html, status, choices)。"""
    from services.llm_service import recognize_ingredients_from_image as vlm_recognize
    if image is None:
        return (current_state, ingredient_table_html(current_state or []),
                "请先上传一张图片（菜单、菜品或餐桌均可）。", ingredient_delete_choices(current_state or []))
    if isinstance(image, str):
        path = image
    elif isinstance(image, dict):
        path = image.get("path") or image.get("name")
    else:
        path = getattr(image, "name", None) or getattr(image, "path", None)
    if not path or not os.path.isfile(path):
        return (current_state, ingredient_table_html(current_state or []),
                "无法读取图片文件，请重新上传。", ingredient_delete_choices(current_state or []))
    try:
        with open(path, "rb") as f:
            image_data = f.read()
    except Exception as e:
        return (current_state, ingredient_table_html(current_state or []),
                f"读取图片失败：{e}", ingredient_delete_choices(current_state or []))
    mime = "image/png" if os.path.splitext(path)[1].lower() == ".png" else "image/jpeg"
    try:
        names = vlm_recognize(image_data, mime_type=mime)
    except Exception as e:
        return (current_state, ingredient_table_html(current_state or []),
                f"VLM 识别失败：{e}", ingredient_delete_choices(current_state or []))
    if not names:
        return (current_state, ingredient_table_html(current_state or []),
                "图中未识别到火锅食材，请换一张图片试试。", ingredient_delete_choices(current_state or []))
    rows = table_ensure_rows(current_state)
    for name in names:
        if name and name.strip():
            rows.append([name.strip(), "", 1])
    return (rows, ingredient_table_html(rows),
            f"已识别：{'、'.join(names)}", ingredient_delete_choices(rows))


# ── 偏好 ─────────────────────────────────────────────────────────

def load_preference_ui():
    """加载已保存的用户偏好，返回 (broth_label, texture_label, mode_label, allergen_str, status)。"""
    r = api.get_user_preferences()
    if not r.success:
        return "麻辣红汤", "标准", "普通", "", f"❌ {r.error}"
    prefs         = r.data
    broth_label   = next((t for t, v in BROTH_CHOICES   if v == prefs.get("broth_type",  "SPICY")),    "麻辣红汤")
    texture_label = next((t for t, v in TEXTURE_CHOICES if v == prefs.get("texture",     "STANDARD")), "标准")
    mode_label    = next((t for t, v in MODE_CHOICES    if v == prefs.get("user_mode",   "NORMAL")),   "普通")
    allergens     = prefs.get("allergens_to_avoid") or []
    allergen_str  = "，".join(allergens) if isinstance(allergens, list) else str(allergens)
    return broth_label, texture_label, mode_label, allergen_str, "✅ 已加载您的偏好"


# ── 食材库 ───────────────────────────────────────────────────────

def build_ingredient_placeholder() -> str:
    """获取示例食材名，用于输入框占位提示。"""
    r = api.get_available_ingredients()
    if not r.success or not r.data:
        return "肥牛、毛肚、鸭肠、虾滑、土豆、金针菇、菠菜"
    return "、".join(x["name"] for x in r.data["ingredients"][:10])
