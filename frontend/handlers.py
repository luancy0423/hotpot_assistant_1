# -*- coding: utf-8 -*-
"""
涮涮AI - 前端事件回调
generate_plan、start_eating、食材增删、语音/识图、偏好加载保存、搜索补全等。
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

    try:
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
    except Exception as e:
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

    rows = table_ensure_rows(current_state)
    for name in names:
        if name and name.strip():
            rows.append([name.strip(), "", 1])
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

    try:
        with open(path, "rb") as f:
            image_data = f.read()
    except Exception as e:
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

    rows = table_ensure_rows(current_state)
    for name in names:
        if name and name.strip():
            rows.append([name.strip(), "", 1])
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


def show_generating(app_state):
    """点击生成后立即显示加载提示并切换到结果页，透传 app_state。"""
    from frontend.state import AppState
    loading_md = (
        "## ⏳ 正在生成方案\n\n**请等待一下，方案即将生成…**\n\n"
        "正在调用大模型智能排序，请稍候。\n\n*（通常需要 10～30 秒）*"
    )
    app_state = app_state or AppState()
    return (
        loading_md,
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=False),
        "",
        app_state,
    )


def generate_and_go(app_state, broth_label, texture_label, mode_label, allergen_text, num_people):
    """生成方案并返回 (markdown, new_app_state, v0,v1,v2,v3, status)。plan_text 写入 app_state。"""
    from frontend.state import AppState
    app_state = app_state or AppState()
    md, step, plan_data = generate_plan_ui(
        app_state.ingredients, broth_label, texture_label, mode_label, allergen_text, num_people=num_people,
    )
    if step == 2 and plan_data is not None:
        plan_text = components.plan_to_share_text(plan_data) if plan_data else ""
        new_state = app_state.with_step(2).with_plan(plan_data).with_plan_text(plan_text)
        return md, new_state, gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), ""
    new_state = app_state.with_step(1)
    return md, new_state, gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), md


def start_eating(app_state):
    """点击「开始吃饭」：进入步骤3，将开始时间与 last_beeped 写入 app_state，返回底部文案与初始提醒。"""
    from frontend.state import AppState
    app_state = app_state or AppState()
    plan_data = app_state.plan_data
    if not plan_data or not plan_data.get("timeline"):
        return (app_state, gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(visible=False),
                "暂无方案数据，请先生成方案。",
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
    new_state = app_state.with_step(3).with_timer_start(start_time)
    return (new_state, gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=True),
            bottom_md, initial_reminder, "")


def search_ingredients_for_dropdown(query: str):
    """输入关键词模糊搜索食材库，返回最多 8 条匹配名称列表。"""
    if not query or not str(query).strip():
        return []
    results = search_ingredient(str(query).strip())
    return [r.name for r in results[:8]] if results else []


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

