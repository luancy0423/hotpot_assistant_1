# -*- coding: utf-8 -*-
"""
<<<<<<< Updated upstream
前端 HTML 组件层
所有生成 HTML 字符串的函数集中于此。
不依赖 Gradio，不依赖 api.py，可独立单测。
"""

import html as _html
import base64
import io
import time
from typing import List, Optional


# ── 首页 ────────────────────────────────────────────────────────
=======
涮涮AI - 前端 HTML 组件生成
首页海报、步骤头、购物车栏/抽屉、食材表格、开锅检测、方案分享/复制/二维码、计时闪烁等。
"""

import html as _html
import time
import base64
import io
import json
from typing import List, Any, Optional

from data.ingredients_db import search_ingredient


def _get_default_seconds(name: str) -> Optional[int]:
    """根据食材名称查库，返回默认涮煮秒数；未匹配返回 None。"""
    if not name or not str(name).strip():
        return None
    results = search_ingredient(str(name).strip())
    if not results:
        return None
    return results[0].cooking_rule.base_seconds


def get_default_seconds(name: str) -> Optional[int]:
    """根据食材名称查库，返回默认涮煮秒数；未匹配返回 None。供 handlers 等使用。"""
    return _get_default_seconds(name)


def ingredient_table_display_rows(state: list) -> list:
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
            portion = max(1, min(99, int(portion))) if portion not in (None, "") else 1
        except (TypeError, ValueError):
            portion = 1
        if time_user is not None and time_user != "":
            try:
                t = int(float(time_user))
                time_display = str(t) if t > 0 else ""
            except (TypeError, ValueError):
                time_display = ""
        else:
            time_display = ""
        if not time_display:
            default_sec = _get_default_seconds(name)
            time_display = f"{default_sec}（库默认）" if default_sec is not None else ""
        out.append([name, time_display, portion])
    return out


def ingredient_table_display_html(state: list) -> str:
    """将 state 转为只展示已填写的食材表格 HTML。"""
    rows = ingredient_table_display_rows(state)
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
        name = _html.escape(str(row[0] if len(row) > 0 else ""))
        time_display = _html.escape(str(row[1] if len(row) > 1 else ""))
        portion = _html.escape(str(row[2] if len(row) > 2 else "1"))
        buf.append(f"<tr><td>{name}</td><td>{time_display}</td><td>{portion}</td></tr>")
    buf.append("</tbody></table></div>")
    return "".join(buf)


def ingredient_delete_choices(state: list) -> list:
    """根据当前 state 生成「选择要删除的行」下拉选项。"""
    if not state:
        return []
    return [
        f"第{i+1}行：{(row[0] or '').strip() if isinstance(row[0], str) else str(row[0] or '')}"
        for i, row in enumerate(state) if row and (row[0] or "").strip()
    ]

>>>>>>> Stashed changes

def homepage_html() -> str:
    """首页海报 HTML。"""
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


<<<<<<< Updated upstream
# ── 步骤头部 ─────────────────────────────────────────────────────

def step_header_html(step_num: str, step_title: str, extra_cls: str = "") -> str:
    """统一步骤头部横条（斜杠风格）。"""
=======
def step_header_html(step_num: str, step_title: str, extra_cls: str = "") -> str:
    """统一步骤头部。"""
>>>>>>> Stashed changes
    return (
        f'<div class="shuai-step-bar {extra_cls}">'
        f'<div class="shuai-step-wrapper">'
        f'<span class="shuai-step-num">/ {step_num} /</span>'
        f'<span class="shuai-step-title">{step_title}</span>'
<<<<<<< Updated upstream
        f'</div>'
        f'</div>'
    )


# ── 食材表格 ─────────────────────────────────────────────────────

def ingredient_table_rows(state: list) -> list:
    """
    将 state（list of [name, time_user, portion]）转为展示用行列表。
    time 列：用户填了显示数字；未填且库匹配显示「N（库默认）」；否则空白。
    """
    from frontend.parsers import get_default_seconds
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
        portion   = row[2] if len(row) > 2 else 1
        try:
            portion = max(1, min(99, int(portion))) if portion not in (None, "") else 1
        except (TypeError, ValueError):
            portion = 1
        time_display = ""
        if time_user not in (None, ""):
            try:
                t = int(float(time_user))
                if t > 0:
                    time_display = str(t)
            except (TypeError, ValueError):
                pass
        if not time_display:
            default_sec = get_default_seconds(name)
            if default_sec is not None:
                time_display = f"{default_sec}（库默认）"
        out.append([name, time_display, portion])
    return out


def ingredient_table_html(state: list) -> str:
    """将 state 渲染为只读 HTML 表格（固定表头，无滚动条）。"""
    rows = ingredient_table_rows(state)
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
        buf.append(
            f"<tr><td>{_html.escape(str(row[0]))}</td>"
            f"<td>{_html.escape(str(row[1]))}</td>"
            f"<td>{_html.escape(str(row[2]))}</td></tr>"
        )
    buf.append("</tbody></table></div>")
    return "".join(buf)


def ingredient_delete_choices(state: list) -> list:
    """生成「选择要删除的行」下拉选项列表。"""
    if not state:
        return []
    return [
        f"第{i+1}行：{(row[0] or '').strip() if isinstance(row[0], str) else str(row[0] or '')}"
        for i, row in enumerate(state)
        if row and (row[0] or "").strip()
    ]


def add_ingredient_row(name, time_val, portion, state):
    """将当前表单一行加入 state，返回 (state, rows, name, time, portion, hint, choices)。"""
    name = (name or "").strip() if isinstance(name, str) else str(name or "").strip()
    state = list(state or [])
    if not name:
        return state, ingredient_table_rows(state), "", 0, 1, "", ingredient_delete_choices(state)
    try:
        p = max(1, min(99, int(portion))) if portion not in (None, "") else 1
    except (TypeError, ValueError):
        p = 1
    time_stored = ""
    if time_val not in (None, ""):
        try:
            t = int(float(time_val))
            if t > 0:
                time_stored = t
        except (TypeError, ValueError):
            pass
    state.append([name, time_stored, p])
    return state, ingredient_table_rows(state), "", 0, 1, "", ingredient_delete_choices(state)


def delete_selected_ingredient_row(state: list, selected_label: str):
    """删除选中行，返回 (state, rows, choices)。"""
    state = list(state or [])
    if not state or not selected_label or not str(selected_label).strip():
        return state, ingredient_table_rows(state), ingredient_delete_choices(state)
    choices_before = ingredient_delete_choices(state)
    try:
        idx = choices_before.index(selected_label)
    except ValueError:
        return state, ingredient_table_rows(state), ingredient_delete_choices(state)
    state.pop(idx)
    return state, ingredient_table_rows(state), ingredient_delete_choices(state)


def table_ensure_rows(table, min_rows: int = 1) -> list:
    """确保表格为 list of lists，且至少 min_rows 行（每行 3 列）。"""
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


# ── 购物车栏 ─────────────────────────────────────────────────────

def basket_drawer_html(state: list) -> str:
    """购物车抽屉内的食材列表 HTML（只读）。"""
=======
        f'</div></div>'
    )


def basket_drawer_html(state: list) -> str:
    """购物车抽屉内的食材列表 HTML。"""
>>>>>>> Stashed changes
    if not state:
        return '<p class="drawer-empty">尚未添加食材，请在上方输入。</p>'
    rows = []
    for row in state:
        name = (row[0] if row else "") or ""
        if not name:
            continue
<<<<<<< Updated upstream
        t_val   = row[1] if len(row) > 1 else None
=======
        t_val = row[1] if len(row) > 1 else None
>>>>>>> Stashed changes
        portion = int(row[2]) if len(row) > 2 and row[2] else 1
        try:
            t = int(float(t_val)) if t_val and str(t_val).strip() not in ("", "0", "0.0") else 0
        except Exception:
            t = 0
        t_disp = f"{t}秒" if t > 0 else "库默认"
        rows.append(
            f'<div class="drawer-item">'
            f'<span class="di-name">{name}</span>'
<<<<<<< Updated upstream
            f'<span class="di-meta">{t_disp} · {portion}份</span>'
            f'</div>'
=======
            f'<span class="di-meta">{t_disp} · {portion}份</span></div>'
>>>>>>> Stashed changes
        )
    return "\n".join(rows) if rows else '<p class="drawer-empty">无有效食材。</p>'


def basket_bar_html(count: int, state: list) -> str:
    """
<<<<<<< Updated upstream
    底部购物车栏 HTML（含上拉抽屉和 JS）。
    右侧「下一步」已改为 Gradio 真实按钮（btn-next-in-bar），此处只渲染左侧篮子区。
    """
    items_list = [r[0] for r in (state or []) if r and r[0]]
    preview = "、".join(items_list[:3]) + ("…" if len(items_list) > 3 else "") if items_list else "还未添加食材"
    badge   = f'<span class="bsk-badge">{count}</span>' if count > 0 else ""
=======
    底部购物车栏（仿美团风格）+ 上拉抽屉。
    抽屉内「下一步」仅关闭抽屉，跳转请点击底部栏的 Gradio「下一步」按钮。
    """
    items_list = [r[0] for r in (state or []) if r and r[0]]
    preview = "、".join(items_list[:3]) + ("…" if len(items_list) > 3 else "") if items_list else "还未添加食材"
    badge = f'<span class="bsk-badge">{count}</span>' if count > 0 else ""
>>>>>>> Stashed changes
    drawer_content = basket_drawer_html(state or [])
    return f"""
<div class="shuai-basket-area">
  <div class="shuai-basket-bar">
    <div class="bsk-left" onclick="shuaiOpenBasket(event)">
      <span class="bsk-icon">🛒{badge}</span>
      <span class="bsk-preview">{preview}</span>
    </div>
    <div class="bsk-right">
      <span class="bsk-count">共 {count} 件涮品</span>
    </div>
  </div>
<<<<<<< Updated upstream

=======
>>>>>>> Stashed changes
  <div class="shuai-overlay" id="shuai-overlay-{count}" onclick="shuaiCloseBasket(this)" style="display:none"></div>
  <div class="shuai-drawer" id="shuai-drawer-{count}">
    <div class="shuai-drawer-handle"></div>
    <div class="shuai-drawer-header">
      <span class="shuai-drawer-title">已选食材（{count}件）</span>
      <button class="shuai-drawer-close" onclick="shuaiCloseBasket2('{count}')">✕</button>
    </div>
    <div class="shuai-drawer-body">{drawer_content}</div>
    <div class="shuai-drawer-footer">
<<<<<<< Updated upstream
      <button class="shuai-drawer-next" onclick="shuaiCloseBasket2('{count}'); setTimeout(shuaiGrNextRaw, 120)">下一步</button>
=======
      <button class="shuai-drawer-next" onclick="shuaiCloseBasket2('{count}')">下一步</button>
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
  function fireClick(el){{
    el.dispatchEvent(new MouseEvent('click', {{bubbles:true, cancelable:true, view:window}}));
  }}
  function grNext(){{
    var wrapper = document.getElementById('btn-next-in-bar') || document.querySelector('[id^="btn-next-in-bar"]');
    if(wrapper){{
      var button = wrapper.querySelector('button');
      if(button){{ fireClick(button); return; }}
      fireClick(wrapper); return;
    }}
    var allBtns = document.querySelectorAll('button');
    for(var i=0; i<allBtns.length; i++){{
      var b = allBtns[i];
      if(b.closest && b.closest('.shuai-basket-area')) continue;
      if(b.textContent.trim().indexOf('下一步')>=0){{ fireClick(b); return; }}
    }}
  }}
  window.shuaiOpenBasket=openDrawer;
  window.shuaiCloseBasket=function(el){{closeDrawer();}};
  window.shuaiCloseBasket2=closeDrawer;
  window.shuaiGrNext=function(e){{if(e)e.stopPropagation();grNext();}};
  window.shuaiGrNextRaw=grNext;
=======
  window.shuaiOpenBasket=openDrawer;
  window.shuaiCloseBasket=function(el){{closeDrawer();}};
  window.shuaiCloseBasket2=closeDrawer;
>>>>>>> Stashed changes
}})();
</script>
"""


<<<<<<< Updated upstream
# ── 开锅检测结果卡片 ──────────────────────────────────────────────

def boiling_result_html(icon: str, stage: str, description: str, advice: str) -> str:
    """渲染开锅检测结果卡片，颜色随沸腾状态变化。"""
    if not stage:
        return ""
    color_map = {
        "沸腾":   ("#c0392b", "#fff5f5", "#ffd5d5"),
        "微沸":   ("#e07c24", "#fff8f0", "#ffe5c0"),
        "未沸":   ("#2980b9", "#f0f7ff", "#c8e0f8"),
        "无法判断": ("#888",   "#f8f8f8", "#e8e8e8"),
    }
    text_color, bg_color, border_color = color_map.get(stage, ("#555", "#f8f8f8", "#ddd"))
    desc_part = f'<p style="margin:4px 0 0;font-size:.82em;color:#666">{_html.escape(description)}</p>' if description else ""
    adv_part  = (f'<p style="margin:6px 0 0;font-size:.88em;font-weight:600;color:{text_color}">{_html.escape(advice)}</p>'
                 if advice else "")
    return (
        f'<div style="background:{bg_color};border:1.5px solid {border_color};'
        f'border-radius:12px;padding:12px 16px;margin:6px 0;">'
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<span style="font-size:1.8em;line-height:1">{icon}</span>'
        f'<span style="font-size:1.05em;font-weight:700;color:{text_color}">{_html.escape(stage)}</span>'
        f'</div>'
        f'{desc_part}{adv_part}'
        f'</div>'
    )


# ── 方案分享 ─────────────────────────────────────────────────────

def plan_to_share_text(plan_data: dict) -> str:
    """将方案数据转为适合微信分享的纯文本摘要（QR 码内容限 600 字符）。"""
    if not plan_data:
        return ""
    tl       = plan_data.get("timeline") or {}
    items    = tl.get("items") or []
    portions = plan_data.get("portions") or {}
    meta     = []
    if tl.get("broth_type"):  meta.append(f"锅底：{tl['broth_type']}")
    if tl.get("user_mode"):   meta.append(f"模式：{tl['user_mode']}")
    if plan_data.get("num_people"): meta.append(f"{plan_data['num_people']}人份")
    if tl.get("total_duration_display"): meta.append(f"总时长：{tl['total_duration_display']}")
    lines = ["🍲 涮涮AI 火锅方案"]
=======
def boiling_result_html(icon: str, stage: str, description: str, advice: str) -> str:
    """开锅检测结果展示 HTML。"""
    if not stage:
        return ""
    color_map = {
        "沸腾": ("#c0392b", "#fff5f5", "#ffd5d5"),
        "微沸": ("#e07c24", "#fff8f0", "#ffe5c0"),
        "未沸": ("#2980b9", "#f0f7ff", "#c8e0f8"),
        "无法判断": ("#888", "#f8f8f8", "#e8e8e8"),
    }
    text_color, bg_color, border_color = color_map.get(stage, ("#555", "#f8f8f8", "#ddd"))
    desc_esc = _html.escape(description) if description else ""
    adv_esc = _html.escape(advice) if advice else ""
    desc_part = f"<p style=\"margin:4px 0 0;font-size:.82em;color:#666\">{desc_esc}</p>" if desc_esc else ""
    adv_part = (
        f"<p style=\"margin:6px 0 0;font-size:.88em;font-weight:600;color:{text_color}\">{adv_esc}</p>"
        if adv_esc else ""
    )
    return (
        f"<div style=\"background:{bg_color};border:1.5px solid {border_color};"
        f"border-radius:12px;padding:12px 16px;margin:6px 0;\">"
        f"<div style=\"display:flex;align-items:center;gap:8px;\">"
        f"<span style=\"font-size:1.8em;line-height:1\">{icon}</span>"
        f"<span style=\"font-size:1.05em;font-weight:700;color:{text_color}\">{_html.escape(stage)}</span>"
        f"</div>{desc_part}{adv_part}</div>"
    )


def flash_overlay_html(flash_duration_sec: float = 1.0) -> str:
    """全屏闪烁 overlay HTML，用于下锅/捞出到点提醒。"""
    return (
        '<div class="hotpot-flash-overlay" style="'
        "position:fixed;inset:0;z-index:9999;pointer-events:none;"
        "background:rgba(255,140,0,0.35);"
        f"animation:hotpot-flash-fade {flash_duration_sec}s ease-out forwards;"
        '"></div>'
        "<style>@keyframes hotpot-flash-fade { 0% { opacity: 1; } 100% { opacity: 0; } }</style>"
    )


def plan_to_share_text(plan_data: Optional[dict]) -> str:
    """将方案数据转换为适合分享的纯文本摘要。"""
    if not plan_data:
        return ""
    tl = plan_data.get("timeline") or {}
    items = tl.get("items") or []
    broth = tl.get("broth_type", "")
    mode = tl.get("user_mode", "")
    total = tl.get("total_duration_display", "")
    num = plan_data.get("num_people") or ""
    portions = plan_data.get("portions") or {}
    lines = ["🍲 涮涮AI 火锅方案"]
    meta = [x for x in [f"锅底：{broth}" if broth else "", f"模式：{mode}" if mode else "", f"{num}人份" if num else "", f"总时长：{total}" if total else ""] if x]
>>>>>>> Stashed changes
    if meta:
        lines.append(" | ".join(meta))
    lines.append("")
    lines.append("【下锅顺序】")
    for i, item in enumerate(items, 1):
<<<<<<< Updated upstream
        name  = item.get("ingredient_name", "")
        p     = portions.get(name, 1)
        pstr  = f" x{p}" if p > 1 else ""
        tip   = item.get("technique", "")
        row   = f"{i}. {name}{pstr}  {item.get('cooking_display', '')}"
=======
        name = item.get("ingredient_name", "")
        t = item.get("cooking_display", "")
        p = portions.get(name, 1)
        pstr = f" x{p}" if p > 1 else ""
        tip = item.get("technique", "")
        row = f"{i}. {name}{pstr}  {t}"
>>>>>>> Stashed changes
        if tip:
            row += f"  （{tip}）"
        lines.append(row)
    warnings = plan_data.get("safety_warnings") or []
    if warnings:
<<<<<<< Updated upstream
        lines += ["", "【安全提醒】"] + [f"· {w}" for w in warnings]
    lines += ["", "by 涮涮AI"]
=======
        lines.append("")
        lines.append("【安全提醒】")
        for w in warnings:
            lines.append(f"· {w}")
    lines.append("")
    lines.append("by 涮涮AI")
>>>>>>> Stashed changes
    return "\n".join(lines)


def copy_plan_html(plan_text: str) -> str:
<<<<<<< Updated upstream
    """返回一段 HTML+JS，将 plan_text 写入剪贴板并在页面提示结果。"""
    if not plan_text or not plan_text.strip():
        return "<span style='color:#e67e22;font-size:.9em'>⚠️ 暂无方案内容，请先生成方案。</span>"
    import json
    text_js = json.dumps(plan_text)
    uid = f"copy_btn_{int(time.time() * 1000) % 1_000_000}"
=======
    """返回复制到剪贴板的 HTML+JS 片段。"""
    if not plan_text or not plan_text.strip():
        return "<span style='color:#e67e22;font-size:.9em'>⚠️ 暂无方案内容，请先生成方案。</span>"
    text_js = json.dumps(plan_text)
    uid = f"copy_btn_{int(time.time() * 1000) % 1000000}"
>>>>>>> Stashed changes
    return f"""
<span id="{uid}_status" style="font-size:.88em;color:#27ae60"></span>
<script>
(function() {{
  var text = {text_js};
<<<<<<< Updated upstream
  function showOk()  {{ var el=document.getElementById('{uid}_status'); if(el){{ el.textContent='✅ 已复制到剪贴板！'; setTimeout(function(){{el.textContent='';}}, 3500); }} }}
  function showFail(e) {{ var el=document.getElementById('{uid}_status'); if(el) el.textContent='⚠️ 复制失败，请手动选中下方文字复制。'; }}
  if (navigator.clipboard && window.isSecureContext) {{
    navigator.clipboard.writeText(text).then(showOk, showFail);
  }} else {{
    try {{ var ta=document.createElement('textarea'); ta.value=text; ta.style.position='fixed'; ta.style.opacity='0'; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta); showOk(); }} catch(e) {{ showFail(e); }}
=======
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
>>>>>>> Stashed changes
  }}
}})();
</script>
"""


def generate_qr_html(plan_text: str) -> str:
<<<<<<< Updated upstream
    """用 qrcode 库生成二维码 PNG 并以 base64 内嵌返回；未安装时返回提示。"""
    if not plan_text or not plan_text.strip():
        return "<span style='color:#e67e22;font-size:.9em'>⚠️ 暂无方案内容，请先生成方案。</span>"
    try:
        import qrcode as _qr
    except ImportError:
        return ("<div style='padding:10px;border:1px solid #f0c040;border-radius:8px;"
                "background:#fffde7;font-size:.88em;color:#7d6608'>"
                "⚠️ 需要安装 qrcode[pil]：<br><code>pip install qrcode[pil]</code></div>")
    content = plan_text[:600]
    try:
        qr = _qr.QRCode(version=None, error_correction=_qr.constants.ERROR_CORRECT_L, box_size=7, border=3)
=======
    """用 qrcode 库将方案摘要生成二维码 PNG，以 base64 内嵌 HTML 返回。"""
    if not plan_text or not plan_text.strip():
        return "<span style='color:#e67e22;font-size:.9em'>⚠️ 暂无方案内容，请先生成方案。</span>"
    try:
        import qrcode as _qrcode
        from PIL import Image as _PILImage
    except ImportError:
        return (
            "<div style='padding:10px;border:1px solid #f0c040;border-radius:8px;"
            "background:#fffde7;font-size:.88em;color:#7d6608'>"
            "⚠️ 需要安装 qrcode[pil] 才能生成二维码：<br><code>pip install qrcode[pil]</code></div>"
        )
    content = plan_text[:600]
    try:
        qr = _qrcode.QRCode(version=None, error_correction=_qrcode.constants.ERROR_CORRECT_L, box_size=7, border=3)
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
            "<div style='font-size:.78em;color:#999;margin-top:6px'>用微信扫码即可查看方案</div>"
            "</div>"
=======
            "<div style='font-size:.78em;color:#999;margin-top:6px'>用微信扫码即可查看方案</div></div>"
>>>>>>> Stashed changes
        )
    except Exception as e:
        return f"<span style='color:#c0392b;font-size:.9em'>二维码生成失败：{e}</span>"
