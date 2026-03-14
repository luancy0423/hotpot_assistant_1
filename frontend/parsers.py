# -*- coding: utf-8 -*-
"""
<<<<<<< Updated upstream
前端输入解析层
负责将用户在 Gradio 各控件中输入的原始数据（文本框、表格、下拉框等）
解析为后端 API 可直接消费的 Python 数据结构。
不依赖 Gradio，不依赖 api.py，可单独测试。
"""

import re
from typing import List, Tuple, Dict, Optional


def parse_ingredients_from_text(text: str) -> List[str]:
    """将逗号/顿号/换行分隔的食材文本解析为名称列表。"""
=======
涮涮AI - 前端输入解析
所有从表单/表格/文本框解析为结构化数据的函数。
"""

import re
from typing import List, Tuple, Dict, Any


def parse_ingredients_from_text(text: str) -> List[str]:
    """从文本框解析食材列表，供生成方案使用。支持中文顿号、逗号、空格、换行分隔。"""
    if not text or not text.strip():
        return []
    raw = text.replace("，", ",").replace("、", ",").replace("\n", ",")
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return parts


def parse_allergens(text: str) -> List[str]:
    """从「过敏原」文本框解析为列表。"""
>>>>>>> Stashed changes
    if not text or not text.strip():
        return []
    raw = text.replace("，", ",").replace("、", ",").replace("\n", ",")
    return [p.strip() for p in raw.split(",") if p.strip()]


<<<<<<< Updated upstream
def parse_allergens(text: str) -> List[str]:
    """将过敏原文本框内容解析为列表。"""
    return parse_ingredients_from_text(text)


def parse_custom_ingredients(text: str) -> Tuple[List[Dict], str]:
    """
    解析「特色/自定义食材」文本框。
    每行一条：名称 + 时间（支持 "90"、"2分钟"、"1分30秒" 等格式，缺省 120 秒）。
    示例输入：
        田鸡 90
        蛇段 2分钟
        牛蛙, 120
    返回 ([{"name": "田鸡", "cooking_seconds": 90}, ...], "")
=======
def parse_custom_ingredients(text: str) -> Tuple[List[Dict[str, Any]], str]:
    """
    解析「特色/自定义食材」文本框。
    每行一条：名称 + 时间。时间可为秒数（90）、"1分钟"、"2分30秒"等；缺省时间按 120 秒。
    返回 (列表, 提示信息)：([{"name": "田鸡", "cooking_seconds": 90}, ...], "")
>>>>>>> Stashed changes
    """
    if not text or not text.strip():
        return [], ""
    out = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = re.split(r"[\s,，]+", line, maxsplit=1)
        name = (parts[0] or "").strip()
        if not name:
            continue
<<<<<<< Updated upstream
        seconds = 120  # 默认
=======
        seconds = 120
>>>>>>> Stashed changes
        if len(parts) > 1 and parts[1].strip():
            raw_time = parts[1].strip()
            if raw_time.isdigit():
                seconds = int(raw_time)
            else:
                m = re.search(r"(\d+)\s*分(?:\s*(\d+)\s*秒)?", raw_time)
                if m:
<<<<<<< Updated upstream
                    seconds = int(m.group(1)) * 60 + (int(m.group(2)) if m.group(2) else 0)
=======
                    minutes = int(m.group(1))
                    sec = int(m.group(2)) if m.group(2) else 0
                    seconds = minutes * 60 + sec
>>>>>>> Stashed changes
                else:
                    sec_m = re.search(r"(\d+)\s*秒", raw_time)
                    if sec_m:
                        seconds = int(sec_m.group(1))
        out.append({"name": name, "cooking_seconds": min(999 * 60, max(10, seconds))})
    return out, ""


<<<<<<< Updated upstream
def parse_ingredient_table(table) -> Tuple[List[str], List[Dict], Dict[str, int]]:
    """
    从食材表格（state = list of [name, time_sec, portion]）解析出：
      - names            — 库内食材名列表（涮煮时间留空或为 0）
      - custom_ingredients — 自定义食材列表（涮煮时间已填写且 > 0）
      - portions         — {食材名: 份数}
=======
def parse_ingredient_table(table: Any) -> Tuple[List[str], List[Dict[str, Any]], Dict[str, int]]:
    """
    从食材表格解析：常见食材名列表、特色食材列表、份数字典。
    表格每行：[食材名称, 涮煮时间(秒), 份数]。
    返回 (names, custom_ingredients, portions)。
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream

    if rows and len(rows[0]) >= 3 and rows[0][0] in ("食材名称", "名称"):
        rows = rows[1:]

    names: List[str] = []
    custom_ingredients: List[Dict] = []
    portions: Dict[str, int] = {}

=======
    if rows and len(rows[0]) >= 3 and rows[0][0] in ("食材名称", "名称"):
        rows = rows[1:]
    names = []
    custom_ingredients = []
    portions = {}
>>>>>>> Stashed changes
    for row in rows:
        if not row or len(row) < 1:
            continue
        name = (row[0] if row[0] is not None else "").strip() if isinstance(row[0], str) else str(row[0] or "").strip()
        if not name:
            continue
<<<<<<< Updated upstream
        time_val   = row[1] if len(row) > 1 else None
        portion_val = row[2] if len(row) > 2 else None
        try:
            sec = None
            if time_val not in (None, ""):
                sec = int(time_val) if isinstance(time_val, (int, float)) else int(str(time_val).strip())
            if sec and sec > 0:
=======
        time_val = row[1] if len(row) > 1 else None
        portion_val = row[2] if len(row) > 2 else None
        try:
            sec = None
            if time_val is not None and time_val != "":
                sec = int(time_val) if isinstance(time_val, (int, float)) else int(str(time_val).strip())
            if sec is not None and sec > 0:
>>>>>>> Stashed changes
                custom_ingredients.append({"name": name, "cooking_seconds": min(999 * 60, max(10, sec))})
            else:
                names.append(name)
        except (ValueError, TypeError):
            names.append(name)
        try:
<<<<<<< Updated upstream
            p = max(1, min(99, int(portion_val))) if portion_val not in (None, "") else 1
        except (ValueError, TypeError):
            p = 1
        portions[name] = p
=======
            p = max(1, min(99, int(portion_val))) if portion_val is not None and portion_val != "" else 1
            portions[name] = p
        except (ValueError, TypeError):
            portions[name] = 1
>>>>>>> Stashed changes
    return names, custom_ingredients, portions


def parse_portions(text: str) -> Dict[str, int]:
<<<<<<< Updated upstream
    """将「各菜品份数」文本框解析为 {食材名: 份数}，格式：每行「名称 数字」。"""
    if not text or not text.strip():
        return {}
    out: Dict[str, int] = {}
=======
    """解析「各菜品份数」文本框，返回 { 食材名: 份数 }，未出现的默认 1。"""
    if not text or not text.strip():
        return {}
    out = {}
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
            n = max(1, min(99, int(parts[1].strip()))) if len(parts) > 1 else 1
=======
            n = int(parts[1].strip()) if len(parts) > 1 else 1
            n = max(1, min(99, n))
>>>>>>> Stashed changes
        except (ValueError, IndexError):
            n = 1
        out[name] = n
    return out
<<<<<<< Updated upstream


# ── 食材库辅助 ───────────────────────────────────────────────────

def get_default_seconds(name: str) -> Optional[int]:
    """根据食材名称查库，返回默认涮煮秒数；未匹配返回 None。"""
    if not name or not str(name).strip():
        return None
    from data.ingredients_db import search_ingredient
    results = search_ingredient(str(name).strip())
    return results[0].cooking_rule.base_seconds if results else None


def ingredient_lookup_hint(name: str, time_val=None) -> str:
    """输入食材名称时，若用户未填写时间则提示库内默认时长。"""
    try:
        if time_val not in (None, "") and int(float(time_val)) > 0:
            return ""
    except (TypeError, ValueError):
        pass
    sec = get_default_seconds(name)
    if sec is None:
        return ""
    return f"库内默认：**{sec} 秒**（可留空使用，填写则按您的时间）"


def search_ingredients_for_dropdown(query: str) -> List[str]:
    """模糊搜索食材库，返回最多 8 条匹配名称，供自动补全下拉使用。"""
    if not query or not str(query).strip():
        return []
    from data.ingredients_db import search_ingredient
    results = search_ingredient(str(query).strip())
    return [r.name for r in results[:8]] if results else []


def batch_add_ingredients(batch_text: str, state: list):
    """
    批量添加食材：解析逗号/顿号/换行分隔的食材文本，追加到 state。
    返回 (新 state, 展示表 HTML, 状态消息, gr.update(choices=...))。
    """
    import gradio as gr
    from frontend.components import ingredient_table_html, ingredient_delete_choices

    names = parse_ingredients_from_text(batch_text or "")
    if not names:
        return (
            state,
            ingredient_table_html(state or []),
            "⚠️ 未解析到食材，请检查格式（用逗号、顿号或换行分隔）。",
            gr.update(choices=ingredient_delete_choices(state or []), value=None),
        )
    state = list(state or [])
    added = []
    for name in names:
        name = name.strip()
        if name:
            state.append([name, "", 1])
            added.append(name)
    choices = ingredient_delete_choices(state)
    msg = f"✅ 已批量添加 {len(added)} 种食材：{'、'.join(added[:6])}{'…' if len(added) > 6 else ''}"
    return state, ingredient_table_html(state), msg, gr.update(choices=choices, value=None)
=======
>>>>>>> Stashed changes
