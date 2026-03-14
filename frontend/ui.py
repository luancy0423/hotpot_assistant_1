# -*- coding: utf-8 -*-
"""
前端 UI 层
只负责：① 用 Gradio 声明所有组件  ② 绑定事件到 handlers/nav/timer 的回调函数。
不含任何业务逻辑，不直接调用 api.py。
"""

import gradio as gr

from config import BROTH_CHOICES, TEXTURE_CHOICES, MODE_CHOICES
from frontend.components import (
    homepage_html, homepage_action_card_html, step_header_html,
    basket_bar_html, boiling_result_html,
    add_ingredient_row,
    copy_plan_html, generate_qr_html,
)
from frontend.parsers import (
    ingredient_lookup_hint, search_ingredients_for_dropdown,
)
from frontend.nav import (
    nav_next_v4, nav_prev_v4, nav_restart_v4, nav_back_timer_v4,
)
from frontend.handlers import (
    api,
    generate_and_go, show_generating, start_eating,
    voice_to_ingredients, image_to_ingredients,
    load_preference_ui,
)
from frontend.timer import timer_tick

# ── 样式表 ───────────────────────────────────────────────────────
_CSS = """
/* ═══════════════════════════════════════════════════════
   涮涮AI v4 CSS  —  火锅红主色 / 手机框居中 / 弹性滚动
   ═══════════════════════════════════════════════════════ */

/* ── 网页最外层背景（深暗红） ── */
body {
  font-family: 'Noto Sans SC', 'PingFang SC', 'Hiragino Sans GB',
               'Microsoft YaHei', sans-serif !important;
  background: #2b0505 !important;
}

/* ── 主容器 450×954 ── */
.gradio-container {
  width: 450px !important;
  max-width: 100% !important;
  min-height: 954px !important;
  height: 954px !important;
  margin: 0 auto !important;
  padding: 0 !important;
  padding-bottom: 80px !important;
  border: none !important;
  border-radius: 0 !important;
  overflow: auto !important;
  background: #a31515 !important;
  display: flex !important; flex-direction: column !important;
  position: relative !important;
  box-sizing: border-box !important;
}

@media (min-width: 500px) {
  .gradio-container {
      margin: 20px auto !important;
      border: 10px solid #111 !important;
      border-radius: 40px !important;
  }
}

.gradio-container > .main {
  flex: 1 !important;
}
.contain { padding: 0 !important; }
footer  { display: none !important; }

/* ── 各个页面容器设为透明，透出红色底 ── */
#page-home, #page-step0, #page-step1, #page-step2, #page-step3 {
  background: transparent !important;
}

/* ── 步骤头部「第X步」颜色底框 ── */
.shuai-step-bar {
  background: linear-gradient(135deg, rgba(139,0,0,.75) 0%, rgba(163,21,21,.85) 50%, rgba(192,57,43,.7) 100%) !important;
  text-align: center !important;
  padding: 16px 20px !important;
  display: block !important;
  margin: 0 12px 16px !important;
  border-radius: 16px !important;
  border: 2px solid rgba(255,218,117,.45) !important;
  box-shadow: 0 4px 12px rgba(0,0,0,.25) !important;
}
.shuai-step-bar--timer {
  background: linear-gradient(135deg, rgba(44,62,80,.85) 0%, rgba(52,73,94,.9) 100%) !important;
  border-color: rgba(255,255,255,.2) !important;
}
.shuai-step-wrapper { display: inline-block; }
.shuai-step-num   { display: block; font-family: 'Noto Serif SC', serif; font-size: 1.2em; color: #ffda75 !important; margin-bottom: 5px; letter-spacing: .15em; }
.shuai-step-title { font-size: 1.5em; font-weight: 700; color: #ffffff !important; }
.shuai-sec-sep { font-size: .85em; color: #ffda75 !important; letter-spacing: .1em; padding: 9px 12px 5px; font-weight: bold; }

/* ── 首页海报（比例 99:140，仅图片无文字）── */
.hp-wrap { display: flex; flex-direction: column; align-items: stretch; }
.hp-poster {
  position: relative; overflow: hidden; width: 100% !important;
  aspect-ratio: 99 / 140 !important;
  border-radius: 0 0 20px 20px;
  background: #2b0505;
}
.hp-poster-cover {
  position: absolute !important; inset: 0 !important; z-index: 0;
  background-size: cover !important; background-position: center !important;
  background-repeat: no-repeat !important;
}
.hp-poster-overlay {
  position: absolute !important; inset: 0 !important; z-index: 1;
  pointer-events: none !important;
}
/* ── 首页下方行动卡片（浅色块 + 开始定制按钮）── */
#hp-action-block {
  background: #faf7f2 !important;
  border-radius: 20px !important;
  padding: 20px 24px 18px !important;
  margin: 16px 12px 12px !important;
  border: 1px solid #e8e0d8 !important;
  box-shadow: 0 4px 16px rgba(0,0,0,.08) !important;
}
.hp-action-card { margin-bottom: 14px !important; }
.hp-action-line {
  font-size: .95em !important; color: #2a2a2a !important;
  letter-spacing: .12em !important; text-align: center !important;
  padding-bottom: 8px !important; border-bottom: 1px solid #e8e0d8 !important;
  margin-bottom: 8px !important;
}
.hp-action-sub {
  font-size: .9em !important; color: #555 !important;
  text-align: center !important;
}
#btn-enter-home button {
  height: 52px !important; border-radius: 26px !important;
  font-size: 1.1em !important; font-weight: 600 !important; letter-spacing: .15em !important;
  background: #faf7f2 !important; color: #1a1a1a !important;
  border: 2px solid #1a1a1a !important; box-shadow: none !important;
  width: 100% !important;
}
#btn-enter-home button:hover {
  background: #f0ebe3 !important; border-color: #1a1a1a !important;
}
.hp-bounce {
  text-align: center; color: rgba(255,255,255,.6);
  font-size: .88em; margin: 8px 0 4px;
  animation: bounce 1.5s ease-in-out infinite;
}
@keyframes bounce { 0%,100% { transform: translateY(0); } 50% { transform: translateY(6px); } }

/* ── 步骤1：食材输入 ── */
#ing-card-group { background: white; margin: 12px; border-radius: 20px !important; padding: 20px !important; box-shadow: 0 4px 14px rgba(0,0,0,.2); border: none !important; }
.ing-card-title { font-size: .78em; color: #e07c24; letter-spacing: .1em; font-weight: 600; margin-bottom: 10px; text-transform: uppercase; }
#img-rec-group { background: white; margin: 0 12px 10px; border-radius: 14px; padding: 0 14px 14px; box-shadow: 0 4px 14px rgba(0,0,0,.2); }
#merchant-status { margin: 0 12px; color: white; }
#page-step0 #btn-merchant { margin: 4px 12px 8px; width: calc(100% - 24px); }
#page-step0 #ingredient-table-html { margin: 0 12px; background: white; border-radius: 10px; padding: 5px; }
#delete-row      { margin: 4px 12px 8px; }
#step0-next-row  { margin: 16px 12px 8px; justify-content: flex-end; }
#step0-next-row button { min-width: 120px; }
#ing-confirm-row { margin-top: 10px; gap: 10px; }
#ing-confirm-row #btn-confirm-add { flex: 2 !important; }
#ing-confirm-row #btn-clear-input { flex: 1 !important; }
#time-portion-row { margin-top: 6px; }
#ing-voice-img-row { margin-top: 12px; gap: 12px !important; }
#ing-voice-col .wrap, #ing-img-col .wrap { min-height: 0 !important; }
#ing-voice-col audio, #ing-voice-col [class*="audio"], #ing-img-col .image-container { max-height: 72px !important; }
#ing-voice-col label, #ing-img-col label { font-size: .85em !important; }
#btn-voice-rec, #btn-image-rec { font-size: .8em !important; padding: 6px 10px !important; }

/* ── 购物车栏悬浮 ── */
#basket-bar-row { background: #2a2424 !important; display: flex !important; align-items: center; justify-content: space-between; padding: 11px 16px; margin: 0; position: fixed; bottom: 0; left: 50%; transform: translateX(-50%); width: 450px; max-width: 100%; z-index: 50; box-sizing: border-box; }
#basket-bar-row > div:first-child { flex: 1 !important; min-width: 0 !important; }
#basket-bar-row .shuai-basket-bar { background: transparent !important; padding: 0; flex: 1; min-width: 0; }
#basket-bar-row #btn-next-in-bar button,
#basket-bar-row [id^="btn-next-in-bar"] button { background: linear-gradient(135deg, #e07c24, #c0392b) !important; color: white !important; border: none; border-radius: 6px; padding: 7px 14px; font-size: .88em; }
.shuai-basket-area { width: 100%; }
.shuai-basket-bar  { background: #2a2424; color: white; display: flex; align-items: center; justify-content: space-between; padding: 11px 16px; cursor: default; }
.bsk-left  { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; cursor: pointer; }
.bsk-icon  { font-size: 1.25em; position: relative; flex-shrink: 0; }
.bsk-badge { position: absolute; top: -5px; right: -7px; background: #e07c24; color: white; border-radius: 50%; font-size: .6em; width: 15px; height: 15px; display: flex; align-items: center; justify-content: center; font-weight: 700; }
.bsk-preview { font-size: .8em; color: rgba(255,255,255,.65); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.bsk-right { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
.bsk-count { font-size: 1em !important; font-weight: 600 !important; color: #fff !important; background: rgba(255,255,255,.1); padding: 4px 12px; border-radius: 20px; }
/* ── 遮罩层 (修复动画) ── */
.shuai-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.6);
  z-index: 99998 !important;
  cursor: pointer;
  /* 核心：用 opacity 和 visibility 替代 display:none 以支持动画过渡 */
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.3s ease, visibility 0.3s ease;
}
.shuai-overlay.active {
  opacity: 1;
  visibility: visible;
}

/* ── 上拉抽屉 (修复动画) ── */
.shuai-drawer {
  position: fixed; bottom: 0; left: 50%;
  /* 核心：默认沉在屏幕底部外 100% 的位置 */
  transform: translateX(-50%) translateY(100%);
  width: 450px; max-width: 100%; max-height: 70vh;
  background: white; border-radius: 18px 18px 0 0;
  z-index: 99999 !important; display: flex; flex-direction: column;
  transition: transform 0.3s cubic-bezier(0.32,0,0.15,1);
  box-shadow: 0 -6px 36px rgba(0,0,0,0.18);
}
.shuai-drawer.active {
  /* 激活时升起回原位 */
  transform: translateX(-50%) translateY(0);
}

/* 确保底部悬浮栏自身也能触发鼠标手势 */
.shuai-basket-bar {
  cursor: pointer !important;
}
.shuai-drawer-handle { width: 38px; height: 4px; background: #ddd; border-radius: 2px; margin: 10px auto 6px; }
.shuai-drawer-header { padding: 8px 20px 14px; border-bottom: 1px solid #f0ece8; display: flex; justify-content: space-between; align-items: center; color: #111 !important; }
.shuai-drawer-title  { font-weight: 600; font-size: .97em; color: #111 !important; }
.shuai-drawer-close  { background: none; border: none; font-size: 1.05em; cursor: pointer; color: #666; padding: 4px 8px; }
.shuai-drawer-body   { overflow-y: auto; flex: 1; padding: 10px 20px; color: #111 !important; }
.drawer-item  { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #f3efe9; color: #111 !important; }
.di-info { flex: 1; display: flex; flex-direction: column; gap: 4px; }
.di-name { font-weight: 500; font-size: .93em; color: #111 !important; }
.di-meta { font-size: .8em; color: #333 !important; }
.drawer-empty { color: #555; font-size: .88em; text-align: center; padding: 24px 0; }
.shuai-drawer-footer { padding: 12px 20px; border-top: 1px solid #f0ece8; display: flex; justify-content: flex-end; }
.shuai-drawer-next   { background: linear-gradient(135deg, #e07c24, #c0392b); color: white; border: none; border-radius: 24px; padding: 10px 28px; font-size: .93em; cursor: pointer; font-family: 'Noto Sans SC', sans-serif; font-weight: 500; }
#btn-next-hidden { position: fixed !important; top: -9999px !important; left: -9999px !important; width: 1px !important; height: 36px !important; opacity: 0 !important; z-index: -999 !important; overflow: hidden !important; }

/* ── 食材表格 ── */
.ingredient-table-wrap .ingredient-display-table { width: 100%; border-collapse: collapse; color: black; }
.ingredient-table-wrap .ingredient-display-table th,
.ingredient-table-wrap .ingredient-display-table td { border: 1px solid #ede8e2; padding: .38em .55em; text-align: left; font-size: .88em; }
.ingredient-table-wrap .ingredient-display-table th { background: #f7f3ee; font-weight: 600; }
.ingredient-table-empty { color: #bbb; font-size: .88em; margin: .4em 0; }
#ingredient-table-html { overflow: visible !important; max-height: none !important; }

/* ── 步骤2：偏好 ── */
.pref-acc { margin: 8px 12px !important; border-radius: 12px !important; overflow: hidden !important; box-shadow: 0 4px 14px rgba(0,0,0,.2) !important; border: none !important; background: white !important; }
.pref-acc--hero { border-color: #f5c89a !important; }
.pref-acc > div:first-child { background: white !important; font-family: 'Noto Sans SC', sans-serif !important; font-size: .97em !important; color: #2a2a2a !important; padding: 14px 18px !important; transition: background .15s !important; }
.pref-acc > div:first-child:hover { background: #fef9f4 !important; }
.pref-acc--hero > div:first-child { font-size: 1.05em !important; font-weight: 600 !important; background: linear-gradient(135deg,#fff 70%,#fff5ee 100%) !important; border-bottom: 2px solid #f5c89a !important; }
.pref-radio .wrap { display: flex !important; flex-wrap: wrap !important; padding: 10px 12px 14px !important; gap: 6px !important; }
.pref-radio label { border: 1.5px solid #e8e0d8 !important; border-radius: 20px !important; padding: 6px 16px !important; cursor: pointer !important; font-size: .88em !important; background: #faf8f5 !important; color: #3a3535 !important; display: inline-flex !important; align-items: center !important; transition: all .15s !important; user-select: none !important; }
.pref-radio label:hover { border-color: #e07c24 !important; background: #fff8f0 !important; }
.pref-radio label:has(input:checked) { background: linear-gradient(135deg,#e07c24,#c0392b) !important; border-color: transparent !important; color: white !important; font-weight: 600 !important; }
.pref-radio input[type=radio] { display: none !important; }
#pref-half-row { margin: 0 4px; gap: 0; }
#allergen-col .pref-acc, #people-col .pref-acc { margin: 8px 8px !important; }
#load-pref-btn { margin: 4px 12px 0; width: calc(100% - 24px); }
#pref_status, #result_status { margin: 2px 12px; color: white; }
#step1-nav-row { margin: 8px 12px 16px; gap: 8px; }
#broth-radio .wrap { display: grid !important; grid-template-columns: 1fr 1fr !important; gap: 12px !important; padding: 10px !important; }
#broth-radio label { height: 90px !important; background: white !important; border: 2px solid #eee !important; border-radius: 15px !important; display: flex !important; align-items: center !important; justify-content: center !important; transition: all .2s !important; box-shadow: 0 2px 6px rgba(0,0,0,.05) !important; }
#broth-radio label:has(input:checked) { border-color: #e65c00 !important; background: #fff8f0 !important; }
#broth-radio input[type="radio"] { display: none !important; }

/* ── 步骤3：方案结果 ── */
#plan-scroll-wrap { background: white; margin: 12px; border-radius: 14px; padding: 16px 18px; box-shadow: 0 4px 14px rgba(0,0,0,.2); max-height: 44vh; overflow-y: auto; scrollbar-width: thin; scrollbar-color: #e0d8d0 #f5f0ea; color: black; }
#plan-scroll-wrap::-webkit-scrollbar { width: 4px; }
#plan-scroll-wrap::-webkit-scrollbar-track { background: #f5f0ea; }
#plan-scroll-wrap::-webkit-scrollbar-thumb { background: #d8cfc7; border-radius: 2px; }
.eating-btn-wrap { display: flex; justify-content: center; padding: 18px 0 10px; }
#btn-start-eating button, #page-step2 #btn-start-eating button { width: 112px !important; height: 112px !important; border-radius: 50% !important; font-family: 'Noto Serif SC', serif !important; font-size: 1.1em !important; font-weight: 700 !important; line-height: 1.45 !important; white-space: pre-line !important; background: linear-gradient(145deg,#e07c24 0%,#c0392b 100%) !important; color: white !important; border: none !important; box-shadow: 0 4px 22px rgba(192,57,43,.4), 0 0 0 7px rgba(224,124,36,.13) !important; transition: transform .2s, box-shadow .2s !important; }
#btn-start-eating button:hover { transform: scale(1.06) !important; box-shadow: 0 8px 32px rgba(192,57,43,.52), 0 0 0 9px rgba(224,124,36,.18) !important; }
#share-row { margin: 4px 12px 0; gap: 8px; }
#copy-status-html, #qr-display-html { margin: 2px 12px; min-height: 0; color: white; }
#step2-nav-row { margin: 8px 12px 16px; gap: 8px; }

/* ── 步骤4：计时 ── */
#hotpot-timer-display { margin: 10px; font-family: 'Noto Sans SC', sans-serif; color: white; }

/* ── 开锅检测区域 ── */
#boiling-detect-group { background: white; border-radius: 14px; padding: 12px; margin: 0 12px 8px; box-shadow: 0 4px 14px rgba(0,0,0,.2); }
#boiling-image-input { border-radius: 10px !important; }
#btn-detect-boiling { margin-top: 8px; width: 100%; }
#boiling-result-html { margin-top: 4px; }

/* ── Gradio 通用覆盖 ── */
.block { border: none !important; box-shadow: none !important; }
.gr-form { background: transparent !important; border: none !important; }
.gradio-container .block.padded { padding: 6px 0 !important; }

/* 隐藏后端的辅助组件区（避免 step1 多出一个 textbox） */
.hidden-func-wrap { display: none !important; visibility: hidden !important; position: absolute !important; left: -9999px !important; }

/* 抽屉内删除按钮的样式 */
.drawer-del-btn {
  background: transparent; border: none; font-size: 1.2em;
  color: #999; cursor: pointer; padding: 0 10px; margin-left: 10px;
}
.drawer-del-btn:hover { color: #e74c3c; }
"""

# 注入到头部，避免 Svelte 刷新导致事件丢失
_HEAD_JS = """
<script>
  function getDoc() {
    if (document.getElementById('shuai-global-overlay')) return document;
    try {
      var iframes = document.querySelectorAll('iframe');
      for (var i = 0; i < iframes.length; i++) {
        var doc = iframes[i].contentDocument || (iframes[i].contentWindow && iframes[i].contentWindow.document);
        if (doc && doc.getElementById('shuai-global-overlay')) return doc;
      }
    } catch (e) {}
    return document;
  }

  window.shuaiToggleDrawer = function(show) {
    var doc = getDoc();
    var overlay = doc.getElementById('shuai-global-overlay');
    var drawer = doc.getElementById('shuai-global-drawer');
    if (!overlay || !drawer) return;
    if (show) {
      overlay.style.display = 'block';
      setTimeout(function() { overlay.classList.add('active'); drawer.classList.add('active'); }, 10);
    } else {
      overlay.classList.remove('active');
      drawer.classList.remove('active');
      setTimeout(function() { overlay.style.display = 'none'; }, 300);
    }
  };

  window.shuaiTriggerNext = function(e) {
    if(e) e.stopPropagation();
    window.shuaiToggleDrawer(false);
    setTimeout(function() {
      var doc = getDoc();
      var btnWrap = doc.getElementById('btn-next-in-bar');
      if (btnWrap) { var btn = btnWrap.querySelector('button'); if (btn) btn.click(); }
    }, 150);
  };

  // 核心：点击抽屉里的删除按钮时触发（使用同一 getDoc 保证在 iframe 内也能找到组件）
  window.shuaiDeleteIngredient = function(index) {
    var doc = getDoc();
    var inputWrap = doc.getElementById('hidden-delete-index');
    if (inputWrap) {
      var input = inputWrap.querySelector('input');
      if (input) {
        input.value = String(index);
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
      }
    }
    setTimeout(function() {
      var btnWrap = doc.getElementById('btn-hidden-delete');
      if (btnWrap) {
        var btn = btnWrap.querySelector('button');
        if (btn) btn.click();
      }
    }, 150);
  };
</script>
"""

# ── 主界面构建 ───────────────────────────────────────────────────

def create_ui():
    """
    构建完整的 Gradio 多页应用。
    页面流：首页 → 步骤1（食材）→ 步骤2（偏好）→ 步骤3（方案）→ 步骤4（计时）
    """
    with gr.Blocks(title="涮涮AI - 智能火锅助手") as demo:
        gr.HTML('<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700;900'
                '&family=Noto+Sans+SC:wght@300;400;500&display=swap" rel="stylesheet">')

        # ── States ───────────────────────────────────────────────
        step_state           = gr.State(-1)
        plan_data_state      = gr.State(None)
        plan_text_state      = gr.State("")
        start_time_state     = gr.State(0)
        last_beeped_put      = gr.State(-1)
        last_beeped_take     = gr.State(-1)
        ingredient_table_state = gr.State([])
        search_just_selected = gr.State(False)

        NAV_OUT = [step_state, None, None, None, None, None]  # 占位，实际在绑定时指定

        # ══════════════════════════════════════════════════════════
        # 首页
        # ══════════════════════════════════════════════════════════
        step_home = gr.Column(visible=True, elem_id="page-home")
        with step_home:
            gr.HTML(value=homepage_html())
            with gr.Column(elem_id="hp-action-block"):
                gr.HTML(value=homepage_action_card_html())
                btn_enter = gr.Button("开始定制", elem_id="btn-enter-home", variant="secondary")
                gr.HTML('<div class="hp-bounce">▼</div>')

        # ══════════════════════════════════════════════════════════
        # 步骤1：输入食材
        # ══════════════════════════════════════════════════════════
        step0 = gr.Column(visible=False, elem_id="page-step0")
        with step0:
            gr.HTML(step_header_html("第一步", "输入食材"))

            with gr.Group(elem_id="ing-card-group"):
                gr.HTML('<div class="ing-card-title">新增食材</div>')
                with gr.Row(elem_id="ing-input-top"):
                    with gr.Column(scale=3, elem_id="ing-text-col"):
                        ingredient_name_input = gr.Textbox(label="🖊 食材名称", placeholder="如：毛肚、肥牛、土豆片", lines=1, elem_id="ing-name-tb")
                        ingredient_search_dd  = gr.Dropdown(label="🔍 搜索补全", choices=[], value=None, allow_custom_value=True, interactive=True, elem_id="ing-search-dd")
                        ingredient_default_hint = gr.Markdown("", visible=True)
                with gr.Row(elem_id="time-portion-row"):
                    ingredient_time_input    = gr.Slider(label="涮煮时间(秒)", minimum=0, maximum=600, value=0, step=5, info="留0则使用库默认", scale=2)
                    ingredient_portion_input = gr.Slider(label="份数", minimum=1, maximum=99, value=1, step=1, scale=1)
                with gr.Row(elem_id="ing-confirm-row"):
                    btn_add_row      = gr.Button("✔ 加入清单", variant="primary", elem_id="btn-confirm-add")
                    btn_reject_input = gr.Button("✘ 清空",     variant="secondary", elem_id="btn-clear-input")
                with gr.Row(elem_id="ing-voice-img-row"):
                    with gr.Column(scale=1, elem_id="ing-voice-col"):
                        voice_input   = gr.Audio(label="🎤 语音", sources=["microphone", "upload"], type="filepath", elem_id="ing-voice-audio")
                        btn_voice     = gr.Button("识别语音", size="sm", elem_id="btn-voice-rec")
                        voice_status  = gr.Markdown("", visible=True)
                    with gr.Column(scale=1, elem_id="ing-img-col"):
                        image_input   = gr.Image(label="📷 识图", type="filepath", sources=["upload"], elem_id="ing-image-input")
                        btn_image     = gr.Button("识图填入", size="sm", elem_id="btn-image-rec")
                        image_status  = gr.Markdown("", visible=True)

            merchant_status = gr.Markdown("", visible=True, elem_id="merchant-status")
            btn_merchant    = gr.Button("🔗 一键接入商家点餐系统", size="sm", variant="secondary", elem_id="btn-merchant")

            # 隐藏组件区：用 CSS .hidden-func-wrap 隐藏，保证在 DOM 内以便 JS 能找到并触发
            with gr.Group(elem_classes=["hidden-func-wrap"]):
                hidden_delete_index = gr.Number(value=-1, elem_id="hidden-delete-index", label="")
                btn_hidden_delete   = gr.Button("删除", elem_id="btn-hidden-delete")

            with gr.Row(elem_id="step0-next-row"):
                gr.HTML("")
                btn_next_visible = gr.Button("下一步 ›", variant="primary", elem_id="btn-next-visible")

            with gr.Row(elem_id="basket-bar-row"):
                basket_bar_html_comp = gr.HTML(value=basket_bar_html(0, []), elem_id="basket-bar-html")
                btn_next_bar         = gr.Button("下一步 ›", variant="primary", elem_id="btn-next-in-bar")

        # ══════════════════════════════════════════════════════════
        # 步骤2：锅底与偏好
        # ══════════════════════════════════════════════════════════
        step1 = gr.Column(visible=False, elem_id="page-step1")
        with step1:
            gr.HTML(step_header_html("第二步", "选择你的口味"))
            broth_acc = gr.Accordion("🍲 锅底类型", open=True, elem_classes=["pref-acc", "pref-acc--hero"], elem_id="broth-acc")
            with broth_acc:
                broth_dd = gr.Radio(choices=[t for t, _ in BROTH_CHOICES], value="麻辣红汤", label="", elem_id="broth-radio", elem_classes=["pref-radio"])
            texture_acc = gr.Accordion("🌶 口感偏好", open=True, elem_classes=["pref-acc"])
            with texture_acc:
                texture_dd = gr.Radio(choices=[t for t, _ in TEXTURE_CHOICES], value="标准", label="", elem_classes=["pref-radio"])
            mode_acc = gr.Accordion("👤 用户模式", open=True, elem_classes=["pref-acc"])
            with mode_acc:
                mode_dd = gr.Radio(choices=[t for t, _ in MODE_CHOICES], value="普通", label="", elem_classes=["pref-radio"])
            with gr.Row(elem_id="pref-half-row"):
                with gr.Column(elem_id="allergen-col"):
                    allergen_acc = gr.Accordion("⚠️ 过敏原", open=False, elem_classes=["pref-acc"])
                    with allergen_acc:
                        allergen_input = gr.Textbox(label="", placeholder="如：虾、鱼", lines=1)
                with gr.Column(elem_id="people-col"):
                    people_acc = gr.Accordion("👥 就餐人数", open=False, elem_classes=["pref-acc"])
                    with people_acc:
                        num_people_input = gr.Number(label="", value=2, minimum=1, maximum=99, step=1, precision=0)
            load_pref_btn = gr.Button("📂 加载我的偏好", size="sm", elem_id="load-pref-btn")
            pref_status   = gr.Markdown("", elem_id="pref_status")
            result_status = gr.Markdown("", elem_id="result_status")
            with gr.Row(elem_id="step1-nav-row"):
                btn_prev     = gr.Button("← 上一步",   elem_id="btn-prev-s1")
                btn_generate = gr.Button("⚡ 生成方案", variant="primary", elem_id="btn-generate")

        # ══════════════════════════════════════════════════════════
        # 步骤3：方案结果
        # ══════════════════════════════════════════════════════════
        step2 = gr.Column(visible=False, elem_id="page-step2")
        with step2:
            gr.HTML(step_header_html("第三步", "涮煮方案"))
            with gr.Group(elem_id="plan-scroll-wrap"):
                output_md = gr.Markdown("方案将显示在此。", label="", elem_id="plan-output-md")
            with gr.Row(elem_id="share-row"):
                btn_copy_plan = gr.Button("📋 复制方案文字", size="sm", variant="secondary")
                btn_gen_qr    = gr.Button("📱 生成分享二维码", size="sm", variant="secondary")
            copy_status_html = gr.HTML("", elem_id="copy-status-html")
            qr_html          = gr.HTML("", elem_id="qr-display-html")
            gr.HTML('<div class="eating-btn-wrap">')
            btn_start_eating = gr.Button("开始\n吃饭", variant="primary", elem_id="btn-start-eating")
            gr.HTML('</div>')
            with gr.Row(elem_id="step2-nav-row"):
                btn_restart = gr.Button("↩ 重新开始", elem_id="btn-restart")
                btn_prev2   = gr.Button("← 上一步",   elem_id="btn-prev-s2")

        # ══════════════════════════════════════════════════════════
        # 步骤4：吃饭计时
        # ══════════════════════════════════════════════════════════
        step3 = gr.Column(visible=False, elem_id="page-step3")
        with step3:
            gr.HTML(step_header_html("", "🍲 吃饭计时", "shuai-step-bar--timer"))
            timer_reminder_md = gr.HTML(
                value="<p style='color:#bbb;text-align:center;padding:40px;font-size:.95em'>点击「开始吃饭」后计时将在此显示。</p>",
                elem_id="hotpot-timer-display",
            )
            timer_beep_html = gr.HTML("")
            timer_bottom_md = gr.Markdown("")
            gr.HTML('<div class="shuai-sec-sep" style="margin:10px 0 4px">📷 开锅检测</div>')
            with gr.Group(elem_id="boiling-detect-group"):
                boiling_image      = gr.Image(label="拍摄 / 上传锅底照片", sources=["webcam", "upload"], type="filepath", elem_id="boiling-image-input", height=180)
                btn_detect_boiling = gr.Button("🔍 检测是否开锅", variant="primary", size="sm", elem_id="btn-detect-boiling")
                boiling_result     = gr.HTML("", elem_id="boiling-result-html")
            btn_back_from_timer = gr.Button("结束计时，返回首页", elem_id="btn-back-timer")

        # ══════════════════════════════════════════════════════════
        # Event Bindings
        # ══════════════════════════════════════════════════════════
        _nav_outputs = [step_state, step_home, step0, step1, step2, step3]

        # 首页 → 步骤1
        btn_enter.click(
            fn=lambda: (0, gr.update(visible=False), gr.update(visible=True),
                        gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)),
            inputs=[], outputs=_nav_outputs,
        )

        # 步骤1：食材名称搜索补全
        def _on_name_change(name_val, just_sel):
            try:
                if just_sel:
                    return gr.update(), gr.update(), False
                choices = search_ingredients_for_dropdown(name_val)
                hint    = ingredient_lookup_hint(name_val, None)
                return gr.update(choices=choices, value=None), hint, False
            except Exception:
                return gr.update(choices=[], value=None), "", False

        ingredient_name_input.change(fn=_on_name_change, inputs=[ingredient_name_input, search_just_selected], outputs=[ingredient_search_dd, ingredient_default_hint, search_just_selected])

        ingredient_time_input.change(
            fn=lambda n, t: ingredient_lookup_hint(n, t),
            inputs=[ingredient_name_input, ingredient_time_input], outputs=[ingredient_default_hint],
        )

        def _on_search_select(v):
            try:
                if v and str(v).strip():
                    return str(v).strip(), gr.update(choices=[], value=None), True
                return gr.update(), gr.update(choices=[], value=None), False
            except Exception:
                return gr.update(), gr.update(), False

        ingredient_search_dd.change(fn=_on_search_select, inputs=[ingredient_search_dd], outputs=[ingredient_name_input, ingredient_search_dd, search_just_selected])

        # 添加食材行：只更新购物车 HTML，不再返回表格与下拉
        def _add_v4(name, t, p, state):
            try:
                state, _, _, nt, np_, _, _ = add_ingredient_row(name, t, p, state)
                return (state, "", nt, np_, "", basket_bar_html(len(state), state, is_open=False))
            except Exception as e:
                return (state or [], f"❌ 错误：{e}", 0, 1, "", basket_bar_html(len(state or []), state or [], False))

        btn_add_row.click(
            fn=_add_v4,
            inputs=[ingredient_name_input, ingredient_time_input, ingredient_portion_input, ingredient_table_state],
            outputs=[ingredient_table_state, ingredient_name_input, ingredient_time_input, ingredient_portion_input, ingredient_default_hint, basket_bar_html_comp],
        )
        btn_reject_input.click(fn=lambda: ("", 0, 1, ""), inputs=[], outputs=[ingredient_name_input, ingredient_time_input, ingredient_portion_input, ingredient_default_hint])

        # 响应抽屉内的删除操作（索引由 JS 写入 hidden_delete_index，删除后重置为 -1 避免误用）
        def _do_hidden_delete(idx_val, state):
            state = list(state or [])
            try:
                idx = int(idx_val) if idx_val is not None else -1
                if 0 <= idx < len(state):
                    state.pop(idx)
            except (TypeError, ValueError):
                pass
            return (state, basket_bar_html(len(state), state, is_open=True), -1)

        btn_hidden_delete.click(
            fn=_do_hidden_delete,
            inputs=[hidden_delete_index, ingredient_table_state],
            outputs=[ingredient_table_state, basket_bar_html_comp, hidden_delete_index],
        )

        # 图片识别
        def _img_v4(img, state):
            try:
                state, _, status, _ = image_to_ingredients(img, state)
                return (state, status, basket_bar_html(len(state), state))
            except Exception as e:
                return (state or [], f"❌ {e}", basket_bar_html(len(state or []), state or []))

        btn_image.click(fn=_img_v4, inputs=[image_input, ingredient_table_state], outputs=[ingredient_table_state, image_status, basket_bar_html_comp])

        # 语音识别
        def _voice_v4(audio, state):
            try:
                state, _, status, _ = voice_to_ingredients(audio, state)
                return (state, status, basket_bar_html(len(state), state))
            except Exception as e:
                return (state or [], f"❌ {e}", basket_bar_html(len(state or []), state or []))

        btn_voice.click(fn=_voice_v4, inputs=[voice_input, ingredient_table_state], outputs=[ingredient_table_state, voice_status, basket_bar_html_comp])

        # 商家系统（占位）
        def _merchant_v4(state):
            state = state or []
            return (state, "⚠️ 暂未适配商家点餐系统，敬请期待。", basket_bar_html(len(state), state))

        btn_merchant.click(fn=_merchant_v4, inputs=[ingredient_table_state], outputs=[ingredient_table_state, merchant_status, basket_bar_html_comp])

        # 底部「下一步」：参考“隐藏按钮”模式，抽屉内「下一步」由 JS 触发此按钮；底部栏仅保留 HTML 购物车条 + 此按钮，无单独“打开购物车”Gradio 按钮
        btn_next_bar.click(fn=nav_next_v4,     inputs=[step_state], outputs=_nav_outputs)
        btn_next_visible.click(fn=nav_next_v4, inputs=[step_state], outputs=_nav_outputs)

        # 步骤2：偏好 Accordion 标题同步
        broth_dd.change(   fn=lambda v: gr.update(label=f"🍲 锅底类型　✓ {v}"),  inputs=[broth_dd],        outputs=[broth_acc])
        texture_dd.change( fn=lambda v: gr.update(label=f"🌶 口感偏好　✓ {v}"),  inputs=[texture_dd],      outputs=[texture_acc])
        mode_dd.change(    fn=lambda v: gr.update(label=f"👤 用户模式　✓ {v}"),  inputs=[mode_dd],         outputs=[mode_acc])
        allergen_input.change(fn=lambda v: gr.update(label=f"⚠️ 过敏原　{v.strip() or '无'}"), inputs=[allergen_input], outputs=[allergen_acc])
        num_people_input.change(fn=lambda v: gr.update(label=f"👥 就餐人数　{int(v or 2)}人"), inputs=[num_people_input], outputs=[people_acc])

        def _load_pref_v4():
            broth, texture, mode, allergen, status = load_preference_ui()
            return (broth, texture, mode, allergen, 2, status,
                    gr.update(label=f"🍲 锅底类型　✓ {broth}"),
                    gr.update(label=f"🌶 口感偏好　✓ {texture}"),
                    gr.update(label=f"👤 用户模式　✓ {mode}"),
                    gr.update(label=f"⚠️ 过敏原　{allergen.strip() or '无'}"))

        load_pref_btn.click(fn=_load_pref_v4, inputs=[], outputs=[broth_dd, texture_dd, mode_dd, allergen_input, num_people_input, pref_status, broth_acc, texture_acc, mode_acc, allergen_acc])
        btn_prev.click(fn=nav_prev_v4, inputs=[step_state], outputs=_nav_outputs)

        # 生成方案
        btn_generate.click(
            fn=show_generating, inputs=[],
            outputs=[output_md, step_state, step0, step1, step2, step3, result_status],
        ).then(
            fn=generate_and_go,
            inputs=[ingredient_table_state, broth_dd, texture_dd, mode_dd, allergen_input, num_people_input],
            outputs=[output_md, step_state, step0, step1, step2, step3, result_status, plan_data_state, plan_text_state],
        )

        # 步骤3：分享
        btn_copy_plan.click(fn=copy_plan_html,    inputs=[plan_text_state], outputs=[copy_status_html])
        btn_gen_qr.click(   fn=generate_qr_html,  inputs=[plan_text_state], outputs=[qr_html])
        btn_restart.click(  fn=nav_restart_v4,    inputs=[step_state],      outputs=_nav_outputs)
        btn_prev2.click(    fn=nav_prev_v4,        inputs=[step_state],      outputs=_nav_outputs)
        btn_start_eating.click(
            fn=start_eating, inputs=[plan_data_state],
            outputs=[start_time_state, step_state, step0, step1, step2, step3,
                     timer_bottom_md, last_beeped_put, last_beeped_take, timer_reminder_md, timer_beep_html],
        )

        # 步骤4：开锅检测
        def _do_detect_boiling(img_path):
            import os as _os
            if img_path is None or not _os.path.isfile(str(img_path or "")):
                return boiling_result_html("⚠️", "未沸", "请先拍摄或上传一张锅底照片", "")
            try:
                with open(img_path, "rb") as f:
                    img_bytes = f.read()
            except Exception as e:
                return boiling_result_html("❌", "无法判断", f"读取图片失败：{e}", "")
            mime = "image/png" if img_path.endswith(".png") else "image/jpeg"
            resp = api.detect_boiling(image_data=img_bytes, mime_type=mime)
            if not resp.success:
                return boiling_result_html("❌", "无法判断", f"检测失败：{resp.error}", "")
            d    = resp.data
            icon = {"沸腾": "🔥", "微沸": "♨️", "未沸": "⏳", "无法判断": "❓"}.get(d["stage"], "❓")
            return boiling_result_html(icon, d["stage"], d["description"], d["advice"])

        btn_detect_boiling.click(fn=_do_detect_boiling, inputs=[boiling_image], outputs=[boiling_result])

        # 步骤4：计时
        btn_back_from_timer.click(fn=nav_back_timer_v4, inputs=[step_state, start_time_state], outputs=_nav_outputs)
        gr.Timer(value=1).tick(
            fn=timer_tick,
            inputs=[plan_data_state, start_time_state, last_beeped_put, last_beeped_take],
            outputs=[timer_reminder_md, last_beeped_put, last_beeped_take, timer_beep_html],
        )

    return demo


def launch_demo():
    """创建界面并启动服务（app.py 部署入口调用）。"""
    from config import SERVER_NAME, SERVER_PORT, GRADIO_SHARE
    demo = create_ui()
    demo.launch(
        server_name=SERVER_NAME,
        server_port=SERVER_PORT,
        share=GRADIO_SHARE,
        theme=gr.themes.Soft(primary_hue="orange"),
        css=_CSS,
        head=_HEAD_JS,
    )


if __name__ == "__main__":
    launch_demo()
