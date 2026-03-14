# -*- coding: utf-8 -*-
"""
前端 HTML 组件层
所有生成 HTML 字符串的函数集中于此。
不依赖 Gradio，不依赖 api.py，可独立单测。
"""

import html as _html
import os
import time
import base64
import io
import json
from typing import List, Any, Optional

from data.ingredients_db import search_ingredient

# 项目根目录（frontend 的上级）
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COVER_IMAGE_PATH = os.path.join(_ROOT, "picture.png")


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

def ingredient_table_rows(state: list) -> list:
    """将 state 转为展示用行列表。"""
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
    """将当前表单一行加入 state。"""
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
    """删除选中行。"""
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

def _cover_image_base64() -> str:
    """若存在 picture.png 则返回 base64 数据 URL，否则返回空串。"""
    if not os.path.isfile(COVER_IMAGE_PATH):
        return ""
    try:
        with open(COVER_IMAGE_PATH, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception:
        return ""


def homepage_html() -> str:
    """首页海报 HTML；若项目根目录有 picture.png 则作为封面图展示。"""
    cover_data = _cover_image_base64()
    if cover_data:
        cover_block = (
            f'<div class="hp-poster-cover" style="'
            "position:absolute;inset:0;z-index:0;background-size:cover;background-position:center;"
            f"background-image:url({cover_data});"
            '"></div>'
            '<div class="hp-poster-overlay" style="'
            "position:absolute;inset:0;z-index:1;background:rgba(0,0,0,.35);pointer-events:none;"
            '"></div>'
        )
    else:
        cover_block = ""
    return f"""
<div class="hp-main-container">
  <div class="hp-wrap">
    <div class="hp-poster">{cover_block}</div>
  </div>
</div>
"""


def homepage_action_card_html() -> str:
    """首页下方浅色行动卡片（/三步走/、定制你的专属菜单），与「开始定制」按钮同块。"""
    return """
<div class="hp-action-card">
  <div class="hp-action-line">/ 三步走 /</div>
  <div class="hp-action-sub">定制你的专属菜单</div>
</div>
"""

def step_header_html(step_num: str, step_title: str, extra_cls: str = "") -> str:
    """统一步骤头部横条（斜杠风格）。"""
    return (
        f'<div class="shuai-step-bar {extra_cls}">'
        f'<div class="shuai-step-wrapper">'
        f'<span class="shuai-step-num">/ {step_num} /</span>'
        f'<span class="shuai-step-title">{step_title}</span>'
        f'</div></div>'
    )

def basket_drawer_html(state: list) -> str:
    """购物车抽屉内的食材列表 HTML（只读）。"""
    if not state:
        return '<p class="drawer-empty">尚未添加食材，请在上方输入。</p>'
    rows = []
    for row in state:
        name = (row[0] if row else "") or ""
        if not name:
            continue
        t_val   = row[1] if len(row) > 1 else None
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

def basket_bar_html(count: int, state: list) -> str:
    """底部购物车栏 HTML（含上拉抽屉），采用全局动画触发，不再劫持DOM。"""
    items_list = [r[0] for r in (state or []) if r and r[0]]
    preview = "、".join(items_list[:3]) + ("…" if len(items_list) > 3 else "") if items_list else "还未添加食材"
    badge   = f'<span class="bsk-badge">{count}</span>' if count > 0 else ""
    drawer_content = basket_drawer_html(state or [])

    return f"""
<div class="shuai-basket-area">
  <div class="shuai-basket-bar" onclick="window.shuaiToggleDrawer(true)">
    <div class="bsk-left">
      <span class="bsk-icon">🛒{badge}</span>
      <span class="bsk-preview">{preview}</span>
    </div>
    <div class="bsk-right">
      <span class="bsk-count">共 {count} 件涮品</span>
    </div>
  </div>

  <div class="shuai-overlay" id="shuai-global-overlay" onclick="window.shuaiToggleDrawer(false)"></div>

  <div class="shuai-drawer" id="shuai-global-drawer">
    <div class="shuai-drawer-handle"></div>
    <div class="shuai-drawer-header">
      <span class="shuai-drawer-title">已选食材（{count}件）</span>
      <button class="shuai-drawer-close" onclick="window.shuaiToggleDrawer(false)">✕</button>
    </div>
    <div class="shuai-drawer-body">{drawer_content}</div>
    <div class="shuai-drawer-footer">
      <button class="shuai-drawer-next" onclick="window.shuaiTriggerNext(event)">下一步</button>
    </div>
  </div>
</div>
"""

def boiling_result_html(icon: str, stage: str, description: str, advice: str) -> str:
    """渲染开锅检测结果卡片。"""
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

def plan_to_share_text(plan_data: dict) -> str:
    """将方案数据转为适合微信分享的纯文本摘要。"""
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
    if meta:
        lines.append(" | ".join(meta))
    lines.append("")
    lines.append("【下锅顺序】")
    for i, item in enumerate(items, 1):
        name = item.get("ingredient_name", "")
        t = item.get("cooking_display", "")
        p = portions.get(name, 1)
        pstr = f" x{p}" if p > 1 else ""
        tip = item.get("technique", "")
        row = f"{i}. {name}{pstr}  {t}"
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

def copy_plan_html(plan_text: str) -> str:
    """返回复制到剪贴板的 HTML+JS 片段。"""
    if not plan_text or not plan_text.strip():
        return "<span style='color:#e67e22;font-size:.9em'>⚠️ 暂无方案内容，请先生成方案。</span>"
    text_js = json.dumps(plan_text)
    uid = f"copy_btn_{int(time.time() * 1000) % 1000000}"
    return f"""
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

def generate_qr_html(plan_text: str) -> str:
    """用 qrcode 库将方案摘要生成二维码 PNG，以 base64 内嵌 HTML 返回。"""
    if not plan_text or not plan_text.strip():
        return "<span style='color:#e67e22;font-size:.9em'>⚠️ 暂无方案内容，请先生成方案。</span>"
    try:
        import qrcode as _qr
    except ImportError:
        return (
            "<div style='padding:10px;border:1px solid #f0c040;border-radius:8px;"
            "background:#fffde7;font-size:.88em;color:#7d6608'>"
            "⚠️ 需要安装 qrcode[pil] 才能生成二维码：<br><code>pip install qrcode[pil]</code></div>"
        )
    content = plan_text[:600]
    try:
        qr = _qr.QRCode(version=None, error_correction=_qr.constants.ERROR_CORRECT_L, box_size=7, border=3)
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
            "<div style='font-size:.78em;color:#999;margin-top:6px'>用微信扫码即可查看方案</div></div>"
        )
    except Exception as e:
        return f"<span style='color:#c0392b;font-size:.9em'>二维码生成失败：{e}</span>"

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

# 兼容 handlers 等使用的旧名称
ingredient_table_display_rows = ingredient_table_rows
ingredient_table_display_html = ingredient_table_html
