# -*- coding: utf-8 -*-
"""
前端 UI 层（四大支柱：声明式布局 + 统一状态 + 样式分离 + 响应式）
只负责：① 用 Gradio 声明所有组件  ② 绑定事件到 handlers/nav/timer 的回调函数。
"""

import html as _html
import os
import gradio as gr

from config import BROTH_CHOICES, TEXTURE_CHOICES, MODE_CHOICES
from frontend.state import AppState, initial_app_state
from frontend.components import (
    homepage_html, homepage_action_card_html, step_header_html,
    basket_bar_shell, boiling_result_html, add_ingredient_row,
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

# ── 样式表（支柱三：从 assets/style.css 加载）─────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CSS_PATH = os.path.join(_ROOT, "assets", "style.css")
if os.path.isfile(_CSS_PATH):
    with open(_CSS_PATH, "r", encoding="utf-8") as _f:
        _CSS = _f.read()
else:
    _CSS = "/* fallback */\nbody{ font-family: sans-serif; }\n.gradio-container{ max-width: 450px; margin: 0 auto; }\n"

# 全局原生 JavaScript 控制器（支柱一：JS 仅负责抽屉升降动画）
_HEAD_JS = """
<script>
  // 健壮的元素查找器：处理 Gradio 可能存在的 iframe 嵌套
  function safeFind(selector) {
    var el = document.querySelector(selector);
    if (el) return el;
    var frames = document.querySelectorAll('iframe');
    for (var i = 0; i < frames.length; i++) {
      try {
        var d = frames[i].contentDocument || frames[i].contentWindow.document;
        el = d.querySelector(selector);
        if (el) return el;
      } catch (e) {}
    }
    return null;
  }

  window.shuaiToggleDrawer = function(show) {
    var overlay = safeFind('#shuai-global-overlay');
    var drawer = safeFind('#drawer-fixed-container');
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
      var btn = safeFind('#btn-next-in-bar button');
      if (btn) btn.click();
    }, 150);
  };

</script>
"""

# ── 主界面构建 ───────────────────────────────────────────────────

def create_ui():
    """
    构建完整的 Gradio 多页应用。
    """
    with gr.Blocks(title="涮涮AI - 智能火锅助手") as demo:
        gr.HTML('<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700;900'
                '&family=Noto+Sans+SC:wght@300;400;500&display=swap" rel="stylesheet">')

        # ── State（建议 4：单一 app_state，数据流一目了然）────────────────────
        app_state = gr.State(initial_app_state())

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

            with gr.Column(elem_id="ing-card-wrap", elem_classes=["ing-card-wrap"]):
                with gr.Group(elem_id="ing-card-group"):
                    with gr.Row(elem_id="ing-input-top"):
                        with gr.Column(scale=3, elem_id="ing-text-col"):
                            ingredient_name_input = gr.Textbox(label="🖊 食材名称", placeholder="如：毛肚、肥牛", lines=1, elem_id="ing-name-tb")
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
                            voice_input   = gr.Audio(label="🎤 语音", sources=["microphone", "upload"], type="filepath")
                            btn_voice     = gr.Button("识别语音", size="sm", elem_id="btn-voice-rec")
                            voice_status  = gr.Markdown("", visible=True)
                        with gr.Column(scale=1, elem_id="ing-img-col"):
                            image_input   = gr.Image(label="📷 识图", type="filepath", sources=["upload"])
                            btn_image     = gr.Button("识图填入", size="sm", elem_id="btn-image-rec")
                            image_status  = gr.Markdown("", visible=True)

            merchant_status = gr.Markdown("", visible=True, elem_id="merchant-status")
            btn_merchant    = gr.Button("🔗 一键接入商家点餐系统", size="sm", variant="secondary", elem_id="btn-merchant")

            with gr.Row(elem_id="step0-next-row"):
                gr.HTML("")
                btn_next_visible = gr.Button("下一步 ›", variant="primary", elem_id="btn-next-visible")

            # 底部悬浮栏（仅外壳，由 basket_bar_shell 提供）
            with gr.Row(elem_id="basket-bar-row"):
                basket_bar_html_comp = gr.HTML(value=basket_bar_shell(0), elem_id="basket-bar-html")
                btn_next_bar         = gr.Button("下一步 ›", variant="primary", elem_id="btn-next-in-bar")

            # 抽屉：原生 Column + @gr.render（支柱一：声明式，删除为原生 gr.Button）
            with gr.Column(elem_id="drawer-fixed-container"):
                gr.HTML('<div class="handle"></div>')
                gr.HTML(
                    '<div class="drawer-header-row">'
                    '<span class="drawer-title">已选食材</span>'
                    '<button type="button" class="drawer-close-btn" onclick="window.shuaiToggleDrawer(false)" title="关闭">✕ 关闭</button>'
                    '</div>'
                )
                with gr.Column(elem_id="drawer-list-wrap"):
                    @gr.render(inputs=[app_state])
                    def render_cart(state):
                        items = (state or initial_app_state()).ingredients
                        if not items:
                            gr.Markdown("购物车是空的哦~", elem_classes=["drawer-empty-msg"])
                            return
                        for i, item in enumerate(items):
                            name = (item[0] if item else "") or ""
                            if not name:
                                continue
                            t_val = item[1] if len(item) > 1 else None
                            portion = int(item[2]) if len(item) > 2 and item[2] else 1
                            try:
                                t = int(float(t_val)) if t_val and str(t_val).strip() not in ("", "0", "0.0") else 0
                            except (TypeError, ValueError):
                                t = 0
                            t_disp = f"{t}秒" if t > 0 else "库默认"
                            with gr.Row(elem_classes=["cart-row", "drawer-item-row"]):
                                gr.Markdown(f"**{_html.escape(str(name))}**\n{t_disp} · {portion}份")
                                del_btn = gr.Button("✕", elem_classes=["drawer-del-btn-native", "del-icon"], scale=0)
                                def make_delete(index):
                                    def delete_item(s):
                                        s = s or initial_app_state()
                                        new_ing = list(s.ingredients)
                                        if 0 <= index < len(new_ing):
                                            new_ing.pop(index)
                                        new_s = s.with_ingredients(new_ing)
                                        return new_s, basket_bar_shell(len(new_ing))
                                    return delete_item
                                del_btn.click(make_delete(i), inputs=[app_state], outputs=[app_state, basket_bar_html_comp])
                btn_next_in_drawer = gr.Button("确认方案 ›", variant="primary", elem_id="btn-next-in-drawer")

        # ══════════════════════════════════════════════════════════
        # 步骤2：锅底与偏好
        # ══════════════════════════════════════════════════════════
        step1 = gr.Column(visible=False, elem_id="page-step1")
        with step1:
            gr.HTML(step_header_html("第二步", "选择你的口味"))
            broth_acc = gr.Accordion("🍲 锅底类型", open=True, elem_classes=["pref-acc", "pref-acc--hero"])
            with broth_acc:
                broth_dd = gr.Radio(choices=[t for t, _ in BROTH_CHOICES], value="麻辣红汤", label="", show_label=False, elem_classes=["pref-radio"], elem_id="pref-broth")
            texture_acc = gr.Accordion("🌶 口感偏好", open=True, elem_classes=["pref-acc"])
            with texture_acc:
                texture_dd = gr.Radio(choices=[t for t, _ in TEXTURE_CHOICES], value="标准", label="", show_label=False, elem_classes=["pref-radio"], elem_id="pref-texture")
            mode_acc = gr.Accordion("👤 用户模式", open=True, elem_classes=["pref-acc"])
            with mode_acc:
                mode_dd = gr.Radio(choices=[t for t, _ in MODE_CHOICES], value="普通", label="", show_label=False, elem_classes=["pref-radio"], elem_id="pref-mode")
            with gr.Row(elem_id="pref-half-row"):
                with gr.Column():
                    allergen_acc = gr.Accordion("⚠️ 过敏原", open=False, elem_classes=["pref-acc"])
                    with allergen_acc:
                        allergen_input = gr.Textbox(label="", placeholder="如：虾、鱼", lines=1, show_label=False, elem_id="pref-allergen")
                with gr.Column():
                    people_acc = gr.Accordion("👥 就餐人数", open=False, elem_classes=["pref-acc"])
                    with people_acc:
                        num_people_input = gr.Number(label="", value=2, minimum=1, maximum=99, step=1, precision=0, show_label=False, elem_id="pref-people")
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
                output_md = gr.Markdown("方案将显示在此。", label="")
            with gr.Row(elem_id="share-row"):
                btn_copy_plan = gr.Button("📋 复制方案文字", size="sm", variant="secondary")
                btn_gen_qr    = gr.Button("📱 生成分享二维码", size="sm", variant="secondary")
            copy_status_html = gr.HTML("", elem_id="copy-status-html")
            qr_html          = gr.HTML("", elem_id="qr-display-html")
            gr.HTML('<div class="eating-btn-wrap">')
            btn_start_eating = gr.Button("开始\n吃饭", variant="primary", elem_id="btn-start-eating")
            gr.HTML('</div>')
            with gr.Row(elem_id="step2-nav-row"):
                btn_restart = gr.Button("↩ 重新开始")
                btn_prev2   = gr.Button("← 上一步")

        # ══════════════════════════════════════════════════════════
        # 步骤4：吃饭计时
        # ══════════════════════════════════════════════════════════
        step3 = gr.Column(visible=False, elem_id="page-step3")
        with step3:
            gr.HTML(step_header_html("", "🍲 吃饭计时", "shuai-step-bar--timer"))
            timer_reminder_md = gr.HTML("<p style='color:#bbb;text-align:center;padding:40px;font-size:.95em'>等待开始…</p>")
            timer_beep_html = gr.HTML("")
            timer_bottom_md = gr.Markdown("")
            gr.HTML('<div class="shuai-sec-sep" style="margin:10px 0 4px">📷 开锅检测</div>')
            with gr.Group(elem_id="boiling-detect-group"):
                boiling_image      = gr.Image(label="拍摄 / 上传锅底照片", sources=["webcam", "upload"], type="filepath", height=180)
                btn_detect_boiling = gr.Button("🔍 检测是否开锅", variant="primary", size="sm")
                boiling_result     = gr.HTML("")
            btn_back_from_timer = gr.Button("结束计时，返回首页")

        # ══════════════════════════════════════════════════════════
        # 后端交互与数据流绑定
        # ══════════════════════════════════════════════════════════
        _nav_outputs = [app_state, step_home, step0, step1, step2, step3]

        def _enter_step0(s):
            st = s if isinstance(s, AppState) else initial_app_state()
            return (st.with_step(0), gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False))
        btn_enter.click(fn=_enter_step0, inputs=[app_state], outputs=_nav_outputs)

        def _on_name_change(name_val, s):
            st = s or initial_app_state()
            try:
                if getattr(st, "search_just_selected", False):
                    return gr.update(), gr.update(), st.with_search_just_selected(False)
                choices = search_ingredients_for_dropdown(name_val)
                hint    = ingredient_lookup_hint(name_val, None)
                return gr.update(choices=choices, value=None), hint, st.with_search_just_selected(False)
            except Exception:
                return gr.update(choices=[], value=None), "", st
        ingredient_name_input.change(fn=_on_name_change, inputs=[ingredient_name_input, app_state], outputs=[ingredient_search_dd, ingredient_default_hint, app_state])

        ingredient_time_input.change(fn=lambda n, t: ingredient_lookup_hint(n, t), inputs=[ingredient_name_input, ingredient_time_input], outputs=[ingredient_default_hint])

        def _on_search_select(v, s):
            st = s or initial_app_state()
            try:
                if v and str(v).strip():
                    return str(v).strip(), gr.update(choices=[], value=None), st.with_search_just_selected(True)
                return gr.update(), gr.update(choices=[], value=None), st.with_search_just_selected(False)
            except Exception:
                return gr.update(), gr.update(), st
        ingredient_search_dd.change(fn=_on_search_select, inputs=[ingredient_search_dd, app_state], outputs=[ingredient_name_input, ingredient_search_dd, app_state])

        # 添加食材：更新 app_state.ingredients 与外壳数量
        def _add_v4(name, t, p, s):
            s = s or initial_app_state()
            try:
                new_list, _, _, nt, np_, _, _ = add_ingredient_row(name, t, p, s.ingredients)
                new_s = s.with_ingredients(new_list)
                return (new_s, "", nt, np_, "", basket_bar_shell(len(new_list)))
            except Exception as e:
                return (s, f"❌ 错误：{e}", 0, 1, "", basket_bar_shell(len(s.ingredients)))

        btn_add_row.click(fn=_add_v4, inputs=[ingredient_name_input, ingredient_time_input, ingredient_portion_input, app_state],
                          outputs=[app_state, ingredient_name_input, ingredient_time_input, ingredient_portion_input, ingredient_default_hint, basket_bar_html_comp])
        btn_reject_input.click(fn=lambda: ("", 0, 1, ""), inputs=[], outputs=[ingredient_name_input, ingredient_time_input, ingredient_portion_input, ingredient_default_hint])

        def _img_v4(img, s):
            s = s or initial_app_state()
            try:
                new_list, _, status, _ = image_to_ingredients(img, s.ingredients)
                new_s = s.with_ingredients(new_list)
                return (new_s, status, basket_bar_shell(len(new_list)))
            except Exception as e:
                return (s, f"❌ {e}", basket_bar_shell(len(s.ingredients)))
        btn_image.click(fn=_img_v4, inputs=[image_input, app_state], outputs=[app_state, image_status, basket_bar_html_comp])

        def _voice_v4(audio, s):
            s = s or initial_app_state()
            try:
                new_list, _, status, _ = voice_to_ingredients(audio, s.ingredients)
                new_s = s.with_ingredients(new_list)
                return (new_s, status, basket_bar_shell(len(new_list)))
            except Exception as e:
                return (s, f"❌ {e}", basket_bar_shell(len(s.ingredients)))
        btn_voice.click(fn=_voice_v4, inputs=[voice_input, app_state], outputs=[app_state, voice_status, basket_bar_html_comp])

        def _merchant_v4(s):
            s = s or initial_app_state()
            return (s, "⚠️ 暂未适配商家点餐系统，敬请期待。", basket_bar_shell(len(s.ingredients)))
        btn_merchant.click(fn=_merchant_v4, inputs=[app_state], outputs=[app_state, merchant_status, basket_bar_html_comp])

        btn_next_bar.click(fn=nav_next_v4, inputs=[app_state], outputs=_nav_outputs)
        btn_next_visible.click(fn=nav_next_v4, inputs=[app_state], outputs=_nav_outputs)
        btn_next_in_drawer.click(fn=nav_next_v4, inputs=[app_state], outputs=_nav_outputs)

        broth_dd.change(fn=lambda v: gr.update(label=f"🍲 锅底类型　✓ {v}"), inputs=[broth_dd], outputs=[broth_acc])
        texture_dd.change(fn=lambda v: gr.update(label=f"🌶 口感偏好　✓ {v}"), inputs=[texture_dd], outputs=[texture_acc])
        mode_dd.change(fn=lambda v: gr.update(label=f"👤 用户模式　✓ {v}"), inputs=[mode_dd], outputs=[mode_acc])
        allergen_input.change(fn=lambda v: gr.update(label=f"⚠️ 过敏原　{v.strip() or '无'}"), inputs=[allergen_input], outputs=[allergen_acc])
        num_people_input.change(fn=lambda v: gr.update(label=f"👥 就餐人数　{int(v or 2)}人"), inputs=[num_people_input], outputs=[people_acc])

        def _load_pref_v4():
            broth, texture, mode, allergen, status = load_preference_ui()
            return (broth, texture, mode, allergen, 2, status,
                    gr.update(label=f"🍲 锅底类型　✓ {broth}"), gr.update(label=f"🌶 口感偏好　✓ {texture}"),
                    gr.update(label=f"👤 用户模式　✓ {mode}"), gr.update(label=f"⚠️ 过敏原　{allergen.strip() or '无'}"))
        load_pref_btn.click(fn=_load_pref_v4, inputs=[], outputs=[broth_dd, texture_dd, mode_dd, allergen_input, num_people_input, pref_status, broth_acc, texture_acc, mode_acc, allergen_acc])

        btn_prev.click(fn=nav_prev_v4, inputs=[app_state], outputs=_nav_outputs)

        btn_generate.click(fn=show_generating, inputs=[app_state], outputs=[output_md, step0, step1, step2, step3, result_status, app_state]
        ).then(fn=generate_and_go, inputs=[app_state, broth_dd, texture_dd, mode_dd, allergen_input, num_people_input],
               outputs=[output_md, app_state, step0, step1, step2, step3, result_status])

        def _copy_plan_from_state(s):
            return copy_plan_html(getattr(s, "plan_text", "") or "" if s else "")
        def _qr_from_state(s):
            return generate_qr_html(getattr(s, "plan_text", "") or "" if s else "")
        btn_copy_plan.click(fn=_copy_plan_from_state, inputs=[app_state], outputs=[copy_status_html])
        btn_gen_qr.click(fn=_qr_from_state, inputs=[app_state], outputs=[qr_html])
        btn_restart.click(fn=nav_restart_v4, inputs=[app_state], outputs=_nav_outputs)
        btn_prev2.click(fn=nav_prev_v4, inputs=[app_state], outputs=_nav_outputs)
        btn_start_eating.click(fn=start_eating, inputs=[app_state], outputs=[app_state, step0, step1, step2, step3, timer_bottom_md, timer_reminder_md, timer_beep_html])

        def _do_detect_boiling(img_path):
            import os as _os
            if not img_path or not _os.path.isfile(str(img_path or "")): return boiling_result_html("⚠️", "未沸", "请先拍摄或上传照片", "")
            try:
                with open(img_path, "rb") as f: img_bytes = f.read()
            except Exception as e: return boiling_result_html("❌", "无法判断", f"读取失败：{e}", "")
            resp = api.detect_boiling(image_data=img_bytes, mime_type="image/png" if str(img_path).endswith(".png") else "image/jpeg")
            if not resp.success: return boiling_result_html("❌", "无法判断", f"检测失败：{resp.error}", "")
            d = resp.data
            icon = {"沸腾": "🔥", "微沸": "♨️", "未沸": "⏳", "无法判断": "❓"}.get(d.get("stage", ""), "❓")
            return boiling_result_html(icon, d.get("stage", ""), d.get("description", ""), d.get("advice", ""))
        btn_detect_boiling.click(fn=_do_detect_boiling, inputs=[boiling_image], outputs=[boiling_result])

        def _timer_tick_wrapper(s):
            st = s or initial_app_state()
            plan = st.plan_data if hasattr(st, "plan_data") else None
            start = getattr(st, "timer_start_time", 0) or 0
            put = getattr(st, "last_beeped_put", -1) or -1
            take = getattr(st, "last_beeped_take", -1) or -1
            reminder, new_put, new_take, beep = timer_tick(plan, start, put, take)
            new_st = st.with_last_beeped(new_put, new_take)
            return new_st, reminder, beep
        btn_back_from_timer.click(fn=nav_back_timer_v4, inputs=[app_state], outputs=_nav_outputs)
        gr.Timer(value=1).tick(fn=_timer_tick_wrapper, inputs=[app_state], outputs=[app_state, timer_reminder_md, timer_beep_html])

    return demo


def launch_demo():
    """创建界面并启动服务（app.py 部署入口调用）。"""
    from config import SERVER_NAME, SERVER_PORT, GRADIO_SHARE
    demo = create_ui()
    # 主题仅为 Gradio 组件默认高亮色，实际颜色以 assets/style.css 中 :root 变量为准
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
