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
        use_llm_sort=bool(
            os.environ.get("HOTPOT_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
        ),
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
            "<p class='ingredient-table-empty'>暂无食材，请在上方添加。</p>"
            "</div>"
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
    返回 (新 state, 展示表HTML, 状态提示, 删除行下拉选项)
    """
    if not audio_path or not os.path.isfile(audio_path):
        return current_state, _ingredient_table_display_html(current_state or []), "请先录制或上传一段语音（说菜名即可）。", _ingredient_delete_choices(current_state or [])
    try:
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
    except Exception as e:
        return current_state, _ingredient_table_display_html(current_state or []), f"读取音频失败：{e}", _ingredient_delete_choices(current_state or [])
    result = api.input_from_voice(audio_data=audio_bytes)
    if not result.success:
        return current_state, _ingredient_table_display_html(current_state or []), f"语音识别失败：{result.error}", _ingredient_delete_choices(current_state or [])
    names = result.data.get("ingredient_names") or []
    transcript = result.data.get("transcript") or ""
    if not names:
        return current_state, _ingredient_table_display_html(current_state or []), f"未识别到食材。转写：「{(transcript[:50] + '…') if len(transcript) > 50 else transcript}」", _ingredient_delete_choices(current_state or [])
    rows = _table_ensure_rows(current_state)
    for name in names:
        if name and name.strip():
            rows.append([name.strip(), "", 1])
    short_transcript = (transcript[:30] + "…") if len(transcript) > 30 else transcript
    return rows, _ingredient_table_display_html(rows), f"已识别：{'、'.join(names)}（转写：{short_transcript}）", _ingredient_delete_choices(rows)


def image_to_ingredients(image, current_state):
    """
    上传图片用 VLM 识别食材并填入：将识别到的食材追加到当前列表（每行：名称、空、1）。
    返回 (新 state, 展示表HTML, 状态提示, 删除行下拉选项)
    """
    if image is None:
        return current_state, _ingredient_table_display_html(current_state or []), "请先上传一张图片（菜单、菜品或餐桌均可）。", _ingredient_delete_choices(current_state or [])
    if isinstance(image, str):
        path = image
    elif isinstance(image, dict):
        path = image.get("path") or image.get("name")
    else:
        path = getattr(image, "name", None) or getattr(image, "path", None)
    if not path or not os.path.isfile(path):
        return current_state, _ingredient_table_display_html(current_state or []), "无法读取图片文件，请重新上传。", _ingredient_delete_choices(current_state or [])
    try:
        with open(path, "rb") as f:
            image_data = f.read()
    except Exception as e:
        return current_state, _ingredient_table_display_html(current_state or []), f"读取图片失败：{e}", _ingredient_delete_choices(current_state or [])
    ext = os.path.splitext(path)[1].lower()
    mime = "image/png" if ext == ".png" else "image/jpeg"
    try:
        names = vlm_recognize_ingredients(image_data, mime_type=mime)
    except Exception as e:
        return current_state, _ingredient_table_display_html(current_state or []), f"VLM 识别失败：{e}", _ingredient_delete_choices(current_state or [])
    if not names:
        return current_state, _ingredient_table_display_html(current_state or []), "图中未识别到火锅食材，请换一张图片试试。", _ingredient_delete_choices(current_state or [])
    rows = _table_ensure_rows(current_state)
    for name in names:
        if name and name.strip():
            rows.append([name.strip(), "", 1])
    return rows, _ingredient_table_display_html(rows), f"已识别：{'、'.join(names)}", _ingredient_delete_choices(rows)


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


def _nav_restart_from_timer(step, start_time):
    """从计时页返回：步骤 3 -> 0，同时清理该 session 的缓存防内存泄漏。"""
    if start_time and start_time > 0:
        _cleanup_timer_state(start_time)
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
    """生成方案并返回 (markdown, new_step, v0,v1,v2,v3, step1_message, plan_data, plan_text)。失败时在步骤1显示错误。"""
    md, step, plan_data = generate_plan_ui(
        ingredient_table, broth_label, texture_label, mode_label, allergen_text, num_people=num_people,
    )
    if step == 2:
        plan_text = _plan_to_share_text(plan_data) if plan_data else ""
        return md, 2, gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), "", plan_data, plan_text
    return md, step, gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), md, None, ""


def _start_eating(plan_data):
    """点击「开始吃饭」：进入步骤 3，记录开始时间，并返回步骤 3 底部文案（安全/健康/蘸料）及初始提醒；同时后台一次性预生成本方案所有时间点的 TTS。"""
    if not plan_data or not plan_data.get("timeline"):
        return 0, 2, gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), "暂无方案数据，请先生成方案。", -1, -1, "<p style='color:#c0392b;padding:16px'>暂无方案数据，请先生成方案。</p>", ""
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
    initial_reminder = "<p style='color:#aaa;text-align:center;padding:32px;font-size:.95em'>⏱ 计时已启动，请按方案顺序开始下锅。</p>"
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
# 最多同时保留的 session 数，防止长时间运行内存持续增长
_TIMER_STATE_MAX_SESSIONS = 5


def _cleanup_timer_state(start_time: float):
    """结束计时时清理该 start_time 对应的全部缓存，并对两个全局字典做 LRU 兜底。"""
    with _tts_preload_lock:
        # 精确清除当前 session 的 TTS 预加载条目
        for k in [k for k in _tts_preload_cache if k[0] == start_time]:
            del _tts_preload_cache[k]
        # LRU 兜底：超出上限时删除最旧 session 的全部条目
        sessions = sorted({k[0] for k in _tts_preload_cache})
        while len(sessions) > _TIMER_STATE_MAX_SESSIONS:
            oldest = sessions.pop(0)
            for k in [k for k in _tts_preload_cache if k[0] == oldest]:
                del _tts_preload_cache[k]
    # 清除语音状态
    _voice_timer_state_by_start.pop(start_time, None)
    # LRU 兜底
    if len(_voice_timer_state_by_start) > _TIMER_STATE_MAX_SESSIONS:
        for k in sorted(_voice_timer_state_by_start)[:-_TIMER_STATE_MAX_SESSIONS]:
            _voice_timer_state_by_start.pop(k, None)


def _ingredient_from_msg(msg: str) -> str:
    """从事件 message 字段提取食材名称（格式：…【名称】…）。"""
    if not msg:
        return ""
    import re
    m = re.search(r"【([^】]+)】", msg)
    return m.group(1) if m else msg


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


def _build_timer_html(elapsed: int, total_seconds: int,
                      show_put: bool, show_take: bool,
                      name_put: str, name_take: str,
                      next_put_info, next_take_info,
                      items: list) -> str:
    """
    生成计时页的富文本 HTML 面板，包含：
      · 大字时钟 + 整体进度条
      · 当前操作卡片（橙色=下锅 / 绿色=捞出 / 虚线=等待）
      · 即将操作预告
      · 各食材状态列表（等待 / 进行中+小进度条 / 已完成✓）
    """
    import html as _html

    m_e, s_e = elapsed // 60, elapsed % 60
    m_t, s_t = total_seconds // 60, total_seconds % 60
    pct = min(100, int(elapsed / max(total_seconds, 1) * 100)) if total_seconds > 0 else 0
    bar_color = "#e65c00" if pct < 85 else "#c0392b"

    # ── 时钟 ──────────────────────────────────────────────────
    clock = f"""
    <div style="text-align:center;padding:18px 0 6px">
      <div style="font-size:3em;font-weight:700;letter-spacing:2px;color:#e65c00;line-height:1.1">
        {m_e:02d}<span style="opacity:.55;font-size:.65em">分</span>{s_e:02d}<span style="opacity:.55;font-size:.65em">秒</span>
      </div>
      <div style="font-size:.82em;color:#999;margin-top:4px">总时长 {m_t}分{s_t:02d}秒</div>
    </div>"""

    # ── 进度条 ────────────────────────────────────────────────
    progress = f"""
    <div style="margin:4px 20px 4px">
      <div style="background:#f0f0f0;border-radius:8px;height:10px;overflow:hidden">
        <div style="width:{pct}%;height:100%;background:{bar_color};border-radius:8px;transition:width .9s ease"></div>
      </div>
    </div>
    <div style="text-align:center;font-size:.78em;color:#bbb;margin-bottom:12px">{pct}% 完成</div>"""

    # ── 当前操作卡片 ──────────────────────────────────────────
    cards = ""
    if show_put:
        cards += f"""
        <div style="margin:6px 16px;padding:14px 18px;border-radius:12px;
                    background:linear-gradient(135deg,#fff3e0,#ffe0b2);
                    border-left:5px solid #e65c00;box-shadow:0 2px 8px rgba(230,92,0,.14)">
          <div style="font-size:.72em;font-weight:700;color:#e65c00;letter-spacing:1px;margin-bottom:3px">⬇ 现在下锅</div>
          <div style="font-size:1.65em;font-weight:700;color:#333">{_html.escape(name_put)}</div>
        </div>"""
    if show_take:
        cards += f"""
        <div style="margin:6px 16px;padding:14px 18px;border-radius:12px;
                    background:linear-gradient(135deg,#e8f5e9,#c8e6c9);
                    border-left:5px solid #2e7d32;box-shadow:0 2px 8px rgba(46,125,50,.14)">
          <div style="font-size:.72em;font-weight:700;color:#2e7d32;letter-spacing:1px;margin-bottom:3px">⬆ 现在捞出</div>
          <div style="font-size:1.65em;font-weight:700;color:#333">{_html.escape(name_take)}</div>
        </div>"""
    if not show_put and not show_take:
        cards = """
        <div style="margin:6px 16px;padding:14px 18px;border-radius:12px;
                    background:#fafafa;border:1.5px dashed #e0e0e0;
                    text-align:center;color:#bbb;font-size:.95em">
          暂无操作，稍作等待…
        </div>"""

    # ── 即将到来预告 ──────────────────────────────────────────
    upcoming = ""
    rows = []
    if next_put_info:
        sec, name = next_put_info
        rows.append(f'<span style="color:#e65c00">⬇ {_html.escape(name)}</span>（{sec} 秒后下锅）')
    if next_take_info:
        sec, name = next_take_info
        rows.append(f'<span style="color:#2e7d32">⬆ {_html.escape(name)}</span>（{sec} 秒后捞出）')
    if rows:
        upcoming = f"""
        <div style="margin:4px 16px 10px;padding:9px 14px;border-radius:8px;
                    background:#f8f9fa;font-size:.84em;color:#555;line-height:1.9">
          <span style="font-weight:600;color:#aaa;font-size:.8em;display:block;margin-bottom:2px">即将操作</span>
          {"<br>".join(rows)}
        </div>"""

    # ── 食材状态列表 ──────────────────────────────────────────
    status_rows_html = ""
    if items:
        cumulative = 0
        for item in items:
            iname  = item.get("ingredient_name", "")
            cook   = item.get("cooking_seconds", 0)
            put_t  = item.get("start_offset_seconds", cumulative)
            take_t = put_t + cook
            cumulative = max(cumulative, put_t) + cook

            if elapsed < put_t:
                dot   = "#ccc"
                badge = f"<span style='color:#bbb'>等待（{put_t - elapsed}秒后下锅）</span>"
                bg    = "#fafafa"
            elif elapsed < take_t:
                done_pct = min(100, int((elapsed - put_t) / max(cook, 1) * 100))
                dot   = "#e65c00"
                badge = (f"<span style='color:#e65c00'>进行中，还需 {take_t - elapsed} 秒</span>"
                         f"<div style='margin-top:4px;height:4px;background:#f0e0d0;border-radius:4px;overflow:hidden'>"
                         f"<div style='width:{done_pct}%;height:100%;background:#e65c00;border-radius:4px'></div></div>")
                bg    = "#fff8f0"
            else:
                dot   = "#2e7d32"
                badge = "<span style='color:#2e7d32;font-weight:600'>✓ 已捞出</span>"
                bg    = "#f0fff4"

            status_rows_html += f"""
            <tr style="background:{bg}">
              <td style="padding:7px 10px;font-size:.88em;font-weight:600;white-space:nowrap">
                <span style="display:inline-block;width:8px;height:8px;border-radius:50%;
                             background:{dot};margin-right:7px;vertical-align:middle"></span>
                {_html.escape(iname)}
              </td>
              <td style="padding:7px 10px;font-size:.82em;width:100%">{badge}</td>
            </tr>"""

    status_block = ""
    if status_rows_html:
        status_block = f"""
        <div style="margin:8px 16px 18px;border-radius:10px;overflow:hidden;
                    border:1px solid #eee;box-shadow:0 1px 4px rgba(0,0,0,.05)">
          <div style="padding:7px 12px;background:#f5f5f5;
                      font-size:.73em;font-weight:700;color:#999;letter-spacing:.5px">食材状态</div>
          <table style="width:100%;border-collapse:collapse">{status_rows_html}</table>
        </div>"""

    return f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
                max-width:560px;margin:0 auto;border-radius:16px;overflow:hidden;
                border:1px solid #ffe0b2;background:#fff;
                box-shadow:0 4px 18px rgba(230,92,0,.10)">
      {clock}{progress}{cards}{upcoming}{status_block}
    </div>"""


def _timer_tick(plan_data, start_time, last_put_sec, last_take_sec):
    """每秒调用：计算当前进度，返回可视化 HTML + 语音播报 HTML。"""
    if not plan_data or not start_time or start_time <= 0:
        return ("<p style='color:#bbb;text-align:center;padding:40px;font-size:.95em'>"
                "等待开始…</p>"), last_put_sec or -1, last_take_sec or -1, ""

    state = _voice_timer_state_by_start.setdefault(
        start_time, {"last_voice_html": "", "voice_played_at_elapsed": -1}
    )
    last_voice_html      = state.get("last_voice_html") or ""
    voice_played_at_elapsed = state.get("voice_played_at_elapsed", -1) or -1

    elapsed      = int(time.time() - start_time)
    timeline     = plan_data.get("timeline") or {}
    total_sec    = timeline.get("total_duration_seconds") or 0
    events       = timeline.get("events") or []
    items        = timeline.get("items") or []

    put_events  = [e for e in events if e.get("action") == "下锅"]
    take_events = [e for e in events if e.get("action") in ("捞出", "捞起")]
    put_due     = [e for e in put_events  if e["time_seconds"] <= elapsed]
    take_due    = [e for e in take_events if e["time_seconds"] <= elapsed]
    cur_put     = put_due[-1]  if put_due  else None
    cur_take    = take_due[-1] if take_due else None
    next_put    = next((e for e in put_events  if e["time_seconds"] > elapsed), None)
    next_take   = next((e for e in take_events if e["time_seconds"] > elapsed), None)

    show_put  = bool(cur_put  and elapsed < cur_put["time_seconds"]  + TIMER_PROMPT_DURATION_SEC)
    show_take = bool(cur_take and elapsed < cur_take["time_seconds"] + TIMER_PROMPT_DURATION_SEC)

    new_put_sec  = cur_put["time_seconds"]  if cur_put  else (last_put_sec  or -1)
    new_take_sec = cur_take["time_seconds"] if cur_take else (last_take_sec or -1)
    last_put_sec  = last_put_sec  or -1
    last_take_sec = last_take_sec or -1

    name_put  = (_ingredient_from_msg(cur_put.get("message"))  or cur_put.get("item_name",""))  if cur_put  else ""
    name_take = (_ingredient_from_msg(cur_take.get("message")) or cur_take.get("item_name","")) if cur_take else ""

    next_put_info  = ((next_put["time_seconds"]  - elapsed,
                       _ingredient_from_msg(next_put.get("message"))  or next_put.get("item_name",""))
                      if next_put  else None)
    next_take_info = ((next_take["time_seconds"] - elapsed,
                       _ingredient_from_msg(next_take.get("message")) or next_take.get("item_name",""))
                      if next_take else None)

    display_html = _build_timer_html(
        elapsed, total_sec, show_put, show_take,
        name_put, name_take, next_put_info, next_take_info, items,
    )

    # ── 语音播报（逻辑与原版完全一致）────────────────────────
    voice_put_new  = bool(cur_put  and cur_put["time_seconds"]  > last_put_sec)
    voice_take_new = bool(cur_take and cur_take["time_seconds"] > last_take_sec)
    play_voice     = voice_put_new or voice_take_new

    voice_html_out = ""
    if play_voice:
        phrases = []
        if voice_put_new  and cur_put:  phrases.append(f"现在请下锅，{name_put}")
        if voice_take_new and cur_take: phrases.append(f"现在请捞出，{name_take}")
        if phrases:
            event_sec = (cur_put["time_seconds"]  if voice_put_new  and cur_put  else
                         cur_take["time_seconds"] if voice_take_new and cur_take else None)
            if event_sec is not None:
                with _tts_preload_lock:
                    voice_html_out = (_tts_preload_cache.pop((start_time, event_sec), None) or "").strip()
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
        if (last_voice_html and voice_played_at_elapsed >= 0
                and (elapsed - voice_played_at_elapsed) < TIMER_VOICE_KEEP_HTML_SEC):
            voice_html_out = last_voice_html
        _voice_timer_state_by_start[start_time] = {
            "last_voice_html": last_voice_html or "", "voice_played_at_elapsed": voice_played_at_elapsed
        }

    return display_html, new_put_sec, new_take_sec, voice_html_out


# ─────────────────────────────────────────────────────────────────────────────
# 优化3：食材输入 UX — 批量粘贴 + 模糊搜索自动补全
# ─────────────────────────────────────────────────────────────────────────────

def _search_ingredients_for_dropdown(query: str):
    """输入关键词模糊搜索食材库，返回最多 8 条匹配名称列表，供自动补全下拉使用。"""
    if not query or not str(query).strip():
        return []
    results = search_ingredient(str(query).strip())
    return [r.name for r in results[:8]] if results else []


def _batch_add_ingredients(batch_text: str, state: list):
    """
    批量添加食材：解析逗号/顿号/换行分隔的食材文本，批量追加到 state。
    返回 (新 state, 展示表 HTML, 状态消息, 删除行下拉选项)。
    """
    names = parse_ingredients_from_text(batch_text or "")
    if not names:
        return (state, _ingredient_table_display_html(state or []),
                "⚠️ 未解析到食材，请检查格式（用逗号、顿号或换行分隔）。",
                gr.update(choices=_ingredient_delete_choices(state or []), value=None))
    state = list(state or [])
    added = []
    for name in names:
        name = name.strip()
        if name:
            state.append([name, "", 1])
            added.append(name)
    choices = _ingredient_delete_choices(state)
    msg = f"✅ 已批量添加 {len(added)} 种食材：{'、'.join(added[:6])}{'…' if len(added) > 6 else ''}"
    return state, _ingredient_table_display_html(state), msg, gr.update(choices=choices, value=None)


# ─────────────────────────────────────────────────────────────────────────────
# 优化4：方案分享 — 复制文字 + 生成二维码
# ─────────────────────────────────────────────────────────────────────────────

def _plan_to_share_text(plan_data: dict) -> str:
    """将方案数据转换为适合分享（可微信粘贴 / QR 编码）的纯文本摘要。"""
    if not plan_data:
        return ""
    tl = plan_data.get("timeline") or {}
    items = tl.get("items") or []
    broth = tl.get("broth_type", "")
    mode  = tl.get("user_mode", "")
    total = tl.get("total_duration_display", "")
    num   = plan_data.get("num_people") or ""
    portions = plan_data.get("portions") or {}

    lines = ["🍲 涮涮AI 火锅方案"]
    meta = []
    if broth:  meta.append(f"锅底：{broth}")
    if mode:   meta.append(f"模式：{mode}")
    if num:    meta.append(f"{num}人份")
    if total:  meta.append(f"总时长：{total}")
    if meta:   lines.append(" | ".join(meta))
    lines.append("")
    lines.append("【下锅顺序】")
    for i, item in enumerate(items, 1):
        name = item.get("ingredient_name", "")
        t    = item.get("cooking_display", "")
        p    = portions.get(name, 1)
        pstr = f" x{p}" if p > 1 else ""
        tip  = item.get("technique", "")
        row  = f"{i}. {name}{pstr}  {t}"
        if tip:
            row += f"  （{tip}）"
        lines.append(row)

    warnings = plan_data.get("safety_warnings") or []
    if warnings:
        lines.append("")
        lines.append("【安全提醒】")
        for w in warnings:
            lines.append(f"· {w}")

    lines.append("")
    lines.append("by 涮涮AI")
    return "\n".join(lines)


def _copy_plan_html(plan_text: str) -> str:
    """
    返回一段 HTML + JS，执行后将 plan_text 写入剪贴板，并在页面上显示提示。
    使用 navigator.clipboard（HTTPS）并带 execCommand 兜底。
    """
    if not plan_text or not plan_text.strip():
        return "<span style='color:#e67e22;font-size:.9em'>⚠️ 暂无方案内容，请先生成方案。</span>"
    import json
    text_js = json.dumps(plan_text)   # 安全转义，避免 XSS / JS 注入
    uid = f"copy_btn_{int(time.time() * 1000) % 1000000}"
    html = f"""
<span id="{uid}_status" style="font-size:.88em;color:#27ae60"></span>
<script>
(function() {{
  var text = {text_js};
  function showOk() {{
    var el = document.getElementById('{uid}_status');
    if (el) {{ el.textContent = '✅ 已复制到剪贴板！'; setTimeout(function(){{ el.textContent=''; }}, 3500); }}
  }}
  function showFail(e) {{
    var el = document.getElementById('{uid}_status');
    if (el) {{ el.textContent = '⚠️ 复制失败，请手动选中下方文字复制。'; }}
    console.warn('clipboard error', e);
  }}
  if (navigator.clipboard && window.isSecureContext) {{
    navigator.clipboard.writeText(text).then(showOk, showFail);
  }} else {{
    try {{
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      showOk();
    }} catch(e) {{ showFail(e); }}
  }}
}})();
</script>
"""
    return html


def _generate_qr_html(plan_text: str) -> str:
    """
    用 qrcode 库将方案摘要生成二维码 PNG，以 base64 内嵌 HTML 返回。
    若 qrcode/Pillow 未安装，返回安装提示。
    二维码内容限 600 字符以保证扫描可靠性。
    """
    if not plan_text or not plan_text.strip():
        return "<span style='color:#e67e22;font-size:.9em'>⚠️ 暂无方案内容，请先生成方案。</span>"
    try:
        import qrcode as _qrcode
        from PIL import Image as _PILImage
    except ImportError:
        return ("<div style='padding:10px;border:1px solid #f0c040;border-radius:8px;"
                "background:#fffde7;font-size:.88em;color:#7d6608'>"
                "⚠️ 需要安装 qrcode[pil] 才能生成二维码：<br>"
                "<code>pip install qrcode[pil]</code></div>")
    # 截断到 600 字符，避免 QR 版本过高导致扫描困难
    content = plan_text[:600]
    try:
        qr = _qrcode.QRCode(
            version=None,
            error_correction=_qrcode.constants.ERROR_CORRECT_L,
            box_size=7,
            border=3,
        )
        qr.add_data(content)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#1a1a1a", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return (
            "<div style='text-align:center;padding:10px 0'>"
            f"<img src='data:image/png;base64,{b64}' "
            "style='max-width:200px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.12)'>"
            "<div style='font-size:.78em;color:#999;margin-top:6px'>"
            "用微信扫码即可查看方案</div>"
            "</div>"
        )
    except Exception as e:
        return f"<span style='color:#c0392b;font-size:.9em'>二维码生成失败：{e}</span>"


# ═════════════════════════════════════════════════════════════════════════════
# 前端设计 v4 — 按原型设计说明书重构的视觉组件生成器
# ═════════════════════════════════════════════════════════════════════════════

def _homepage_html() -> str:
    """首页海报 HTML - 增加固定高度容器防止塌陷"""
    return """
<div class="hp-main-container">
  <div class="hp-wrap">
    <div class="hp-poster">
      <div class="hp-poster-glow"></div>
      <div class="hp-poster-content">
        <div class="hp-tagline-top">/ 三步走 /</div>
        <div class="hp-poster-headline">涮出无∞限可能</div>
        <div class="hp-poster-brand">涮涮 AI</div>
        <div class="hp-tagline-bottom">定制你的专属菜单</div>
      </div>
      <div class="hp-steam hp-steam--1"></div>
      <div class="hp-steam hp-steam--2"></div>
      <div class="hp-steam hp-steam--3"></div>
      <div class="hp-pot-base"></div>
    </div>
  </div>
</div>
"""


def _step_header_html(step_num: str, step_title: str, extra_cls: str = "") -> str:
    """统一步骤头部 - 对齐原型图斜杠风格"""
    return (
        f'<div class="shuai-step-bar {extra_cls}">'
        f'<div class="shuai-step-wrapper">'
        f'<span class="shuai-step-num">/ {step_num} /</span>'
        f'<span class="shuai-step-title">{step_title}</span>'
        f'</div>'
        f'</div>'
    )


def _basket_drawer_html(state: list) -> str:
    """购物车抽屉内的食材列表 HTML（只读）"""
    if not state:
        return '<p class="drawer-empty">尚未添加食材，请在上方输入。</p>'
    rows = []
    for row in state:
        name = (row[0] if row else "") or ""
        if not name:
            continue
        t_val = row[1] if len(row) > 1 else None
        portion = int(row[2]) if len(row) > 2 and row[2] else 1
        try:
            t = int(float(t_val)) if t_val and str(t_val).strip() not in ("", "0", "0.0") else 0
        except Exception:
            t = 0
        t_disp = f"{t}秒" if t > 0 else "库默认"
        rows.append(
            f'<div class="drawer-item">'
            f'<span class="di-name">{name}</span>'
            f'<span class="di-meta">{t_disp} · {portion}份</span>'
            f'</div>'
        )
    return "\n".join(rows) if rows else '<p class="drawer-empty">无有效食材。</p>'


def _basket_bar_html(count: int, state: list) -> str:
    """
    底部购物车栏（仿美团风格）+ 上拉抽屉。
    点击篮子图标展开抽屉浏览已选食材；点击「下一步」触发隐藏的 Gradio 按钮。
    """
    items_list = [r[0] for r in (state or []) if r and r[0]]
    preview = "、".join(items_list[:3]) + ("…" if len(items_list) > 3 else "") if items_list else "还未添加食材"
    badge = f'<span class="bsk-badge">{count}</span>' if count > 0 else ""
    drawer_content = _basket_drawer_html(state or [])
    return f"""
<div class="shuai-basket-area">
  <div class="shuai-basket-bar">
    <div class="bsk-left" onclick="shuaiOpenBasket(event)">
      <span class="bsk-icon">🛒{badge}</span>
      <span class="bsk-preview">{preview}</span>
    </div>
    <div class="bsk-right">
      <span class="bsk-count">共 {count} 件涮品</span>
      <button class="bsk-next-btn" onclick="shuaiGrNext(event)">下一步 ›</button>
    </div>
  </div>

  <div class="shuai-overlay" id="shuai-overlay-{count}" onclick="shuaiCloseBasket(this)" style="display:none"></div>
  <div class="shuai-drawer" id="shuai-drawer-{count}">
    <div class="shuai-drawer-handle"></div>
    <div class="shuai-drawer-header">
      <span class="shuai-drawer-title">已选食材（{count}件）</span>
      <button class="shuai-drawer-close" onclick="shuaiCloseBasket2('{count}')">✕</button>
    </div>
    <div class="shuai-drawer-body">{drawer_content}</div>
    <div class="shuai-drawer-footer">
      <button class="shuai-drawer-next" onclick="shuaiCloseBasket2('{count}'); setTimeout(shuaiGrNextRaw, 120)">下一步</button>
    </div>
  </div>
</div>
<script>
(function(){{
  var cnt = '{count}';
  function openDrawer(){{
    var o=document.getElementById('shuai-overlay-'+cnt);
    var d=document.getElementById('shuai-drawer-'+cnt);
    if(o)o.style.display='block';
    if(d)d.classList.add('open');
  }}
  function closeDrawer(){{
    var o=document.getElementById('shuai-overlay-'+cnt);
    var d=document.getElementById('shuai-drawer-'+cnt);
    if(o)o.style.display='none';
    if(d)d.classList.remove('open');
  }}
  function fireClick(el){{
    el.dispatchEvent(new MouseEvent('click', {{bubbles:true, cancelable:true, view:window}}));
  }}
  function grNext(){{
    // 1. 首选：按 elem_id 定位 Gradio 按钮包裹层，再找内部 <button>
    var wrapper = document.getElementById('btn-next-hidden');
    if(wrapper){{
      var button = wrapper.querySelector('button');
      if(button){{ fireClick(button); return; }}
    }}
    // 2. 兜底：遍历全部按钮，跳过购物车区域内的按钮（避免找到自身造成无限循环）
    var allBtns = document.querySelectorAll('button');
    for(var i=0; i<allBtns.length; i++){{
      var b = allBtns[i];
      if(b.closest && b.closest('.shuai-basket-area')) continue;
      if(b.textContent.trim() === '下一步'){{ fireClick(b); return; }}
    }}
  }}
  window.shuaiOpenBasket=openDrawer;
  window.shuaiCloseBasket=function(el){{closeDrawer();}};
  window.shuaiCloseBasket2=closeDrawer;
  window.shuaiGrNext=function(e){{if(e)e.stopPropagation();grNext();}};
  window.shuaiGrNextRaw=grNext;
}})();
</script>
"""


# ─── 新增导航函数（6输出版：包含 step_home）────────────────────────────────

def _nav_to_home():
    """回到首页（step_state=-1），显示 step_home，隐藏其他。"""
    return (-1,
            gr.update(visible=True),   # step_home
            gr.update(visible=False),  # step0
            gr.update(visible=False),  # step1
            gr.update(visible=False),  # step2
            gr.update(visible=False))  # step3


def _nav_restart_v4(step):
    """重新开始 → 回到首页。"""
    return _nav_to_home()


def _nav_back_timer_v4(step, start_time):
    """从计时页返回首页，同时清理内存缓存。"""
    if start_time and start_time > 0:
        _cleanup_timer_state(start_time)
    return _nav_to_home()


def _nav_next_v4(step):
    """下一步（含 step_home 输出版）。"""
    s = step
    if s < 0:
        new = 0
    elif s < 3:
        new = s + 1
    else:
        new = s
    _vis = {
        -1: (True,  False, False, False, False),
         0: (False, True,  False, False, False),
         1: (False, False, True,  False, False),
         2: (False, False, False, True,  False),
         3: (False, False, False, False, True),
    }.get(new, (False, True, False, False, False))
    return (new,) + tuple(gr.update(visible=v) for v in _vis)


def _nav_prev_v4(step):
    """上一步（含 step_home 输出版）。"""
    s = step
    if s <= 0:
        new = -1
    else:
        new = s - 1
    _vis = {
        -1: (True,  False, False, False, False),
         0: (False, True,  False, False, False),
         1: (False, False, True,  False, False),
         2: (False, False, False, True,  False),
         3: (False, False, False, False, True),
    }.get(new, (True, False, False, False, False))
    return (new,) + tuple(gr.update(visible=v) for v in _vis)


def create_ui():
    """构建 Gradio 界面：首页 → 步骤1食材 → 步骤2偏好 → 步骤3方案 → 步骤4计时。"""
    with gr.Blocks(title="涮涮AI - 智能火锅助手") as demo:

        # ── 注入 Google Fonts ───────────────────────────────────────────────
        gr.HTML(
            '<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700;900'
            '&family=Noto+Sans+SC:wght@300;400;500&display=swap" rel="stylesheet">'
        )

        # ── States ─────────────────────────────────────────────────────────
        step_state = gr.State(-1)          # -1=首页 0=食材 1=偏好 2=方案 3=计时
        plan_data_state = gr.State(None)
        plan_text_state = gr.State("")
        start_time_state = gr.State(0)
        last_beeped_put = gr.State(-1)
        last_beeped_take = gr.State(-1)
        ingredient_table_state = gr.State([])
        # 用于打破搜索补全的循环触发：
        # 用户从下拉选中 → 写入名称框 → 触发名称框 change → 重新搜索（覆盖选中值）
        # just_selected=True 时 _on_name_change 跳过搜索，只清除 flag
        search_just_selected = gr.State(False)

        # ══════════════════════════════════════════════════════════════════
        # 首页（页面2）
        # ══════════════════════════════════════════════════════════════════
        step_home = gr.Column(visible=True, elem_id="page-home")
        with step_home:
            gr.HTML(value=_homepage_html())
            btn_enter = gr.Button("开始", elem_id="btn-enter-home", variant="primary")
            gr.HTML('<div class="hp-bounce">▼</div>')

        # ══════════════════════════════════════════════════════════════════
        # 步骤1（页面3）：输入食材
        # ══════════════════════════════════════════════════════════════════
        step0 = gr.Column(visible=False, elem_id="page-step0")
        with step0:
            gr.HTML(_step_header_html("第一步", "输入食材"))

            # ── 食材输入卡片区 ─────────────────────────────────────────
            with gr.Group(elem_id="ing-card-group"):
                gr.HTML('<div class="ing-card-title">新增食材</div>')
                with gr.Row(elem_id="ing-input-top"):
                    with gr.Column(scale=3, elem_id="ing-text-col"):
                        ingredient_name_input = gr.Textbox(
                            label="🖊 食材名称",
                            placeholder="如：毛肚、肥牛、土豆片",
                            lines=1, elem_id="ing-name-tb",
                        )
                        ingredient_search_dd = gr.Dropdown(
                            label="🔍 搜索补全（输入后下拉选择）",
                            choices=[], value=None,
                            allow_custom_value=True,
                            interactive=True,
                            elem_id="ing-search-dd",
                        )
                        ingredient_default_hint = gr.Markdown("", visible=True)
                    with gr.Column(scale=2, elem_id="ing-voice-col"):
                        voice_input = gr.Audio(
                            label="🎤 语音输入",
                            sources=["microphone", "upload"],
                            type="filepath",
                        )
                        btn_voice = gr.Button("识别语音", size="sm", elem_id="btn-voice-rec")
                        voice_status = gr.Markdown("", visible=True)

                with gr.Row(elem_id="time-portion-row"):
                    ingredient_time_input = gr.Slider(
                        label="涮煮时间(秒)",
                        minimum=0, maximum=600, value=0, step=5,
                        info="留0则使用库默认", scale=2,
                    )
                    ingredient_portion_input = gr.Slider(
                        label="份数",
                        minimum=1, maximum=99, value=1, step=1, scale=1,
                    )
                with gr.Row(elem_id="ing-confirm-row"):
                    btn_add_row = gr.Button("✔ 加入清单", variant="primary", elem_id="btn-confirm-add")
                    btn_reject_input = gr.Button("✘ 清空", variant="secondary", elem_id="btn-clear-input")

            # ── 识图输入 ───────────────────────────────────────────────
            with gr.Group(elem_id="img-rec-group"):
                gr.HTML('<div class="shuai-sec-sep">📷 识图输入</div>')
                image_input = gr.Image(
                    label="上传菜单 / 菜品图",
                    type="filepath", sources=["upload"],
                )
                image_status = gr.Markdown("", visible=True)
                btn_image = gr.Button("识别图片并填入食材", size="sm")

            # ── 批量粘贴 ───────────────────────────────────────────────
            with gr.Accordion("📋 批量粘贴食材（点击展开）", open=False, elem_id="batch-acc"):
                gr.Markdown("将食材用**逗号、顿号或换行**分隔后粘贴，一键添加。")
                batch_paste_input = gr.Textbox(
                    label="",
                    placeholder="肥牛、毛肚、鸭肠、虾滑、土豆片、金针菇、菠菜",
                    lines=3,
                )
                with gr.Row():
                    btn_batch_add = gr.Button("一键批量添加", variant="primary", size="sm")
                    btn_batch_clear = gr.Button("清空", variant="secondary", size="sm")
                batch_status = gr.Markdown("")

            # ── 商家系统 ───────────────────────────────────────────────
            merchant_status = gr.Markdown("", visible=True, elem_id="merchant-status")
            btn_merchant = gr.Button(
                "🔗 一键接入商家点餐系统",
                size="sm", variant="secondary", elem_id="btn-merchant",
            )

            # ── 已添加食材表格（含删除）────────────────────────────────
            gr.HTML('<div class="shuai-sec-sep" style="margin-top:8px">🧺 已添加的食材</div>')
            ingredient_table = gr.HTML(
                value=_ingredient_table_display_html([]),
                elem_id="ingredient-table-html",
                elem_classes=["ingredient-table-no-scroll"],
            )
            with gr.Row(elem_id="delete-row"):
                ingredient_delete_dd = gr.Dropdown(
                    label="选择要删除的行",
                    choices=[], value=None,
                    allow_custom_value=False, scale=3,
                )
                btn_del_selected = gr.Button("删除所选行", variant="secondary", scale=1)

            # ── 底部购物车栏（仿美团，含上拉抽屉）────────────────────
            basket_bar_html = gr.HTML(
                value=_basket_bar_html(0, []),
                elem_id="basket-bar-html",
            )
            # 隐藏的「下一步」Gradio 按钮，由篮子栏中的 JS 触发（通过 CSS 隐藏）
            btn_next = gr.Button("下一步", elem_id="btn-next-hidden", visible=True)

        # ══════════════════════════════════════════════════════════════════
        # 步骤2（页面4）：锅底与偏好
        # ══════════════════════════════════════════════════════════════════
        step1 = gr.Column(visible=False, elem_id="page-step1")
        with step1:
            gr.HTML(_step_header_html("第二步", "选择你的口味"))

            # ── 大卡片：锅底 ─────────────────────────────────────────
            # open=True：进入偏好页时内容立即可见，避免全折叠产生白屏
            broth_acc = gr.Accordion(
                "🍲 锅底类型", open=True, elem_classes=["pref-acc", "pref-acc--hero"],
                elem_id="broth-acc",
            )
            with broth_acc:
                broth_dd = gr.Radio(
                    choices=[t for t, _ in BROTH_CHOICES],
                    value="麻辣红汤", label="", elem_id="broth-radio",
                    elem_classes=["pref-radio"],
                )

            # ── 普通卡片：口感 / 模式 ─────────────────────────────────
            texture_acc = gr.Accordion(
                "🌶 口感偏好", open=True, elem_classes=["pref-acc"],
            )
            with texture_acc:
                texture_dd = gr.Radio(
                    choices=[t for t, _ in TEXTURE_CHOICES],
                    value="标准", label="",
                    elem_classes=["pref-radio"],
                )

            mode_acc = gr.Accordion(
                "👤 用户模式", open=True, elem_classes=["pref-acc"],
            )
            with mode_acc:
                mode_dd = gr.Radio(
                    choices=[t for t, _ in MODE_CHOICES],
                    value="普通", label="",
                    elem_classes=["pref-radio"],
                )

            # ── 下排两个半宽卡片（次要，折叠即可）───────────────────
            with gr.Row(elem_id="pref-half-row"):
                with gr.Column(elem_id="allergen-col"):
                    allergen_acc = gr.Accordion(
                        "⚠️ 过敏原", open=False, elem_classes=["pref-acc"],
                    )
                    with allergen_acc:
                        allergen_input = gr.Textbox(
                            label="", placeholder="如：虾、鱼", lines=1,
                        )
                with gr.Column(elem_id="people-col"):
                    people_acc = gr.Accordion(
                        "👥 就餐人数", open=False, elem_classes=["pref-acc"],
                    )
                    with people_acc:
                        num_people_input = gr.Number(
                            label="", value=2, minimum=1, maximum=99,
                            step=1, precision=0,
                        )

            load_pref_btn = gr.Button("📂 加载我的偏好", size="sm", elem_id="load-pref-btn")
            pref_status = gr.Markdown("", elem_id="pref_status")
            result_status = gr.Markdown("", elem_id="result_status")

            with gr.Row(elem_id="step1-nav-row"):
                btn_prev = gr.Button("← 上一步", elem_id="btn-prev-s1")
                btn_generate = gr.Button("⚡ 生成方案", variant="primary", elem_id="btn-generate")

        # ══════════════════════════════════════════════════════════════════
        # 步骤3（页面5）：方案结果
        # ══════════════════════════════════════════════════════════════════
        step2 = gr.Column(visible=False, elem_id="page-step2")
        with step2:
            gr.HTML(_step_header_html("第三步", "涮煮方案"))

            # 屏中屏滚动区
            with gr.Group(elem_id="plan-scroll-wrap"):
                output_md = gr.Markdown("方案将显示在此。", label="", elem_id="plan-output-md")

            # 分享按钮（优化4）
            with gr.Row(elem_id="share-row"):
                btn_copy_plan = gr.Button("📋 复制方案文字", size="sm", variant="secondary")
                btn_gen_qr = gr.Button("📱 生成分享二维码", size="sm", variant="secondary")
            copy_status_html = gr.HTML("", elem_id="copy-status-html")
            qr_html = gr.HTML("", elem_id="qr-display-html")

            # 大圆形「开始吃饭」按钮
            gr.HTML('<div class="eating-btn-wrap">')
            btn_start_eating = gr.Button("开始\n吃饭", variant="primary", elem_id="btn-start-eating")
            gr.HTML('</div>')

            with gr.Row(elem_id="step2-nav-row"):
                btn_restart = gr.Button("↩ 重新开始", elem_id="btn-restart")
                btn_prev2 = gr.Button("← 上一步", elem_id="btn-prev-s2")

        # ══════════════════════════════════════════════════════════════════
        # 步骤4（页面6）：吃饭计时
        # ══════════════════════════════════════════════════════════════════
        step3 = gr.Column(visible=False, elem_id="page-step3")
        with step3:
            gr.HTML(_step_header_html("", "🍲 吃饭计时", "shuai-step-bar--timer"))
            timer_reminder_md = gr.HTML(
                value="<p style='color:#bbb;text-align:center;padding:40px;font-size:.95em'>点击「开始吃饭」后计时将在此显示。</p>",
                elem_id="hotpot-timer-display",
            )
            timer_beep_html = gr.HTML("")
            timer_bottom_md = gr.Markdown("")
            btn_back_from_timer = gr.Button("结束计时，返回首页", elem_id="btn-back-timer")

        # ══════════════════════════════════════════════════════════════════
        # Event Bindings
        # ══════════════════════════════════════════════════════════════════

        # ── 首页 → 步骤1 ─────────────────────────────────────────────────
        btn_enter.click(
            fn=lambda: (0, gr.update(visible=False), gr.update(visible=True),
                        gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)),
            inputs=[],
            outputs=[step_state, step_home, step0, step1, step2, step3],
        )

        # ── 步骤1：食材输入 ───────────────────────────────────────────────
        def _on_name_change(name_val, just_sel):
            """
            输入食材名称时：更新搜索下拉 + 更新提示。
            若 just_sel=True，说明本次 change 是由「从下拉选中」触发的，
            跳过搜索（避免循环覆盖选中值），只清 flag。
            """
            try:
                if just_sel:
                    # 本次是从下拉选中触发的，不重新搜索，只清 flag
                    return gr.update(), gr.update(), False
                choices = _search_ingredients_for_dropdown(name_val)
                hint = _ingredient_lookup_hint(name_val, None)
                return gr.update(choices=choices, value=None), hint, False
            except Exception as e:
                print(f"Error in _on_name_change: {e}")
                return gr.update(choices=[], value=None), "", False

        ingredient_name_input.change(
            fn=_on_name_change,
            inputs=[ingredient_name_input, search_just_selected],
            outputs=[ingredient_search_dd, ingredient_default_hint, search_just_selected],
        )

        def _on_time_change(name_val, time_val):
            """涮煮时间变化时更新提示"""
            try:
                hint = _ingredient_lookup_hint(name_val, time_val)
                return hint
            except Exception as e:
                print(f"Error in _on_time_change: {e}")
                return ""

        ingredient_time_input.change(
            fn=_on_time_change,
            inputs=[ingredient_name_input, ingredient_time_input],
            outputs=[ingredient_default_hint],
        )

        def _on_search_select(v):
            """
            用户从下拉框点选一项时：
            1. 把选中值写入名称框
            2. 清空下拉框（避免残留选中值触发再次 change）
            3. 设 just_selected=True，让随后触发的 ingredient_name_input.change 跳过搜索
            """
            try:
                if v and str(v).strip():
                    return str(v).strip(), gr.update(choices=[], value=None), True
                return gr.update(), gr.update(choices=[], value=None), False
            except Exception as e:
                print(f"Error in _on_search_select: {e}")
                return gr.update(), gr.update(), False

        ingredient_search_dd.change(
            fn=_on_search_select,
            inputs=[ingredient_search_dd],
            outputs=[ingredient_name_input, ingredient_search_dd, search_just_selected],
        )

        def _add_v4(name, t, p, state):
            try:
                state, _, _, nt, np_, _, choices = _add_ingredient_row(name, t, p, state)
                return (state, _ingredient_table_display_html(state),
                        "", nt, np_, "",
                        gr.update(choices=choices, value=None),
                        _basket_bar_html(len(state), state))
            except Exception as e:
                import traceback
                print(f"Error in _add_v4: {e}")
                traceback.print_exc()
                return (state or [], _ingredient_table_display_html(state or []),
                        f"❌ 错误：{str(e)}", 0, 1, "",
                        gr.update(choices=[], value=None),
                        _basket_bar_html(0, []))
        btn_add_row.click(
            fn=_add_v4,
            inputs=[ingredient_name_input, ingredient_time_input,
                    ingredient_portion_input, ingredient_table_state],
            outputs=[ingredient_table_state, ingredient_table, ingredient_name_input,
                     ingredient_time_input, ingredient_portion_input,
                     ingredient_default_hint, ingredient_delete_dd, basket_bar_html],
        )

        btn_reject_input.click(
            fn=lambda: ("", 0, 1, ""),
            inputs=[],
            outputs=[ingredient_name_input, ingredient_time_input,
                     ingredient_portion_input, ingredient_default_hint],
        )

        def _del_v4(state, sel):
            try:
                new_state, _, choices = _delete_selected_ingredient_row(state, sel)
                return (new_state, _ingredient_table_display_html(new_state),
                        gr.update(choices=choices, value=None),
                        _basket_bar_html(len(new_state), new_state))
            except Exception as e:
                import traceback
                print(f"Error in _del_v4: {e}")
                traceback.print_exc()
                return (state or [], _ingredient_table_display_html(state or []),
                        gr.update(choices=[], value=None),
                        _basket_bar_html(0, []))
        btn_del_selected.click(
            fn=_del_v4,
            inputs=[ingredient_table_state, ingredient_delete_dd],
            outputs=[ingredient_table_state, ingredient_table,
                     ingredient_delete_dd, basket_bar_html],
        )

        def _batch_v4(text, state):
            try:
                new_state, html, msg, _ = _batch_add_ingredients(text, state)
                return (new_state, html, msg,
                        gr.update(choices=_ingredient_delete_choices(new_state), value=None),
                        _basket_bar_html(len(new_state), new_state))
            except Exception as e:
                import traceback
                print(f"Error in _batch_v4: {e}")
                traceback.print_exc()
                return (state or [], _ingredient_table_display_html(state or []),
                        f"❌ 批量添加失败：{str(e)}", 
                        gr.update(choices=[], value=None),
                        _basket_bar_html(0, []))
        btn_batch_add.click(
            fn=_batch_v4,
            inputs=[batch_paste_input, ingredient_table_state],
            outputs=[ingredient_table_state, ingredient_table, batch_status,
                     ingredient_delete_dd, basket_bar_html],
        )
        btn_batch_clear.click(fn=lambda: "", inputs=[], outputs=[batch_paste_input])

        def _img_v4(img, state):
            try:
                state, _, status, choices = image_to_ingredients(img, state)
                return (state, _ingredient_table_display_html(state), status,
                        gr.update(choices=choices, value=None),
                        _basket_bar_html(len(state), state))
            except Exception as e:
                import traceback
                print(f"Error in _img_v4: {e}")
                traceback.print_exc()
                return (state or [], _ingredient_table_display_html(state or []),
                        f"❌ 图片识别失败：{str(e)}", 
                        gr.update(choices=[], value=None),
                        _basket_bar_html(0, []))
        btn_image.click(
            fn=_img_v4,
            inputs=[image_input, ingredient_table_state],
            outputs=[ingredient_table_state, ingredient_table, image_status,
                     ingredient_delete_dd, basket_bar_html],
        )

        def _voice_v4(audio, state):
            try:
                state, _, status, choices = voice_to_ingredients(audio, state)
                return (state, _ingredient_table_display_html(state), status,
                        gr.update(choices=choices, value=None),
                        _basket_bar_html(len(state), state))
            except Exception as e:
                import traceback
                print(f"Error in _voice_v4: {e}")
                traceback.print_exc()
                return (state or [], _ingredient_table_display_html(state or []),
                        f"❌ 语音识别失败：{str(e)}", 
                        gr.update(choices=[], value=None),
                        _basket_bar_html(0, []))
        btn_voice.click(
            fn=_voice_v4,
            inputs=[voice_input, ingredient_table_state],
            outputs=[ingredient_table_state, ingredient_table, voice_status,
                     ingredient_delete_dd, basket_bar_html],
        )

        def _merchant_v4(state):
            try:
                state = state or []
                msg = "⚠️ 暂未适配商家点餐系统，敬请期待。您可先手动填写、或使用图片/语音识别。"
                return (state, _ingredient_table_display_html(state), msg,
                        gr.update(choices=_ingredient_delete_choices(state), value=None),
                        _basket_bar_html(len(state), state))
            except Exception as e:
                import traceback
                print(f"Error in _merchant_v4: {e}")
                traceback.print_exc()
                return (state or [], _ingredient_table_display_html(state or []),
                        f"❌ 商家系统错误：{str(e)}", 
                        gr.update(choices=[], value=None),
                        _basket_bar_html(0, []))
        btn_merchant.click(
            fn=_merchant_v4,
            inputs=[ingredient_table_state],
            outputs=[ingredient_table_state, ingredient_table, merchant_status,
                     ingredient_delete_dd, basket_bar_html],
        )

        # 购物车栏「下一步」→ 步骤2
        def _handle_next_click():
            """处理下一步点击"""
            try:
                print("Next button clicked")
                return _nav_next_v4(0)  # 从步骤0跳到步骤1
            except Exception as e:
                print(f"Error in _handle_next_click: {e}")
                import traceback
                traceback.print_exc()
                return (0, gr.update(visible=True), gr.update(visible=False),
                        gr.update(visible=False), gr.update(visible=False), gr.update(visible=False))
        
        btn_next.click(
            fn=_handle_next_click,
            inputs=[],
            outputs=[step_state, step_home, step0, step1, step2, step3],
        )

        # ── 步骤2：锅底与偏好 ─────────────────────────────────────────────
        # Accordion 折叠后在标题显示当前选中值
        broth_dd.change(
            fn=lambda v: gr.update(label=f"🍲 锅底类型　✓ {v}"),
            inputs=[broth_dd], outputs=[broth_acc],
        )
        texture_dd.change(
            fn=lambda v: gr.update(label=f"🌶 口感偏好　✓ {v}"),
            inputs=[texture_dd], outputs=[texture_acc],
        )
        mode_dd.change(
            fn=lambda v: gr.update(label=f"👤 用户模式　✓ {v}"),
            inputs=[mode_dd], outputs=[mode_acc],
        )
        allergen_input.change(
            fn=lambda v: gr.update(label=f"⚠️ 过敏原　{v.strip() or '无'}"),
            inputs=[allergen_input], outputs=[allergen_acc],
        )
        num_people_input.change(
            fn=lambda v: gr.update(label=f"👥 就餐人数　{int(v or 2)}人"),
            inputs=[num_people_input], outputs=[people_acc],
        )

        def _load_pref_v4():
            broth, texture, mode, allergen, status = load_preference_ui()
            num = 2
            return (broth, texture, mode, allergen, num, status,
                    gr.update(label=f"🍲 锅底类型　✓ {broth}"),
                    gr.update(label=f"🌶 口感偏好　✓ {texture}"),
                    gr.update(label=f"👤 用户模式　✓ {mode}"),
                    gr.update(label=f"⚠️ 过敏原　{allergen.strip() or '无'}"))
        load_pref_btn.click(
            fn=_load_pref_v4, inputs=[],
            outputs=[broth_dd, texture_dd, mode_dd, allergen_input, num_people_input,
                     pref_status, broth_acc, texture_acc, mode_acc, allergen_acc],
        )

        btn_prev.click(
            fn=_nav_prev_v4,
            inputs=[step_state],
            outputs=[step_state, step_home, step0, step1, step2, step3],
        )

        btn_generate.click(
            fn=_show_generating,
            inputs=[],
            outputs=[output_md, step_state, step0, step1, step2, step3, result_status],
        ).then(
            fn=_generate_and_go,
            inputs=[ingredient_table_state, broth_dd, texture_dd,
                    mode_dd, allergen_input, num_people_input],
            outputs=[output_md, step_state, step0, step1, step2, step3,
                     result_status, plan_data_state, plan_text_state],
        )

        # ── 步骤3：方案结果 ───────────────────────────────────────────────
        btn_copy_plan.click(
            fn=_copy_plan_html,
            inputs=[plan_text_state], outputs=[copy_status_html],
        )
        btn_gen_qr.click(
            fn=_generate_qr_html,
            inputs=[plan_text_state], outputs=[qr_html],
        )
        btn_restart.click(
            fn=_nav_restart_v4,
            inputs=[step_state],
            outputs=[step_state, step_home, step0, step1, step2, step3],
        )
        btn_prev2.click(
            fn=_nav_prev_v4,
            inputs=[step_state],
            outputs=[step_state, step_home, step0, step1, step2, step3],
        )
        btn_start_eating.click(
            fn=_start_eating,
            inputs=[plan_data_state],
            outputs=[start_time_state, step_state, step0, step1, step2, step3,
                     timer_bottom_md, last_beeped_put, last_beeped_take,
                     timer_reminder_md, timer_beep_html],
        )

        # ── 步骤4：吃饭计时 ───────────────────────────────────────────────
        btn_back_from_timer.click(
            fn=_nav_back_timer_v4,
            inputs=[step_state, start_time_state],
            outputs=[step_state, step_home, step0, step1, step2, step3],
        )
        timer = gr.Timer(value=1)
        timer.tick(
            fn=_timer_tick,
            inputs=[plan_data_state, start_time_state, last_beeped_put, last_beeped_take],
            outputs=[timer_reminder_md, last_beeped_put, last_beeped_take, timer_beep_html],
        )

    return demo


if __name__ == "__main__":
    demo = create_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        # 默认开启 Gradio 公网分享链接；如需关闭，可改为 False 或继续使用环境变量控制
        share=True,
        theme=gr.themes.Soft(primary_hue="orange"),
        css="""
/* ═══════════════════════════════════════════════════════
   涮涮AI v4 — 按原型设计说明书重构的 CSS
   设计语言：火锅红橙主色 / 温暖中国食品风格 / 手机框居中
   ═══════════════════════════════════════════════════════ */

/* ── Google Fonts 回退 ─────────────────────────────────── */
body {
  font-family: 'Noto Sans SC', 'PingFang SC', 'Hiragino Sans GB',
               'Microsoft YaHei', sans-serif !important;
  background: #bec9be !important;
}

/* ── 手机框容器：固定大小且开启内部滚动 ── */
.gradio-container {
  width: 390px !important;
  height: 844px !important;
  max-width: 390px !important;
  max-height: 844px !important;
  margin: 20px auto !important;
  border: 10px solid #333 !important; /* 模拟手机黑边 */
  border-radius: 45px !important;
  overflow: hidden !important; /* 外壳不滚动 */
  background: #f7f5f2 !important;
  display: flex !important;
  flex-direction: column !important;
  position: relative !important;
}

/* 核心修复：让 Gradio 内部的主主体区域可以纵向滚动 */
.gradio-container > .main {
  flex: 1 !important;
  overflow-y: auto !important; /* 开启内部滚动 */
  height: 100% !important;
  padding-bottom: 80px !important; /* 为底部按钮留出空间 */
}

/* 隐藏所有多余的 Gradio 默认间距和底部标识 */
.contain { padding: 0 !important; }
footer { display: none !important; }

/* ── 首页 ─────────────────────────────────────────────── */
#page-home { background: #111; }
.hp-wrap {
  display: flex; flex-direction: column; align-items: stretch;
  background: #111;
}
.hp-tagline {
  background: #1e1e1e; color: #aaa;
  text-align: center; padding: 14px 20px;
  font-size: .85em; letter-spacing: .14em;
  font-family: 'Noto Serif SC', 'STSong', serif;
}
.hp-poster {
  position: relative;
  overflow: hidden;
  /* 修复方案：直接设置固定高度，确保绝对定位的子元素有展示空间 */
  height: 380px !important;
  background: linear-gradient(170deg, #7b0000 0%, #b31a1a 22%, #d84315 44%, #f4511e 62%, #ff8f00 78%, #1a0a00 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.hp-poster-content {
  position: relative;
  z-index: 10;
  text-align: center;
  color: white;
}

.hp-tagline-top {
  font-size: 1em;
  letter-spacing: 0.3em;
  margin-bottom: 10px;
  opacity: 0.9;
}

.hp-poster-headline {
  font-family: 'Noto Serif SC', serif;
  font-size: 2.4em;
  font-weight: 900;
  text-shadow: 0 4px 15px rgba(0,0,0,0.5);
  margin-bottom: 5px;
}

.hp-poster-brand {
  font-size: 1.1em;
  letter-spacing: 0.5em;
  margin-bottom: 20px;
  opacity: 0.8;
}

.hp-tagline-bottom {
  font-size: 0.9em;
  background: rgba(0,0,0,0.3);
  padding: 5px 15px;
  border-radius: 20px;
  display: inline-block;
}
.hp-poster-glow {
  position: absolute; inset: 0;
  background: radial-gradient(ellipse 75% 55% at 50% 35%,
    rgba(255,120,40,.38), transparent 72%);
  pointer-events: none;
}
.hp-steam {
  position: absolute; bottom: 28px;
  width: 24px; height: 70px;
  background: linear-gradient(to top, rgba(255,255,255,.28), transparent);
  border-radius: 50%;
  animation: steamRise 2.6s ease-in-out infinite;
}
.hp-steam--1 { left: 37%; animation-delay: 0s; }
.hp-steam--2 { left: 50%; animation-delay: .8s; transform: scaleX(-1); }
.hp-steam--3 { left: 63%; animation-delay: 1.6s; }
@keyframes steamRise {
  0%   { opacity: 0; transform: translateY(0) scaleX(1); }
  30%  { opacity: .85; }
  100% { opacity: 0; transform: translateY(-65px) scaleX(1.5); }
}
.hp-pot-wrap {
  position: absolute; bottom: -24px; left: 50%;
  transform: translateX(-50%); width: 180px; height: 70px; z-index: 2;
}
.hp-pot-ring {
  width: 180px; height: 55px; border-radius: 50%;
  border: 5px solid rgba(255,200,50,.55);
  box-shadow: 0 0 28px rgba(255,140,40,.5);
}
.hp-pot-lava {
  position: absolute; top: 8px; left: 18px;
  width: 144px; height: 40px;
  background: radial-gradient(ellipse,
    rgba(255,70,20,.75) 0%, rgba(120,10,0,.8) 65%, transparent 100%);
  border-radius: 50%;
}
.hp-pot-bubble {
  position: absolute;
  background: rgba(255,180,50,.7);
  border-radius: 50%;
  animation: bubble 1.4s ease-in-out infinite;
}
.hp-pot-bubble.b1 { width:10px;height:10px;left:30px;top:14px;animation-delay:0s; }
.hp-pot-bubble.b2 { width: 7px;height: 7px;left:80px;top:20px;animation-delay:.5s; }
.hp-pot-bubble.b3 { width:12px;height:12px;left:120px;top:12px;animation-delay:.9s; }
@keyframes bubble {
  0%,100% { transform: translateY(0) scale(1); opacity: .7; }
  50%      { transform: translateY(-8px) scale(1.2); opacity: 1; }
}
.hp-poster-text {
  position: absolute; top: 16px; left: 0; right: 0;
  text-align: center; z-index: 3;
}
.hp-poster-headline {
  font-family: 'Noto Serif SC', 'STXingKai', serif;
  font-size: 2em; font-weight: 900;
  color: #fff;
  text-shadow: 0 2px 14px rgba(0,0,0,.6), 0 0 40px rgba(255,120,40,.5);
  letter-spacing: .06em;
}
.hp-poster-brand {
  font-size: .88em; color: rgba(255,255,255,.75);
  letter-spacing: .28em; margin-top: 4px;
}
.hp-poster-sub {
  position: relative; z-index: 3;
  background: rgba(0,0,0,.6); color: rgba(255,255,255,.85);
  text-align: center; padding: 11px;
  font-size: .88em; letter-spacing: .06em;
}
/* 首页「开始」按钮 */
#btn-enter-home button {
  height: 60px !important;
  border-radius: 30px !important;
  font-size: 1.3em !important;
  font-weight: 700 !important;
  letter-spacing: 0.2em !important;
  background: linear-gradient(135deg, #e07c24 0%, #c0392b 100%) !important;
  border: none !important;
  box-shadow: 0 10px 30px rgba(192,57,43,0.5) !important;
}

/* 隐藏通过 JS 触发的隐形“下一步”按钮外壳 */
#btn-next-hidden {
  position: fixed !important;
  top: -9999px !important; left: -9999px !important;
  width: 1px !important; height: 36px !important;
  opacity: 0 !important; pointer-events: none !important;
  z-index: -999 !important; margin: 0 !important;
}

/* ── 锅底选择：强制 2 列瓦片网格 ── */
#broth-radio .wrap {
  display: grid !important;
  grid-template-columns: 1fr 1fr !important; /* 强制两列 */
  gap: 12px !important;
  padding: 10px !important;
}

#broth-radio label {
  height: 90px !important; /* 变成方块 */
  background: white !important;
  border: 2px solid #eee !important;
  border-radius: 15px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  transition: all 0.2s !important;
  box-shadow: 0 2px 6px rgba(0,0,0,0.05) !important;
}

/* 选中后的视觉反馈 */
#broth-radio label:has(input:checked) {
  border-color: #e65c00 !important;
  background: #fff8f0 !important;
}

/* 隐藏原生的单选小圆点 */
#broth-radio input[type="radio"] {
  display: none !important;
}
.hp-bounce {
  text-align: center; color: rgba(200,200,200,.55);
  font-size: .88em; margin: 10px 0 4px;
  animation: bounce 1.5s ease-in-out infinite;
}
@keyframes bounce {
  0%,100% { transform: translateY(0); }
  50%      { transform: translateY(6px); }
}

/* ── 步骤头部横条 ──────────────────────────────────────── */
.shuai-step-bar {
  background: transparent !important;
  color: #333 !important;
  text-align: center;
  padding: 20px 0 !important;
  display: block !important;
}
.shuai-step-wrapper {
  display: inline-block;
}
.shuai-step-num {
  display: block;
  font-family: 'Noto Serif SC', serif;
  font-size: 1.2em;
  color: #e65c00;
  margin-bottom: 5px;
  letter-spacing: .15em;
}
.shuai-step-title {
  font-size: 1.5em;
  font-weight: 700;
  color: #1a1a1a;
}
.shuai-step-bar--timer {
  background: transparent !important;
}

/* ── 步骤1：食材输入 ───────────────────────────────────── */
#page-step0 { background: #f3f0ec; }
#ing-card-group {
  background: white;
  margin: 12px;
  border-radius: 20px !important;
  padding: 20px !important;
  box-shadow: 0 2px 14px rgba(0,0,0,.07);
  border: 2px solid #eee !important;
}
.ing-card-title {
  font-size: .78em; color: #e07c24; letter-spacing: .1em;
  font-weight: 600; margin-bottom: 10px; text-transform: uppercase;
}
#img-rec-group {
  background: white; margin: 0 12px 10px; border-radius: 14px;
  padding: 0 14px 14px; box-shadow: 0 2px 14px rgba(0,0,0,.07);
}
.shuai-sec-sep {
  font-size: .78em; color: #999; letter-spacing: .1em;
  padding: 9px 12px 5px;
}
#batch-acc { margin: 0 12px 8px; border-radius: 12px; overflow: hidden; }
#merchant-status { margin: 0 12px; }
#page-step0 #btn-merchant { margin: 4px 12px 8px; width: calc(100% - 24px); }
#page-step0 #ingredient-table-html { margin: 0 12px; }
#delete-row { margin: 4px 12px 8px; }
#ing-confirm-row { margin-top: 10px; gap: 10px; }
#ing-confirm-row #btn-confirm-add { flex: 2 !important; }
#ing-confirm-row #btn-clear-input { flex: 1 !important; }
#time-portion-row { margin-top: 6px; }

/* ── 购物车栏 ──────────────────────────────────────────── */
.shuai-basket-area { position: sticky; bottom: 0; z-index: 50; }
.shuai-basket-bar {
  background: #2a2424; color: white;
  display: flex; align-items: center; justify-content: space-between;
  padding: 11px 16px; cursor: default;
}
.bsk-left { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; cursor: pointer; }
.bsk-icon { font-size: 1.25em; position: relative; flex-shrink: 0; }
.bsk-badge {
  position: absolute; top: -5px; right: -7px;
  background: #e07c24; color: white; border-radius: 50%;
  font-size: .6em; width: 15px; height: 15px;
  display: flex; align-items: center; justify-content: center; font-weight: 700;
}
.bsk-preview {
  font-size: .8em; color: rgba(255,255,255,.65);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.bsk-right { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
.bsk-count {
  font-size: 1em !important;
  font-weight: 600 !important;
  color: #fff !important;
  background: rgba(255,255,255,0.1);
  padding: 4px 12px;
  border-radius: 20px;
}
.bsk-next-btn {
  background: linear-gradient(135deg, #e07c24, #c0392b);
  color: white; border: none; border-radius: 6px;
  padding: 7px 14px; font-size: .88em; cursor: pointer;
  font-family: 'Noto Sans SC', sans-serif; font-weight: 500;
  transition: opacity .15s;
}
.bsk-next-btn:hover { opacity: .88; }
/* 遮罩 & 抽屉 */
.shuai-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.48); z-index: 200;
}
.shuai-drawer {
  position: fixed; bottom: 0; left: 50%;
  transform: translateX(-50%) translateY(100%);
  width: min(430px, 100vw); max-height: 68vh;
  background: white; border-radius: 18px 18px 0 0;
  z-index: 201; display: flex; flex-direction: column;
  transition: transform .32s cubic-bezier(.32,0,.15,1);
  box-shadow: 0 -6px 36px rgba(0,0,0,.18);
}
.shuai-drawer.open { transform: translateX(-50%) translateY(0); }
.shuai-drawer-handle {
  width: 38px; height: 4px; background: #ddd;
  border-radius: 2px; margin: 10px auto 6px;
}
.shuai-drawer-header {
  padding: 8px 20px 14px;
  border-bottom: 1px solid #f0ece8;
  display: flex; justify-content: space-between; align-items: center;
}
.shuai-drawer-title { font-weight: 600; font-size: .97em; }
.shuai-drawer-close {
  background: none; border: none; font-size: 1.05em;
  cursor: pointer; color: #aaa; padding: 4px 8px;
}
.shuai-drawer-body { overflow-y: auto; flex: 1; padding: 10px 20px; }
.drawer-item {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 0; border-bottom: 1px solid #f3efe9;
}
.di-name { font-weight: 500; font-size: .93em; }
.di-meta { font-size: .8em; color: #999; }
.drawer-empty { color: #bbb; font-size: .88em; text-align: center; padding: 24px 0; }
.shuai-drawer-footer {
  padding: 12px 20px; border-top: 1px solid #f0ece8;
  display: flex; justify-content: flex-end;
}
.shuai-drawer-next {
  background: linear-gradient(135deg, #e07c24, #c0392b);
  color: white; border: none; border-radius: 24px;
  padding: 10px 28px; font-size: .93em; cursor: pointer;
  font-family: 'Noto Sans SC', sans-serif; font-weight: 500;
}
/* 隐藏 Gradio 生成的「下一步」btn_next 外壳 */
#btn-next-hidden {
  position: fixed !important;
  top: -9999px !important; left: -9999px !important;
  width: 1px !important; height: 36px !important;
  opacity: 0 !important; pointer-events: none !important;
  z-index: -999 !important; overflow: hidden !important; }

/* ── 食材表格 ──────────────────────────────────────────── */
.ingredient-table-wrap .ingredient-display-table { width: 100%; border-collapse: collapse; }
.ingredient-table-wrap .ingredient-display-table th,
.ingredient-table-wrap .ingredient-display-table td {
  border: 1px solid #ede8e2; padding: .38em .55em; text-align: left; font-size: .88em; }
.ingredient-table-wrap .ingredient-display-table th { background: #f7f3ee; font-weight: 600; }
.ingredient-table-empty { color: #bbb; font-size: .88em; margin: .4em 0; }
#ingredient-table-html { overflow: visible !important; max-height: none !important; }

/* ── 步骤2：偏好选择卡片 ───────────────────────────────── */
#page-step1 { background: #f3f0ec; min-height: 60vh; }
.pref-acc {
  margin: 8px 12px !important;
  border-radius: 12px !important;
  overflow: hidden !important;
  box-shadow: 0 2px 10px rgba(0,0,0,.07) !important;
  border: 1px solid #ede8e2 !important;
  background: white !important;
}
.pref-acc--hero { border-color: #f5c89a !important; }
.pref-acc > div:first-child {
  background: white !important;
  font-family: 'Noto Sans SC', sans-serif !important;
  font-size: .97em !important; color: #2a2a2a !important;
  padding: 14px 18px !important;
  transition: background .15s !important;
}
.pref-acc > div:first-child:hover { background: #fef9f4 !important; }
.pref-acc--hero > div:first-child {
  font-size: 1.05em !important; font-weight: 600 !important;
  background: linear-gradient(135deg, #fff 70%, #fff5ee 100%) !important;
  border-bottom: 2px solid #f5c89a !important;
}
/* Radio 胶囊按钮 */
.pref-radio .wrap { display: flex !important; flex-wrap: wrap !important;
  padding: 10px 12px 14px !important; gap: 6px !important; }
.pref-radio label {
  border: 1.5px solid #e8e0d8 !important;
  border-radius: 20px !important;
  padding: 6px 16px !important;
  cursor: pointer !important;
  font-size: .88em !important;
  background: #faf8f5 !important;
  color: #3a3535 !important;
  display: inline-flex !important; align-items: center !important;
  transition: all .15s !important;
  user-select: none !important;
}
.pref-radio label:hover { border-color: #e07c24 !important; background: #fff8f0 !important; }
.pref-radio label:has(input:checked) {
  background: linear-gradient(135deg, #e07c24, #c0392b) !important;
  border-color: transparent !important;
  color: white !important; font-weight: 600 !important;
}
.pref-radio input[type=radio] { display: none !important; }
#pref-half-row { margin: 0 4px; gap: 0; }
#allergen-col .pref-acc, #people-col .pref-acc { margin: 8px 8px !important; }
#load-pref-btn { margin: 4px 12px 0; width: calc(100% - 24px); }
#pref_status, #result_status { margin: 2px 12px; }
#step1-nav-row { margin: 8px 12px 16px; gap: 8px; }

/* ── 步骤3：方案结果 ────────────────────────────────────── */
#page-step2 { background: #f3f0ec; }
#plan-scroll-wrap {
  background: white; margin: 12px; border-radius: 14px;
  padding: 16px 18px;
  box-shadow: 0 2px 14px rgba(0,0,0,.07);
  max-height: 44vh; overflow-y: auto;
  scrollbar-width: thin; scrollbar-color: #e0d8d0 #f5f0ea;
}
#plan-scroll-wrap::-webkit-scrollbar { width: 4px; }
#plan-scroll-wrap::-webkit-scrollbar-track { background: #f5f0ea; }
#plan-scroll-wrap::-webkit-scrollbar-thumb { background: #d8cfc7; border-radius: 2px; }
/* 圆形「开始吃饭」按钮 */
.eating-btn-wrap {
  display: flex; justify-content: center; padding: 18px 0 10px;
}
#btn-start-eating { display: none; } /* will be shown via next rule on the button */
#btn-start-eating button,
#page-step2 #btn-start-eating button {
  width: 112px !important; height: 112px !important;
  border-radius: 50% !important;
  font-family: 'Noto Serif SC', serif !important;
  font-size: 1.1em !important; font-weight: 700 !important;
  line-height: 1.45 !important; white-space: pre-line !important;
  background: linear-gradient(145deg, #e07c24 0%, #c0392b 100%) !important;
  color: white !important; border: none !important;
  box-shadow: 0 4px 22px rgba(192,57,43,.4),
              0 0 0 7px rgba(224,124,36,.13) !important;
  transition: transform .2s, box-shadow .2s !important;
}
#btn-start-eating button:hover {
  transform: scale(1.06) !important;
  box-shadow: 0 8px 32px rgba(192,57,43,.52),
              0 0 0 9px rgba(224,124,36,.18) !important;
}
#share-row { margin: 4px 12px 0; gap: 8px; }
#copy-status-html, #qr-display-html { margin: 2px 12px; min-height: 0; }
#step2-nav-row { margin: 8px 12px 16px; gap: 8px; }

/* ── 步骤4：计时 ────────────────────────────────────────── */
#hotpot-timer-display {
  margin: 10px;
  font-family: 'Noto Sans SC', sans-serif;
}

/* ── Gradio 通用覆盖 ────────────────────────────────────── */
.block { border: none !important; box-shadow: none !important; }
.gr-form { background: transparent !important; border: none !important; }
.gradio-container .block.padded { padding: 6px 0 !important; }
""",
    )