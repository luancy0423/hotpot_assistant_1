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
    ("鸳鸯锅", "COMBO"),
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
    每行一条：名称 + 时间。时间可为秒数（90）、"1分钟"、"2分30秒"等；缺省时间按 120 秒。
    示例：田鸡 90\n蛇段 2分钟\n牛蛙, 120
    返回 (列表, 提示信息)：([{"name": "田鸡", "cooking_seconds": 90}, ...], "")
    """
    import re
    if not text or not text.strip():
        return [], ""
    out = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # 支持 "名称 时间" 或 "名称, 时间" 或 "名称，时间"
        parts = re.split(r"[\s,，]+", line, maxsplit=1)
        name = (parts[0] or "").strip()
        if not name:
            continue
        seconds = 120  # 默认
        if len(parts) > 1 and parts[1].strip():
            raw_time = parts[1].strip()
            # 纯数字 -> 秒
            if raw_time.isdigit():
                seconds = int(raw_time)
            else:
                # 尝试 "2分钟" "1分30秒" "90秒"
                m = re.search(r"(\d+)\s*分(?:\s*(\d+)\s*秒)?", raw_time)
                if m:
                    minutes = int(m.group(1))
                    sec = int(m.group(2)) if m.group(2) else 0
                    seconds = minutes * 60 + sec
                else:
                    sec_m = re.search(r"(\d+)\s*秒", raw_time)
                    if sec_m:
                        seconds = int(sec_m.group(1))
        out.append({"name": name, "cooking_seconds": min(999 * 60, max(10, seconds))})
    return out, ""


def _parse_ingredient_table(table) -> tuple:
    """
    从食材表格解析：常见食材名列表、特色食材列表、份数字典。
    表格每行：[食材名称, 涮煮时间(秒), 份数]。
    涮煮时间留空表示从数据库取默认时间；填写表示自定义/特色食材。
    返回 (names, custom_ingredients, portions)。
    """
    if table is None:
        return [], [], {}
    try:
        import pandas as pd
        if isinstance(table, pd.DataFrame):
            rows = table.fillna("").values.tolist()
        else:
            rows = [list(r) if isinstance(r, (list, tuple)) else [] for r in (table or [])]
    except Exception:
        rows = list(table) if table else []
    # 若第一行是表头则跳过
    if rows and len(rows[0]) >= 3 and rows[0][0] in ("食材名称", "名称"):
        rows = rows[1:]
    names = []
    custom_ingredients = []
    portions = {}
    for row in rows:
        if not row or len(row) < 1:
            continue
        name = (row[0] if row[0] is not None else "").strip() if isinstance(row[0], str) else str(row[0] or "").strip()
        if not name:
            continue
        time_val = row[1] if len(row) > 1 else None
        portion_val = row[2] if len(row) > 2 else None
        try:
            sec = None
            if time_val is not None and time_val != "":
                if isinstance(time_val, (int, float)):
                    sec = int(time_val)
                else:
                    sec = int(str(time_val).strip())
            if sec is not None and sec > 0:
                custom_ingredients.append({"name": name, "cooking_seconds": min(999 * 60, max(10, sec))})
            else:
                names.append(name)
        except (ValueError, TypeError):
            names.append(name)
        try:
            p = 1
            if portion_val is not None and portion_val != "":
                p = max(1, min(99, int(portion_val)))
            portions[name] = p
        except (ValueError, TypeError):
            portions[name] = 1
    return names, custom_ingredients, portions


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
    ingredient_table,
    broth_label: str,
    texture_label: str,
    mode_label: str,
    allergen_text: str,
    num_people: int = 2,
):
    """
    Gradio 回调：根据食材表格等输入生成涮煮方案并返回 Markdown。
    表格列：食材名称、涮煮时间(秒)（空则从库取）、份数。大模型 API Key 由系统预设。
    """
    broth_value = next((v for t, v in BROTH_CHOICES if t == broth_label), "SPICY")
    texture_value = next((v for t, v in TEXTURE_CHOICES if t == texture_label), "STANDARD")
    mode_value = next((v for t, v in MODE_CHOICES if t == mode_label), "NORMAL")
    allergens = _parse_allergens(allergen_text)
    num_people = max(1, min(99, int(num_people) if num_people is not None else 2))
    names, custom_ingredients, portions = _parse_ingredient_table(ingredient_table)

    if not names and not custom_ingredients:
        return "⚠️ 请在表格中至少填写一行「食材名称」。", 1, None  # 留在步骤1

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


def _get_default_seconds(name: str):
    """根据食材名称查库，返回默认涮煮秒数；未匹配返回 None。"""
    if not name or not str(name).strip():
        return None
    results = search_ingredient(str(name).strip())
    if not results:
        return None
    return results[0].cooking_rule.base_seconds


def _ingredient_lookup_hint(name, time_val=None):
    """输入食材名称时返回库内默认时间提示；若用户已填写具体时间则不再显示。"""
    try:
        if time_val is not None and time_val != "" and int(float(time_val)) > 0:
            return ""
    except (TypeError, ValueError):
        pass
    sec = _get_default_seconds(name)
    if sec is None:
        return ""
    return f"库内默认：**{sec} 秒**（可留空使用，填写则按您的时间）"


def _ingredient_table_display_rows(state):
    """
    将 state（list of [name, time_user, portion]）转为展示用行。
    涮煮时间：用户填了则显示数字；未填且库匹配则显示「N（库默认）」；否则不显示。
    """
    if not state:
        return []
    out = []
    for row in state:
        if not row or len(row) < 1:
            continue
        name = (row[0] or "").strip() if isinstance(row[0], str) else str(row[0] or "").strip()
        if not name:
            continue
        time_user = row[1] if len(row) > 1 else None
        portion = row[2] if len(row) > 2 else 1
        try:
            if portion is not None and portion != "":
                portion = max(1, min(99, int(portion)))
            else:
                portion = 1
        except (TypeError, ValueError):
            portion = 1
        # 用户填写了具体时间则只显示数字
        if time_user is not None and time_user != "":
            try:
                t = int(float(time_user))
                if t > 0:
                    time_display = str(t)
                else:
                    time_display = ""
            except (TypeError, ValueError):
                time_display = ""
        else:
            time_display = ""
        if not time_display:
            default_sec = _get_default_seconds(name)
            if default_sec is not None:
                time_display = f"{default_sec}（库默认）"
        out.append([name, time_display, portion])
    return out


def _ingredient_table_display_html(state):
    """
    将 state 转为只展示已填写的食材表格 HTML：固定表头、不上下滑动、无滚动条。
    """
    import html
    rows = _ingredient_table_display_rows(state)
    if not rows:
        return (
            "<div class='ingredient-table-wrap' id='ingredient-table-wrap'>"
            "<p class='ingredient-table-empty'>暂无食材，请在上方添加。</p></div>"
        )
    buf = [
        "<div class='ingredient-table-wrap' id='ingredient-table-wrap'>",
        "<table class='ingredient-display-table'>",
        "<thead><tr><th>食材名称</th><th>涮煮时间(秒)</th><th>份数</th></tr></thead>",
        "<tbody>",
    ]
    for row in rows:
        name = html.escape(str(row[0] if len(row) > 0 else ""))
        time_display = html.escape(str(row[1] if len(row) > 1 else ""))
        portion = html.escape(str(row[2] if len(row) > 2 else "1"))
        buf.append(f"<tr><td>{name}</td><td>{time_display}</td><td>{portion}</td></tr>")
    buf.append("</tbody></table></div>")
    return "".join(buf)


def _add_ingredient_row(name, time_val, portion, state):
    """将当前表单一行加入 state，返回新 state、展示表、清空表单与提示、删除行下拉选项。"""
    name = (name or "").strip() if isinstance(name, str) else str(name or "").strip()
    if not name:
        state = list(state or [])
        display = _ingredient_table_display_rows(state)
        choices = _ingredient_delete_choices(state)
        return state, display, "", 0, 1, "", choices
    state = list(state or [])
    try:
        p = 1
        if portion is not None and portion != "":
            p = max(1, min(99, int(portion)))
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
    display = _ingredient_table_display_rows(state)
    choices = _ingredient_delete_choices(state)
    return state, display, "", 0, 1, "", choices


def _ingredient_delete_choices(state):
    """根据当前 state 生成「选择要删除的行」下拉选项：第 i 行：名称。"""
    if not state:
        return []
    return [f"第{i+1}行：{(row[0] or '').strip() if isinstance(row[0], str) else str(row[0] or '')}" for i, row in enumerate(state) if row and (row[0] or '').strip()]


def _delete_last_ingredient_row(state):
    """删除最后一行，返回新 state 与展示表。"""
    state = list(state or [])
    if state:
        state.pop()
    display = _ingredient_table_display_rows(state)
    return state, display


def _delete_selected_ingredient_row(state, selected_label):
    """根据下拉选中的「第k行：名称」删除对应行，返回新 state、展示表、更新后的下拉选项。"""
    state = list(state or [])
    if not state or not selected_label or not str(selected_label).strip():
        choices = _ingredient_delete_choices(state)
        return state, _ingredient_table_display_rows(state), choices
    choices_before = _ingredient_delete_choices(state)
    try:
        idx = choices_before.index(selected_label)
    except ValueError:
        choices = _ingredient_delete_choices(state)
        return state, _ingredient_table_display_rows(state), choices
    state.pop(idx)
    display = _ingredient_table_display_rows(state)
    choices = _ingredient_delete_choices(state)
    return state, display, choices


def _table_ensure_rows(table, min_rows=1):
    """确保表格为 list of lists，且至少 min_rows 行（每行 3 列）。用于语音/图片识别追加。"""
    try:
        import pandas as pd
        if isinstance(table, pd.DataFrame):
            rows = table.fillna("").values.tolist()
        else:
            rows = [list(r) if isinstance(r, (list, tuple)) else [r, "", 1] for r in (table or [])]
    except Exception:
        rows = []
    for r in rows:
        while len(r) < 3:
            r.append("" if len(r) == 1 else 1)
    while len(rows) < min_rows:
        rows.append(["", "", 1])
    return rows


def voice_to_ingredients(audio_path, current_state):
    """
    语音识别并填入食材：将识别到的食材追加到当前列表（每行：名称、空、1）。
    返回 (新 state, 展示表行, 状态提示, 删除行下拉选项)
    """
    if not audio_path or not os.path.isfile(audio_path):
        display = _ingredient_table_display_rows(current_state)
        return current_state, display, "请先录制或上传一段语音（说菜名即可）。", _ingredient_delete_choices(current_state or [])
    try:
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
    except Exception as e:
        display = _ingredient_table_display_rows(current_state)
        return current_state, display, f"读取音频失败：{e}", _ingredient_delete_choices(current_state or [])
    result = api.input_from_voice(audio_data=audio_bytes)
    if not result.success:
        display = _ingredient_table_display_rows(current_state)
        return current_state, display, f"语音识别失败：{result.error}", _ingredient_delete_choices(current_state or [])
    names = result.data.get("ingredient_names") or []
    transcript = result.data.get("transcript") or ""
    if not names:
        display = _ingredient_table_display_rows(current_state)
        return current_state, display, f"未识别到食材。转写：「{(transcript[:50] + '…') if len(transcript) > 50 else transcript}」", _ingredient_delete_choices(current_state or [])
    rows = _table_ensure_rows(current_state)
    for name in names:
        if name and name.strip():
            rows.append([name.strip(), "", 1])
    display = _ingredient_table_display_rows(rows)
    short_transcript = (transcript[:30] + "…") if len(transcript) > 30 else transcript
    return rows, display, f"已识别：{'、'.join(names)}（转写：{short_transcript}）", _ingredient_delete_choices(rows)


def image_to_ingredients(image, current_state):
    """
    上传图片用 VLM 识别食材并填入：将识别到的食材追加到当前列表（每行：名称、空、1）。
    返回 (新 state, 展示表行, 状态提示, 删除行下拉选项)
    """
    if image is None:
        display = _ingredient_table_display_rows(current_state)
        return current_state, display, "请先上传一张图片（菜单、菜品或餐桌均可）。", _ingredient_delete_choices(current_state or [])
    if isinstance(image, str):
        path = image
    elif isinstance(image, dict):
        path = image.get("path") or image.get("name")
    else:
        path = getattr(image, "name", None) or getattr(image, "path", None)
    if not path or not os.path.isfile(path):
        display = _ingredient_table_display_rows(current_state)
        return current_state, display, "无法读取图片文件，请重新上传。", _ingredient_delete_choices(current_state or [])
    try:
        with open(path, "rb") as f:
            image_data = f.read()
    except Exception as e:
        display = _ingredient_table_display_rows(current_state)
        return current_state, display, f"读取图片失败：{e}", _ingredient_delete_choices(current_state or [])
    ext = os.path.splitext(path)[1].lower()
    mime = "image/png" if ext == ".png" else "image/jpeg"
    try:
        names = vlm_recognize_ingredients(image_data, mime_type=mime)
    except Exception as e:
        display = _ingredient_table_display_rows(current_state)
        return current_state, display, f"VLM 识别失败：{e}", _ingredient_delete_choices(current_state or [])
    if not names:
        display = _ingredient_table_display_rows(current_state)
        return current_state, display, "图中未识别到火锅食材，请换一张图片试试。", _ingredient_delete_choices(current_state or [])
    rows = _table_ensure_rows(current_state)
    for name in names:
        if name and name.strip():
            rows.append([name.strip(), "", 1])
    display = _ingredient_table_display_rows(rows)
    return rows, display, f"已识别：{'、'.join(names)}", _ingredient_delete_choices(rows)


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


# 模块加载时生成一次，供计时页提示音使用（语音提醒未启用时的兜底）
_BEEP_B64 = _make_beep_wav_base64()

# 阿里云千问 TTS 实时合成：北京地域 wss，中国内地用；可选 env HOTPOT_TTS_WS_URL 改为新加坡等
_TTS_ALIYUN_WS_URL = os.environ.get("HOTPOT_TTS_WS_URL", "wss://dashscope.aliyuncs.com/api-ws/v1/realtime")
_TTS_ALIYUN_MODEL = os.environ.get("HOTPOT_TTS_MODEL", "qwen3-tts-flash-realtime")


def _pcm_to_wav_base64(pcm_bytes: bytes, sample_rate: int = 24000, sample_width: int = 2, channels: int = 1) -> str:
    """将 PCM 裸流转为 WAV 并 base64 编码（用于阿里云 TTS 返回的 PCM）。"""
    n_frames = len(pcm_bytes) // (sample_width * channels)
    data_size = n_frames * sample_width * channels
    with io.BytesIO() as wav:
        wav.write(b"RIFF")
        wav.write(struct.pack("<I", 36 + data_size))
        wav.write(b"WAVEfmt ")
        wav.write(struct.pack("<IHHIIHH", 16, 1, channels, sample_rate, sample_rate * sample_width * channels, sample_width * channels, sample_width * 8))
        wav.write(b"data")
        wav.write(struct.pack("<I", data_size))
        wav.write(pcm_bytes[:data_size])
        wav.seek(0)
        return base64.b64encode(wav.read()).decode("ascii")


def _tts_aliyun_phrase_to_wav_base64(phrase: str):
    """
    使用阿里云千问 TTS 实时合成（DashScope），将中文文案转为语音。
    需配置 DASHSCOPE_API_KEY。返回 WAV 的 base64 字符串，失败返回 None。
    文档：https://help.aliyun.com/zh/model-studio/qwen-tts-realtime
    """
    if not phrase or not phrase.strip():
        return None
    api_key = (os.environ.get("DASHSCOPE_API_KEY") or "").strip()
    if not api_key:
        return None
    try:
        import threading
        import dashscope
        from dashscope.audio.qwen_tts_realtime import QwenTtsRealtime, QwenTtsRealtimeCallback, AudioFormat

        class _CollectCallback(QwenTtsRealtimeCallback):
            def __init__(self):
                self.complete_event = threading.Event()
                self.pcm_chunks = []

            def on_open(self):
                pass

            def on_close(self, close_status_code, close_msg):
                self.complete_event.set()

            def on_event(self, response):
                try:
                    if response.get("type") == "response.audio.delta" and response.get("delta"):
                        self.pcm_chunks.append(base64.b64decode(response["delta"]))
                    if response.get("type") == "session.finished":
                        self.complete_event.set()
                except Exception:
                    pass

            def wait_for_finished(self, timeout=15):
                self.complete_event.wait(timeout=timeout)

        dashscope.api_key = api_key
        callback = _CollectCallback()
        client = QwenTtsRealtime(
            model=_TTS_ALIYUN_MODEL,
            callback=callback,
            url=_TTS_ALIYUN_WS_URL,
        )
        client.connect()
        client.update_session(
            voice="Cherry",
            response_format=AudioFormat.PCM_24000HZ_MONO_16BIT,
            mode="server_commit",
        )
        client.append_text(phrase.strip())
        client.finish()
        callback.wait_for_finished()
        if not callback.pcm_chunks:
            return None
        pcm_data = b"".join(callback.pcm_chunks)
        return _pcm_to_wav_base64(pcm_data, sample_rate=24000, sample_width=2, channels=1)
    except Exception:
        return None


def _tts_phrase_to_audio_html(phrase: str):
    """
    将一句中文文案转为 TTS 语音，返回可 autoplay 的 <audio> HTML。
    使用阿里云千问 TTS（需配置 DASHSCOPE_API_KEY），失败返回空。
    """
    if not phrase or not phrase.strip():
        return ""
    wav_b64 = _tts_aliyun_phrase_to_wav_base64(phrase.strip())
    if wav_b64:
        return f'<audio autoplay><source src="data:audio/wav;base64,{wav_b64}" type="audio/wav"></audio>'
    return ""


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


def _generate_and_go(ingredient_table, broth_label, texture_label, mode_label, allergen_text, num_people):
    """生成方案并返回 (markdown, new_step, v0,v1,v2,v3, step1_message, plan_data)。失败时在步骤1显示错误。"""
    md, step, plan_data = generate_plan_ui(
        ingredient_table, broth_label, texture_label, mode_label, allergen_text, num_people=num_people,
    )
    if step == 2:
        return md, 2, gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), "", plan_data
    return md, step, gr.update(visible=True), gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), md, None


def _start_eating(plan_data):
    """点击「开始吃饭」：进入步骤 3，记录开始时间，并返回步骤 3 底部文案（安全/健康/蘸料）及初始提醒；同时后台一次性预生成本方案所有时间点的 TTS。"""
    if not plan_data or not plan_data.get("timeline"):
        return 0, 2, gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), "暂无方案数据，请先生成方案。", -1, -1, "⏱️ 已进行 **0 分 0 秒**\n\n暂无提醒。", ""
    start_time = time.time()
    import threading
    threading.Thread(target=_preload_all_tts_for_plan, args=(start_time, plan_data), daemon=True).start()
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


# 计时页「现在请下锅/捞出」提示只显示时长（秒），超时后自动消失
TIMER_PROMPT_DURATION_SEC = 10
# 到点时屏幕闪烁提醒时长（秒）
TIMER_FLASH_DURATION_SEC = 1
# 语音播放后保留 HTML 的秒数（避免下一 tick 覆盖导致播到一半停）
TIMER_VOICE_KEEP_HTML_SEC = 8

# 预加载 TTS 缓存：key=(start_time, time_seconds)，value=audio HTML（不含 flash）
# 「开始吃饭」时一次性后台生成本方案所有时间点的语音，计时过程中直接播缓存
_tts_preload_cache = {}
_tts_preload_lock = __import__("threading").Lock()
# 语音播放状态按 start_time 存，避免 Timer 只传 4 个输入时缺 State（Gradio 兼容）
_voice_timer_state_by_start = {}


def _flash_overlay_html():
    """返回 1 秒内淡出的全屏闪烁 overlay 的 HTML，用于下锅/捞出到点提醒。"""
    return (
        '<div class="hotpot-flash-overlay" style="'
        "position:fixed;inset:0;z-index:9999;pointer-events:none;"
        "background:rgba(255,140,0,0.35);"
        f"animation:hotpot-flash-fade {TIMER_FLASH_DURATION_SEC}s ease-out forwards;"
        '"></div>'
        "<style>@keyframes hotpot-flash-fade { 0% { opacity: 1; } 100% { opacity: 0; } }</style>"
    )


def _phrases_for_events_at_time(events, time_seconds, _ingredient_from_msg):
    """给定时间点，从事件列表里取出该秒的「下锅/捞出」并拼成播报句列表。"""
    phrases = []
    for e in events:
        if e.get("time_seconds") != time_seconds:
            continue
        action = e.get("action")
        name = _ingredient_from_msg(e.get("message")) or e.get("item_name") or e.get("message", "")
        if action == "下锅":
            phrases.append(f"现在请下锅，{name}")
        elif action in ("捞出", "捞起"):
            phrases.append(f"现在请捞出，{name}")
    return phrases


def _do_tts_preload_one(start_time, time_seconds, plan_data):
    """预加载某一秒的 TTS，写入 _tts_preload_cache。"""
    if not plan_data or not start_time or time_seconds is None:
        return
    events = (plan_data.get("timeline") or {}).get("events") or []
    def _ingredient_from_msg(msg):
        if not msg:
            return ""
        import re
        m = re.search(r"【([^】]+)】", msg)
        return m.group(1) if m else msg
    phrases = _phrases_for_events_at_time(events, time_seconds, _ingredient_from_msg)
    if not phrases:
        return
    combined = "。".join(phrases)
    html = _tts_phrase_to_audio_html(combined)
    if html:
        with _tts_preload_lock:
            _tts_preload_cache[(start_time, time_seconds)] = html


def _preload_all_tts_for_plan(start_time, plan_data):
    """
    后台线程：根据方案时间线，按时间顺序一次性生成所有「下锅/捞出」时间点的 TTS，
    写入 _tts_preload_cache。点击「开始吃饭」时调用，计时过程中直接播缓存，无卡顿。
    """
    if not plan_data or not start_time:
        return
    events = (plan_data.get("timeline") or {}).get("events") or []
    if not events:
        return
    unique_seconds = sorted(set(e.get("time_seconds") for e in events if e.get("time_seconds") is not None))
    for t in unique_seconds:
        _do_tts_preload_one(start_time, t, plan_data)


def _timer_tick(plan_data, start_time, last_put_sec, last_take_sec):
    """每秒调用：根据已过时间生成「应下锅/应捞出」提醒，并在新事件时触发语音播报。语音在「开始吃饭」时已一次性预生成，到点直接播缓存；播报后保留 HTML 数秒避免被下一 tick 覆盖导致播到一半停。语音状态用模块级 _voice_timer_state_by_start 存储，兼容 Gradio Timer 只传 4 个输入。"""
    if not plan_data or not start_time or start_time <= 0:
        return "等待开始…", last_put_sec or -1, last_take_sec or -1, ""
    state = _voice_timer_state_by_start.setdefault(start_time, {"last_voice_html": "", "voice_played_at_elapsed": -1})
    last_voice_html = state.get("last_voice_html") or ""
    voice_played_at_elapsed = state.get("voice_played_at_elapsed", -1)
    if voice_played_at_elapsed is None:
        voice_played_at_elapsed = -1
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
    show_put = cur_put and (elapsed < cur_put["time_seconds"] + TIMER_PROMPT_DURATION_SEC)
    show_take = cur_take and (elapsed < cur_take["time_seconds"] + TIMER_PROMPT_DURATION_SEC)
    new_put_sec = (cur_put["time_seconds"] if cur_put else (last_put_sec if last_put_sec is not None else -1))
    new_take_sec = (cur_take["time_seconds"] if cur_take else (last_take_sec if last_take_sec is not None else -1))
    last_put_sec = last_put_sec if last_put_sec is not None else -1
    last_take_sec = last_take_sec if last_take_sec is not None else -1

    def _ingredient_from_msg(msg):
        if not msg:
            return ""
        import re
        m = re.search(r"【([^】]+)】", msg)
        return m.group(1) if m else msg

    # 仅在新到点时播报语音（语音已在「开始吃饭」时一次性预生成，此处直接取缓存或回退现场 TTS）
    play_voice = False
    voice_put_new = cur_put and cur_put["time_seconds"] > last_put_sec
    voice_take_new = cur_take and cur_take["time_seconds"] > last_take_sec
    if voice_put_new or voice_take_new:
        play_voice = True

    m = int(elapsed // 60)
    s = int(elapsed % 60)
    time_str = f"⏱️ 已进行 **{m} 分 {s} 秒**"
    reminder_lines = [time_str, ""]
    if show_put:
        name_put = _ingredient_from_msg(cur_put.get("message")) or cur_put.get("item_name") or cur_put.get("message", "")
        reminder_lines.append(f"## ⬇️ 现在请下锅：**{name_put}**")
    if show_take:
        name_take = _ingredient_from_msg(cur_take.get("message")) or cur_take.get("item_name") or cur_take.get("message", "")
        reminder_lines.append(f"## ⬆️ 现在请捞出：**{name_take}**")
    if not show_put and not show_take:
        reminder_lines.append("暂无提醒，请按方案顺序操作。")
    if next_put:
        sec = next_put["time_seconds"] - elapsed
        name = _ingredient_from_msg(next_put.get("message")) or next_put.get("item_name") or next_put.get("message", "")
        reminder_lines.append(f"\n*即将下锅：{name}（约 {sec} 秒后）*")
    if next_take:
        sec = next_take["time_seconds"] - elapsed
        name = _ingredient_from_msg(next_take.get("message")) or next_take.get("item_name") or next_take.get("message", "")
        reminder_lines.append(f"*即将捞出：{name}（约 {sec} 秒后）*")

    # 语音：到点优先用预加载缓存，避免卡顿；播报后保留 HTML TIMER_VOICE_KEEP_HTML_SEC 秒，避免下一 tick 覆盖导致播到一半停
    voice_html_out = ""
    if play_voice:
        phrases = []
        if voice_put_new and cur_put:
            name = _ingredient_from_msg(cur_put.get("message")) or cur_put.get("item_name") or cur_put.get("message", "")
            phrases.append(f"现在请下锅，{name}")
        if voice_take_new and cur_take:
            name = _ingredient_from_msg(cur_take.get("message")) or cur_take.get("item_name") or cur_take.get("message", "")
            phrases.append(f"现在请捞出，{name}")
        if phrases:
            # 用当前播报事件所在秒作为缓存 key（仅捞出时若用 cur_put 会错用上一秒的下锅时间，导致取不到捞出预加载）
            event_sec = None
            if voice_put_new and cur_put:
                event_sec = cur_put["time_seconds"]
            elif voice_take_new and cur_take:
                event_sec = cur_take["time_seconds"]
            if event_sec is not None:
                cache_key = (start_time, event_sec)
                with _tts_preload_lock:
                    voice_html_out = (_tts_preload_cache.pop(cache_key, None) or "").strip()
            if not voice_html_out or voice_html_out == "None":
                voice_html_out = _tts_phrase_to_audio_html("。".join(phrases))
            if not voice_html_out and _BEEP_B64:
                voice_html_out = f'<audio autoplay><source src="data:audio/wav;base64,{_BEEP_B64}" type="audio/wav"></audio>'
        else:
            if _BEEP_B64:
                voice_html_out = f'<audio autoplay><source src="data:audio/wav;base64,{_BEEP_B64}" type="audio/wav"></audio>'
        voice_html_out = (voice_html_out or "") + _flash_overlay_html()
        _voice_timer_state_by_start[start_time] = {"last_voice_html": voice_html_out, "voice_played_at_elapsed": elapsed}
    else:
        # 未到新到点：若距离上次播报不足 TIMER_VOICE_KEEP_HTML_SEC 秒，继续显示上次 HTML，避免覆盖导致播到一半停
        if last_voice_html and voice_played_at_elapsed >= 0 and (elapsed - voice_played_at_elapsed) < TIMER_VOICE_KEEP_HTML_SEC:
            voice_html_out = last_voice_html
        else:
            voice_html_out = ""
        _voice_timer_state_by_start[start_time] = {"last_voice_html": last_voice_html or "", "voice_played_at_elapsed": voice_played_at_elapsed}

    return "\n".join(reminder_lines), new_put_sec, new_take_sec, voice_html_out


def create_ui():
    """构建 Gradio 界面：步骤1 食材 → 步骤2 锅底/偏好 → 步骤3 方案结果 → 步骤4 吃饭计时。"""
    _head_script = r"""
<script>
(function(){
  function clearScrollOnAncestors(startEl) {
    if (!startEl) return;
    var el = startEl;
    while (el && el !== document.body) {
      var cs = window.getComputedStyle(el);
      var needFix = cs.overflowY === 'auto' || cs.overflowY === 'scroll' || cs.overflow === 'auto' || cs.overflow === 'scroll' || (cs.maxHeight && cs.maxHeight !== 'none');
      if (needFix) {
        el.style.setProperty('overflow-y', 'visible', 'important');
        el.style.setProperty('overflow', 'visible', 'important');
        el.style.setProperty('max-height', 'none', 'important');
      }
      el = el.parentElement;
    }
  }
  function fixScrolls() {
    clearScrollOnAncestors(document.getElementById('ingredient-table-wrap'));
    clearScrollOnAncestors(document.getElementById('ingredient-form-row'));
  }
  function runFix() {
    fixScrolls();
    setTimeout(fixScrolls, 100);
    setTimeout(fixScrolls, 500);
    setTimeout(fixScrolls, 1200);
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', runFix);
  } else {
    runFix();
  }
  var observer = new MutationObserver(function() { fixScrolls(); });
  observer.observe(document.body, { childList: true, subtree: true });
})();
</script>
"""
    with gr.Blocks(title="涮涮AI - 智能火锅助手", head=_head_script) as demo:
        gr.Markdown("# 🍲 涮涮AI — 智能火锅助手")
        step_state = gr.State(0)
        plan_data_state = gr.State(None)
        start_time_state = gr.State(0)
        last_beeped_put = gr.State(-1)
        last_beeped_take = gr.State(-1)

        # 步骤 0：输入食材（表单添加 + 只读表格）
        step0 = gr.Column(visible=True, elem_id="step0-ingredients")
        ingredient_table_state = gr.State([])  # list of [name, time_user, portion]，time_user 为空表示用库默认
        with step0:
            gr.Markdown("### 步骤 1/3：输入食材")
            gr.Markdown("**请在下方填写食材名称后点击「添加一行」加入列表；涮煮时间可留空使用库内默认，份数默认为 1。**")
            with gr.Row(equal_height=True, elem_id="ingredient-form-row"):
                ingredient_name_input = gr.Textbox(
                    label="食材名称",
                    placeholder="如：毛肚、肥牛、土豆片",
                    scale=2,
                    lines=2,
                )
                ingredient_time_input = gr.Slider(
                    label="涮煮时间(秒)",
                    minimum=0,
                    maximum=600,
                    value=0,
                    step=5,
                    info="留空使用库默认",
                    scale=1,
                )
                ingredient_portion_input = gr.Slider(
                    label="份数",
                    minimum=1,
                    maximum=99,
                    value=1,
                    step=1,
                    scale=1,
                )
            ingredient_default_hint = gr.Markdown(value="", visible=True)
            with gr.Row(equal_height=True, elem_id="ingredient-actions-row"):
                btn_add_row = gr.Button("➕ 添加一行", variant="primary")
                ingredient_delete_dd = gr.Dropdown(
                    label="选择要删除的行",
                    choices=[],
                    value=None,
                    allow_custom_value=False,
                    scale=2,
                )
                btn_del_selected = gr.Button("删除所选行", variant="secondary")
            gr.Markdown("**已添加的食材**")
            ingredient_table = gr.HTML(
                value=_ingredient_table_display_html([]),
                elem_id="ingredient-table-html",
                elem_classes=["ingredient-table-no-scroll"],
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
            gr.Markdown("**或一键接入商家点餐系统**")
            merchant_status = gr.Markdown(value="", visible=True)
            btn_merchant = gr.Button("🔗 一键接入商家点餐系统", size="sm", variant="secondary")
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

        def _update_hint(name, time_val):
            return _ingredient_lookup_hint(name, time_val)
        ingredient_name_input.change(
            fn=_update_hint,
            inputs=[ingredient_name_input, ingredient_time_input],
            outputs=[ingredient_default_hint],
        )
        ingredient_time_input.change(
            fn=_update_hint,
            inputs=[ingredient_name_input, ingredient_time_input],
            outputs=[ingredient_default_hint],
        )
        def _add_row_and_update_dropdown(name, time_val, portion, state):
            state, _, _, t, p, _, choices = _add_ingredient_row(name, time_val, portion, state)
            return state, _ingredient_table_display_html(state), "", t, p, "", gr.update(choices=choices, value=None)
        btn_add_row.click(
            fn=_add_row_and_update_dropdown,
            inputs=[ingredient_name_input, ingredient_time_input, ingredient_portion_input, ingredient_table_state],
            outputs=[ingredient_table_state, ingredient_table, ingredient_name_input, ingredient_time_input, ingredient_portion_input, ingredient_default_hint, ingredient_delete_dd],
        )
        def _on_delete_selected(state, selected):
            new_state, _, choices = _delete_selected_ingredient_row(state, selected)
            return new_state, _ingredient_table_display_html(new_state), gr.update(choices=choices, value=None)
        btn_del_selected.click(
            fn=_on_delete_selected,
            inputs=[ingredient_table_state, ingredient_delete_dd],
            outputs=[ingredient_table_state, ingredient_table, ingredient_delete_dd],
        )
        def _image_and_dropdown(image, state):
            state, _, status, choices = image_to_ingredients(image, state)
            return state, _ingredient_table_display_html(state), status, gr.update(choices=choices, value=None)
        btn_image.click(
            fn=_image_and_dropdown,
            inputs=[image_input, ingredient_table_state],
            outputs=[ingredient_table_state, ingredient_table, image_status, ingredient_delete_dd],
        )
        def _voice_and_dropdown(audio, state):
            state, _, status, choices = voice_to_ingredients(audio, state)
            return state, _ingredient_table_display_html(state), status, gr.update(choices=choices, value=None)
        btn_voice.click(
            fn=_voice_and_dropdown,
            inputs=[voice_input, ingredient_table_state],
            outputs=[ingredient_table_state, ingredient_table, voice_status, ingredient_delete_dd],
        )

        def _merchant_connect_placeholder(current_state):
            """虚拟按键：暂未适配商家点餐系统，仅提示。"""
            choices = _ingredient_delete_choices(current_state or [])
            return current_state, _ingredient_table_display_html(current_state or []), "⚠️ 暂未适配商家点餐系统，敬请期待。您可先手动填写食材表、或使用图片/语音识别。", gr.update(choices=choices, value=None)

        btn_merchant.click(
            fn=_merchant_connect_placeholder,
            inputs=[ingredient_table_state],
            outputs=[ingredient_table_state, ingredient_table, merchant_status, ingredient_delete_dd],
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
                ingredient_table_state,
                broth_dd,
                texture_dd,
                mode_dd,
                allergen_input,
                num_people_input,
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
        share=os.environ.get("HOTPOT_GRADIO_SHARE", "").strip() in ("1", "true", "yes"),  # 需公网链接时设 HOTPOT_GRADIO_SHARE=1
        theme=gr.themes.Soft(primary_hue="orange"),
        css="""
        .main-header { font-size: 1.4em; margin-bottom: 0.5em; }
        .gr-markdown { font-size: 0.95em; }
        .timer-reminder { font-size: 1.2em; }
        #ingredient-form-row > div, #ingredient-actions-row > div { align-self: stretch; display: flex; flex-direction: column; }
        #ingredient-form-row .wrap, #ingredient-actions-row .wrap { flex: 1; display: flex; flex-direction: column; min-height: 0; }
        /* 食材名称/涮煮时间/份数 所在行及包裹它的块：禁止滚动 */
        #ingredient-form-row,
        #ingredient-form-row *,
        #step0-ingredients div:has(#ingredient-form-row) {
            overflow: visible !important;
            overflow-y: visible !important;
            max-height: none !important;
        }
        /* 食材表格区域：禁止上下滚动、隐藏滚动条 */
        #ingredient-table-html,
        .ingredient-table-no-scroll,
        #ingredient-table-html *,
        .ingredient-table-no-scroll *,
        .ingredient-table-wrap,
        .ingredient-table-wrap * {
            overflow: visible !important;
            overflow-x: visible !important;
            overflow-y: visible !important;
            max-height: none !important;
        }
        /* step0 列及其中包裹食材表格的任意祖先：禁止最大高度与滚动 */
        #step0-ingredients,
        #step0-ingredients div:has(#ingredient-table-html),
        #step0-ingredients div:has(.ingredient-table-no-scroll) {
            overflow: visible !important;
            max-height: none !important;
        }
        .ingredient-table-wrap .ingredient-display-table { width: 100%; border-collapse: collapse; }
        .ingredient-table-wrap .ingredient-display-table th,
        .ingredient-table-wrap .ingredient-display-table td { border: 1px solid var(--border-color-primary, #e5e7eb); padding: 0.4em 0.6em; text-align: left; }
        .ingredient-table-wrap .ingredient-display-table th { background: var(--block-background-fill, #e5e7eb) !important; color: var(--body-text-color, #111827) !important; font-weight: 600; }
        .ingredient-table-wrap .ingredient-display-table td { background: var(--background-fill-secondary, var(--block-background-fill, #f9fafb)) !important; color: var(--body-text-color, #111827) !important; }
        .ingredient-table-empty { color: var(--body-text-color-secondary, #6b7280); margin: 0.5em 0; font-size: 0.95em; }
        /* 隐藏该区域内可能出现的滚动条 */
        #step0-ingredients ::-webkit-scrollbar { display: none !important; }
        #ingredient-table-html ::-webkit-scrollbar { display: none !important; }
        .ingredient-table-wrap ::-webkit-scrollbar { display: none !important; }
        """,
    )
