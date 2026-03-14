# -*- coding: utf-8 -*-
"""
前端计时器层
管理吃饭计时的全局状态、每秒 tick 回调、TTS 预加载缓存，
以及计时面板的 HTML 渲染。
"""

import html as _html
import re
import threading
import time
from typing import Optional, Tuple

# ── 常量 ────────────────────────────────────────────────────────
TIMER_PROMPT_DURATION_SEC  = 10   # 「下锅/捞出」提示卡片显示秒数
TIMER_FLASH_DURATION_SEC   = 1    # 屏幕闪烁提醒时长（秒）
TIMER_VOICE_KEEP_HTML_SEC  = 8    # 语音播放后保留 HTML 秒数（防止下一 tick 截断音频）
_TIMER_STATE_MAX_SESSIONS  = 5    # 最多同时保留的 session 数（LRU 防内存泄漏）

# ── 全局缓存（进程级，Gradio 单进程多 session 共享）────────────
_tts_preload_cache: dict   = {}          # key=(start_time, time_seconds), value=audio_html
_tts_preload_lock          = threading.Lock()
_voice_timer_state_by_start: dict = {}  # key=start_time, value={"last_voice_html":..., "voice_played_at_elapsed":...}


# ── 缓存清理 ─────────────────────────────────────────────────────

def cleanup_timer_state(start_time: float) -> None:
    """结束计时时清理该 session 的所有缓存，并做 LRU 兜底。"""
    with _tts_preload_lock:
        for k in [k for k in _tts_preload_cache if k[0] == start_time]:
            del _tts_preload_cache[k]
        sessions = sorted({k[0] for k in _tts_preload_cache})
        while len(sessions) > _TIMER_STATE_MAX_SESSIONS:
            oldest = sessions.pop(0)
            for k in [k for k in _tts_preload_cache if k[0] == oldest]:
                del _tts_preload_cache[k]
    _voice_timer_state_by_start.pop(start_time, None)
    if len(_voice_timer_state_by_start) > _TIMER_STATE_MAX_SESSIONS:
        for k in sorted(_voice_timer_state_by_start)[:-_TIMER_STATE_MAX_SESSIONS]:
            _voice_timer_state_by_start.pop(k, None)


# ── 工具函数 ─────────────────────────────────────────────────────

def ingredient_from_msg(msg: str) -> str:
    """从事件 message 字段提取食材名称（格式：…【名称】…）。"""
    if not msg:
        return ""
    m = re.search(r"【([^】]+)】", msg)
    return m.group(1) if m else msg


def flash_overlay_html() -> str:
    """1 秒淡出的全屏橙色闪烁 overlay，用于下锅/捞出到点提醒。"""
    return (
        '<div class="hotpot-flash-overlay" style="'
        "position:fixed;inset:0;z-index:9999;pointer-events:none;"
        "background:rgba(255,140,0,0.35);"
        f"animation:hotpot-flash-fade {TIMER_FLASH_DURATION_SEC}s ease-out forwards;"
        '"></div>'
        "<style>@keyframes hotpot-flash-fade { 0% { opacity: 1; } 100% { opacity: 0; } }</style>"
    )


def phrases_for_events_at_time(events: list, time_seconds: int) -> list:
    """从事件列表中取出指定秒数的「下锅/捞出」，生成播报句列表。"""
    phrases = []
    for e in events:
        if e.get("time_seconds") != time_seconds:
            continue
        action = e.get("action")
        name = ingredient_from_msg(e.get("message")) or e.get("item_name") or e.get("message", "")
        if action == "下锅":
            phrases.append(f"现在请下锅，{name}")
        elif action in ("捞出", "捞起"):
            phrases.append(f"现在请捞出，{name}")
    return phrases


# ── TTS 预加载 ───────────────────────────────────────────────────

def do_tts_preload_one(start_time: float, time_seconds: int, plan_data: dict) -> None:
    """预合成指定时间点的语音，写入 _tts_preload_cache。"""
    from frontend.tts import tts_phrase_to_audio_html
    if not plan_data or not start_time or time_seconds is None:
        return
    events  = (plan_data.get("timeline") or {}).get("events") or []
    phrases = phrases_for_events_at_time(events, time_seconds)
    if not phrases:
        return
    html = tts_phrase_to_audio_html("。".join(phrases))
    if html:
        with _tts_preload_lock:
            _tts_preload_cache[(start_time, time_seconds)] = html


def preload_all_tts_for_plan(start_time: float, plan_data: dict) -> None:
    """
    后台线程：一次性为方案所有「下锅/捞出」时间点预生成 TTS 并缓存。
    点击「开始吃饭」时调用，计时过程中到点直接播缓存，无延迟。
    """
    if not plan_data or not start_time:
        return
    events = (plan_data.get("timeline") or {}).get("events") or []
    if not events:
        return
    unique_seconds = sorted(set(e.get("time_seconds") for e in events if e.get("time_seconds") is not None))
    for t in unique_seconds:
        do_tts_preload_one(start_time, t, plan_data)


# ── 计时面板 HTML ────────────────────────────────────────────────

def build_timer_html(
    elapsed: int, total_seconds: int,
    show_put: bool, show_take: bool,
    name_put: str, name_take: str,
    next_put_info: Optional[Tuple[int, str]],
    next_take_info: Optional[Tuple[int, str]],
    items: list,
) -> str:
    """生成计时页富文本 HTML：大字时钟、进度条、操作卡片、预告、食材状态列表。"""
    m_e, s_e = elapsed // 60, elapsed % 60
    m_t, s_t = total_seconds // 60, total_seconds % 60
    pct       = min(100, int(elapsed / max(total_seconds, 1) * 100)) if total_seconds > 0 else 0
    bar_color = "#e65c00" if pct < 85 else "#c0392b"

    clock = f"""
    <div style="text-align:center;padding:18px 0 6px">
      <div style="font-size:3em;font-weight:700;letter-spacing:2px;color:#e65c00;line-height:1.1">
        {m_e:02d}<span style="opacity:.55;font-size:.65em">分</span>{s_e:02d}<span style="opacity:.55;font-size:.65em">秒</span>
      </div>
      <div style="font-size:.82em;color:#999;margin-top:4px">总时长 {m_t}分{s_t:02d}秒</div>
    </div>"""

    progress = f"""
    <div style="margin:4px 20px 4px">
      <div style="background:#f0f0f0;border-radius:8px;height:10px;overflow:hidden">
        <div style="width:{pct}%;height:100%;background:{bar_color};border-radius:8px;transition:width .9s ease"></div>
      </div>
    </div>
    <div style="text-align:center;font-size:.78em;color:#bbb;margin-bottom:12px">{pct}% 完成</div>"""

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

    status_rows = ""
    if items:
        cumulative = 0
        for item in items:
            iname  = item.get("ingredient_name", "")
            cook   = item.get("cooking_seconds", 0)
            put_t  = item.get("start_offset_seconds", cumulative)
            take_t = put_t + cook
            cumulative = max(cumulative, put_t) + cook
            if elapsed < put_t:
                dot, bg = "#ccc", "#fafafa"
                badge = f"<span style='color:#bbb'>等待（{put_t - elapsed}秒后下锅）</span>"
            elif elapsed < take_t:
                pct2 = min(100, int((elapsed - put_t) / max(cook, 1) * 100))
                dot, bg = "#e65c00", "#fff8f0"
                badge = (f"<span style='color:#e65c00'>进行中，还需 {take_t - elapsed} 秒</span>"
                         f"<div style='margin-top:4px;height:4px;background:#f0e0d0;border-radius:4px;overflow:hidden'>"
                         f"<div style='width:{pct2}%;height:100%;background:#e65c00;border-radius:4px'></div></div>")
            else:
                dot, bg = "#2e7d32", "#f0fff4"
                badge = "<span style='color:#2e7d32;font-weight:600'>✓ 已捞出</span>"
            status_rows += f"""
            <tr style="background:{bg}">
              <td style="padding:7px 10px;font-size:.88em;font-weight:600;white-space:nowrap">
                <span style="display:inline-block;width:8px;height:8px;border-radius:50%;
                             background:{dot};margin-right:7px;vertical-align:middle"></span>
                {_html.escape(iname)}
              </td>
              <td style="padding:7px 10px;font-size:.82em;width:100%">{badge}</td>
            </tr>"""

    status_block = ""
    if status_rows:
        status_block = f"""
        <div style="margin:8px 16px 18px;border-radius:10px;overflow:hidden;
                    border:1px solid #eee;box-shadow:0 1px 4px rgba(0,0,0,.05)">
          <div style="padding:7px 12px;background:#f5f5f5;
                      font-size:.73em;font-weight:700;color:#999;letter-spacing:.5px">食材状态</div>
          <table style="width:100%;border-collapse:collapse">{status_rows}</table>
        </div>"""

    return f"""
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
                max-width:560px;margin:0 auto;border-radius:16px;overflow:hidden;
                border:1px solid #ffe0b2;background:#fff;
                box-shadow:0 4px 18px rgba(230,92,0,.10)">
      {clock}{progress}{cards}{upcoming}{status_block}
    </div>"""


# ── 每秒 tick 回调 ───────────────────────────────────────────────

def timer_tick(plan_data, start_time, last_put_sec, last_take_sec):
    """
    Gradio Timer 每秒调用：计算当前进度，返回
    (display_html, new_put_sec, new_take_sec, voice_html)。
    """
    from frontend.tts import BEEP_B64, tts_phrase_to_audio_html

    if not plan_data or not start_time or start_time <= 0:
        return (
            "<p style='color:#bbb;text-align:center;padding:40px;font-size:.95em'>等待开始…</p>",
            last_put_sec or -1, last_take_sec or -1, "",
        )

    state = _voice_timer_state_by_start.setdefault(
        start_time, {"last_voice_html": "", "voice_played_at_elapsed": -1}
    )
    last_voice_html          = state.get("last_voice_html") or ""
    voice_played_at_elapsed  = state.get("voice_played_at_elapsed", -1) or -1

    elapsed   = int(time.time() - start_time)
    timeline  = plan_data.get("timeline") or {}
    total_sec = timeline.get("total_duration_seconds") or 0
    events    = timeline.get("events") or []
    items     = timeline.get("items") or []

    put_events  = [e for e in events if e.get("action") == "下锅"]
    take_events = [e for e in events if e.get("action") in ("捞出", "捞起")]
    put_due     = [e for e in put_events  if e["time_seconds"] <= elapsed]
    take_due    = [e for e in take_events if e["time_seconds"] <= elapsed]
    cur_put     = put_due[-1]  if put_due  else None
    cur_take    = take_due[-1] if take_due else None
    next_put    = next((e for e in put_events  if e["time_seconds"] > elapsed), None)
    next_take   = next((e for e in take_events if e["time_seconds"] > elapsed), None)

    show_put   = bool(cur_put  and elapsed < cur_put["time_seconds"]  + TIMER_PROMPT_DURATION_SEC)
    show_take  = bool(cur_take and elapsed < cur_take["time_seconds"] + TIMER_PROMPT_DURATION_SEC)
    new_put_sec  = cur_put["time_seconds"]  if cur_put  else (last_put_sec  or -1)
    new_take_sec = cur_take["time_seconds"] if cur_take else (last_take_sec or -1)
    last_put_sec  = last_put_sec  or -1
    last_take_sec = last_take_sec or -1

    name_put  = (ingredient_from_msg(cur_put.get("message"))  or cur_put.get("item_name", ""))  if cur_put  else ""
    name_take = (ingredient_from_msg(cur_take.get("message")) or cur_take.get("item_name", "")) if cur_take else ""

    next_put_info  = ((next_put["time_seconds"]  - elapsed,
                       ingredient_from_msg(next_put.get("message"))  or next_put.get("item_name", ""))
                      if next_put  else None)
    next_take_info = ((next_take["time_seconds"] - elapsed,
                       ingredient_from_msg(next_take.get("message")) or next_take.get("item_name", ""))
                      if next_take else None)

    display_html = build_timer_html(
        elapsed, total_sec, show_put, show_take,
        name_put, name_take, next_put_info, next_take_info, items,
    )

    # ── 语音播报 ──────────────────────────────────────────────────
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
                voice_html_out = tts_phrase_to_audio_html("。".join(phrases))
            if not voice_html_out and BEEP_B64:
                voice_html_out = f'<audio autoplay><source src="data:audio/wav;base64,{BEEP_B64}" type="audio/wav"></audio>'
        else:
            if BEEP_B64:
                voice_html_out = f'<audio autoplay><source src="data:audio/wav;base64,{BEEP_B64}" type="audio/wav"></audio>'
        voice_html_out = (voice_html_out or "") + flash_overlay_html()
        _voice_timer_state_by_start[start_time] = {"last_voice_html": voice_html_out, "voice_played_at_elapsed": elapsed}
    else:
        if (last_voice_html and voice_played_at_elapsed >= 0
                and (elapsed - voice_played_at_elapsed) < TIMER_VOICE_KEEP_HTML_SEC):
            voice_html_out = last_voice_html
        _voice_timer_state_by_start[start_time] = {
            "last_voice_html": last_voice_html or "", "voice_played_at_elapsed": voice_played_at_elapsed
        }

    return display_html, new_put_sec, new_take_sec, voice_html_out
