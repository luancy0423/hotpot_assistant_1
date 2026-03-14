# -*- coding: utf-8 -*-
"""
<<<<<<< Updated upstream
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

=======
涮涮AI - 前端事件回调
generate_plan、start_eating、食材增删、语音/识图、偏好加载保存、批量添加、搜索补全等。
"""

import os
import gradio as gr

from api import HotpotAssistantAPI
from config import BROTH_CHOICES, TEXTURE_CHOICES, MODE_CHOICES
from frontend import components
from frontend import parsers
from frontend import nav
from frontend import timer
from frontend import tts
from data.ingredients_db import search_ingredient
from services.llm_service import recognize_ingredients_from_image as vlm_recognize_ingredients

api = HotpotAssistantAPI(use_mock=True)


def generate_plan_ui(
    ingredient_table,
    broth_label: str,
    texture_label: str,
    mode_label: str,
    allergen_text: str,
    num_people: int = 2,
):
    """Gradio 回调：根据食材表格等输入生成涮煮方案并返回 Markdown。"""
    broth_value = next((v for t, v in BROTH_CHOICES if t == broth_label), "SPICY")
    texture_value = next((v for t, v in TEXTURE_CHOICES if t == texture_label), "STANDARD")
    mode_value = next((v for t, v in MODE_CHOICES if t == mode_label), "NORMAL")
    allergens = parsers.parse_allergens(allergen_text)
    num_people = max(1, min(99, int(num_people) if num_people is not None else 2))
    names, custom_ingredients, portions = parsers.parse_ingredient_table(ingredient_table)
    if not names and not custom_ingredients:
        return "⚠️ 请在表格中至少填写一行「食材名称」。", 1, None
>>>>>>> Stashed changes
    result = api.generate_cooking_plan(
        ingredient_names=names or [],
        broth_type=broth_value,
        texture=texture_value,
        user_mode=mode_value,
        allergens_to_avoid=allergens,
<<<<<<< Updated upstream
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
=======
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
    lines = [
        "## 🍲 涮煮方案",
        "",
        f"**适合 {num_people} 人** · **总时长** {total_display} · **锅底** {timeline['broth_type']} · **模式** {timeline['user_mode']}（大模型智能排序）",
        "",
        "### 📋 涮煮顺序（按下锅顺序）",
        "",
    ]
    for i, item in enumerate(items, 1):
        tag = " *(特色)*" if (item.get("ingredient_id") or "").startswith("custom_") else ""
        portion = portions.get(item["ingredient_name"], 1)
        portion_str = f" x{portion}" if portion > 1 else ""
        line = f"{i}. **{item['ingredient_name']}**{portion_str}{tag} — {item['cooking_display']}"
>>>>>>> Stashed changes
        if item.get("technique"):
            line += f" — {item['technique']}"
        lines.append(line)
        if item.get("warning"):
            lines.append(f"   ⚠️ {item['warning']}")
        if item.get("dipping_sauce"):
            lines.append(f"   🥢 蘸料：{', '.join(item['dipping_sauce'])}")
        lines.append("")
<<<<<<< Updated upstream
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
=======
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
    return "\n".join(lines), 2, plan


def get_default_seconds(name: str):
    """根据食材名称查库，返回默认涮煮秒数。"""
    return components.get_default_seconds(name)


def ingredient_lookup_hint(name, time_val=None):
    """输入食材名称时返回库内默认时间提示。"""
    try:
        if time_val is not None and time_val != "" and int(float(time_val)) > 0:
            return ""
    except (TypeError, ValueError):
        pass
    sec = get_default_seconds(name)
    if sec is None:
        return ""
    return f"库内默认：**{sec} 秒**（可留空使用，填写则按您的时间）"


def add_ingredient_row(name, time_val, portion, state):
    """将当前表单一行加入 state，返回新 state、展示表、清空表单与提示、删除行下拉选项。"""
    name = (name or "").strip() if isinstance(name, str) else str(name or "").strip()
    if not name:
        state = list(state or [])
        display = components.ingredient_table_display_rows(state)
        choices = components.ingredient_delete_choices(state)
        return state, display, "", 0, 1, "", choices
    state = list(state or [])
    try:
        p = max(1, min(99, int(portion))) if portion not in (None, "") else 1
    except (TypeError, ValueError):
        p = 1
    time_stored = ""
    if time_val is not None and time_val != "":
        try:
            t = int(float(time_val))
            if t > 0:
                time_stored = t
        except (TypeError, ValueError):
            pass
    state.append([name, time_stored, p])
    display = components.ingredient_table_display_rows(state)
    choices = components.ingredient_delete_choices(state)
    return state, display, "", 0, 1, "", choices


def delete_selected_ingredient_row(state, selected_label):
    """根据下拉选中的「第k行：名称」删除对应行。"""
    state = list(state or [])
    if not state or not selected_label or not str(selected_label).strip():
        return state, components.ingredient_table_display_rows(state), components.ingredient_delete_choices(state)
    choices_before = components.ingredient_delete_choices(state)
    try:
        idx = choices_before.index(selected_label)
    except ValueError:
        return state, components.ingredient_table_display_rows(state), components.ingredient_delete_choices(state)
    state.pop(idx)
    return state, components.ingredient_table_display_rows(state), components.ingredient_delete_choices(state)


def delete_last_ingredient_row(state):
    """删除最后一行。"""
    state = list(state or [])
    if state:
        state.pop()
    return state, components.ingredient_table_display_rows(state)


def table_ensure_rows(table, min_rows=1):
    """确保表格为 list of lists，且至少 min_rows 行。"""
    try:
        import pandas as pd
        rows = table.fillna("").values.tolist() if isinstance(table, pd.DataFrame) else [list(r) if isinstance(r, (list, tuple)) else [r, "", 1] for r in (table or [])]
    except Exception:
        rows = []
    for r in rows:
        while len(r) < 3:
            r.append("" if len(r) == 1 else 1)
    while len(rows) < min_rows:
        rows.append(["", "", 1])
    return rows


def voice_to_ingredients(audio_path, current_state):
    """语音识别并填入食材。"""
    if not audio_path or not os.path.isfile(audio_path):
        return (current_state, components.ingredient_table_display_html(current_state or []),
                "请先录制或上传一段语音（说菜名即可）。", components.ingredient_delete_choices(current_state or []))
>>>>>>> Stashed changes
    try:
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
    except Exception as e:
<<<<<<< Updated upstream
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
=======
        return (current_state, components.ingredient_table_display_html(current_state or []),
                f"读取音频失败：{e}", components.ingredient_delete_choices(current_state or []))
    result = api.input_from_voice(audio_data=audio_bytes)
    if not result.success:
        return (current_state, components.ingredient_table_display_html(current_state or []),
                f"语音识别失败：{result.error}", components.ingredient_delete_choices(current_state or []))
    names = result.data.get("ingredient_names") or []
    transcript = result.data.get("transcript") or ""
    if not names:
        return (current_state, components.ingredient_table_display_html(current_state or []),
                f"未识别到食材。转写：「{(transcript[:50] + '…') if len(transcript) > 50 else transcript}」",
                components.ingredient_delete_choices(current_state or []))
>>>>>>> Stashed changes
    rows = table_ensure_rows(current_state)
    for name in names:
        if name and name.strip():
            rows.append([name.strip(), "", 1])
<<<<<<< Updated upstream
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
=======
    short_transcript = (transcript[:30] + "…") if len(transcript) > 30 else transcript
    return (rows, components.ingredient_table_display_html(rows),
            f"已识别：{'、'.join(names)}（转写：{short_transcript}）", components.ingredient_delete_choices(rows))


def image_to_ingredients(image, current_state):
    """上传图片用 VLM 识别食材并填入。"""
    if image is None:
        return (current_state, components.ingredient_table_display_html(current_state or []),
                "请先上传一张图片（菜单、菜品或餐桌均可）。", components.ingredient_delete_choices(current_state or []))
    path = image if isinstance(image, str) else (image.get("path") or image.get("name") if isinstance(image, dict) else getattr(image, "name", None) or getattr(image, "path", None))
    if not path or not os.path.isfile(path):
        return (current_state, components.ingredient_table_display_html(current_state or []),
                "无法读取图片文件，请重新上传。", components.ingredient_delete_choices(current_state or []))
>>>>>>> Stashed changes
    try:
        with open(path, "rb") as f:
            image_data = f.read()
    except Exception as e:
<<<<<<< Updated upstream
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
=======
        return (current_state, components.ingredient_table_display_html(current_state or []),
                f"读取图片失败：{e}", components.ingredient_delete_choices(current_state or []))
    ext = os.path.splitext(path)[1].lower()
    mime = "image/png" if ext == ".png" else "image/jpeg"
    try:
        names = vlm_recognize_ingredients(image_data, mime_type=mime)
    except Exception as e:
        return (current_state, components.ingredient_table_display_html(current_state or []),
                f"VLM 识别失败：{e}", components.ingredient_delete_choices(current_state or []))
    if not names:
        return (current_state, components.ingredient_table_display_html(current_state or []),
                "图中未识别到火锅食材，请换一张图片试试。", components.ingredient_delete_choices(current_state or []))
>>>>>>> Stashed changes
    rows = table_ensure_rows(current_state)
    for name in names:
        if name and name.strip():
            rows.append([name.strip(), "", 1])
<<<<<<< Updated upstream
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
=======
    return (rows, components.ingredient_table_display_html(rows),
            f"已识别：{'、'.join(names)}", components.ingredient_delete_choices(rows))


def build_ingredient_placeholder():
    """获取示例食材列表，用于占位提示。"""
    r = api.get_available_ingredients()
    if not r.success or not r.data:
        return "肥牛、毛肚、鸭肠、虾滑、土豆、金针菇、菠菜"
    names = [x["name"] for x in r.data["ingredients"][:10]]
    return "、".join(names)


def load_preference_ui():
    """加载已保存的用户偏好。"""
    r = api.get_user_preferences()
    if not r.success:
        return "麻辣红汤", "标准", "普通", "", f"❌ {r.error}"
    prefs = r.data
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
    allergens = parsers.parse_allergens(allergen_text)
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
    """生成食材库说明 Markdown。"""
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


def show_generating():
    """点击生成后立即显示加载提示并切换到结果页。"""
    loading_md = (
        "## ⏳ 正在生成方案\n\n**请等待一下，方案即将生成…**\n\n"
        "正在调用大模型智能排序，请稍候。\n\n*（通常需要 10～30 秒）*"
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


def generate_and_go(ingredient_table, broth_label, texture_label, mode_label, allergen_text, num_people):
    """生成方案并返回 (markdown, new_step, v0,v1,v2,v3, step1_message, plan_data, plan_text)。"""
    md, step, plan_data = generate_plan_ui(
        ingredient_table, broth_label, texture_label, mode_label, allergen_text, num_people=num_people,
    )
    if step == 2:
        plan_text = components.plan_to_share_text(plan_data) if plan_data else ""
        return md, 2, gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), "", plan_data, plan_text
    return md, step, gr.update(visible=True), gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), md, None, ""


def start_eating(plan_data):
    """点击「开始吃饭」：进入步骤3，记录开始时间，预加载 TTS，返回底部文案与初始提醒。"""
    if not plan_data or not plan_data.get("timeline"):
        return (0, 2, gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(visible=False),
                "暂无方案数据，请先生成方案。", -1, -1,
                "<p style='color:#c0392b;padding:16px'>暂无方案数据，请先生成方案。</p>", "")
    import threading
    start_time = __import__("time").time()
    threading.Thread(target=timer.preload_all_tts_for_plan, args=(start_time, plan_data), daemon=True).start()
    num_people = plan_data.get("num_people") or 0
    head = f"**适合 {num_people} 人**\n\n" if num_people else ""
    lines = [f"- {w}" for w in plan_data.get("safety_warnings") or []]
    safety = "\n".join(lines) if lines else "无"
    lines = [f"- {t}" for t in plan_data.get("health_tips") or []]
    health = "\n".join(lines) if lines else "无"
    sauce_lines = [f"- **{food}**：{' / '.join(sauces)}" for food, sauces in (plan_data.get("sauce_recommendations") or {}).items()]
    sauce = "\n".join(sauce_lines) if sauce_lines else "无"
    bottom_md = head + f"### 🚨 安全提醒\n{safety}\n\n### 💚 健康贴士\n{health}\n\n### 🥢 蘸料推荐\n{sauce}"
    initial_reminder = "<p style='color:#aaa;text-align:center;padding:32px;font-size:.95em'>⏱ 计时已启动，请按方案顺序开始下锅。</p>"
    return (start_time, 3, gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=True),
            bottom_md, -1, -1, initial_reminder, "")


def search_ingredients_for_dropdown(query: str):
    """输入关键词模糊搜索食材库，返回最多 8 条匹配名称列表。"""
    if not query or not str(query).strip():
        return []
    results = search_ingredient(str(query).strip())
    return [r.name for r in results[:8]] if results else []


def batch_add_ingredients(batch_text: str, state: list):
    """批量添加食材：解析逗号/顿号/换行分隔的食材文本，批量追加到 state。"""
    names = parsers.parse_ingredients_from_text(batch_text or "")
    if not names:
        return (state, components.ingredient_table_display_html(state or []),
                "⚠️ 未解析到食材，请检查格式（用逗号、顿号或换行分隔）。",
                gr.update(choices=components.ingredient_delete_choices(state or []), value=None))
    state = list(state or [])
    added = []
    for name in names:
        name = name.strip()
        if name:
            state.append([name, "", 1])
            added.append(name)
    choices = components.ingredient_delete_choices(state)
    msg = f"✅ 已批量添加 {len(added)} 种食材：{'、'.join(added[:6])}{'…' if len(added) > 6 else ''}"
    return state, components.ingredient_table_display_html(state), msg, gr.update(choices=choices, value=None)


def copy_plan_html(plan_text: str) -> str:
    """返回复制方案到剪贴板的 HTML+JS。"""
    return components.copy_plan_html(plan_text)


def generate_qr_html(plan_text: str) -> str:
    """返回方案二维码 HTML。"""
    return components.generate_qr_html(plan_text)


def plan_to_share_text(plan_data) -> str:
    """将方案数据转换为适合分享的纯文本。"""
    return components.plan_to_share_text(plan_data)


def boiling_detect_callback(img_path):
    """拍照/上传图片后调用 API 检测火锅是否已开锅，返回结果 HTML。"""
    if img_path is None or not os.path.isfile(str(img_path or "")):
        return components.boiling_result_html("⚠️", "未沸", "请先拍摄或上传一张锅底照片", "")
    try:
        with open(img_path, "rb") as f:
            img_bytes = f.read()
    except Exception as e:
        return components.boiling_result_html("❌", "无法判断", f"读取图片失败：{e}", "")
    ext = os.path.splitext(img_path)[1].lower()
    mime = "image/png" if ext == ".png" else "image/jpeg"
    resp = api.detect_boiling(image_data=img_bytes, mime_type=mime)
    if not resp.success:
        return components.boiling_result_html("❌", "无法判断", f"检测失败：{resp.error}", "")
    d = resp.data
    icon = {"沸腾": "🔥", "微沸": "♨️", "未沸": "⏳", "无法判断": "❓"}.get(d["stage"], "❓")
    return components.boiling_result_html(icon, d["stage"], d["description"], d["advice"])
>>>>>>> Stashed changes
