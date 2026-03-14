# -*- coding: utf-8 -*-
"""
涮涮AI - 计时器逻辑
tick 回调、TTS 预加载缓存、计时页 HTML 面板、语音播报与闪烁。
"""

import time
import threading
import re
from typing import Any, Optional, List, Tuple

from frontend import components
from frontend import tts

TIMER_PROMPT_DURATION_SEC = 10
TIMER_FLASH_DURATION_SEC = 1.0
TIMER_VOICE_KEEP_HTML_SEC = 8
TIMER_STATE_MAX_SESSIONS = 5

_tts_preload_cache = {}
_tts_preload_lock = threading.Lock()
_voice_timer_state_by_start = {}


def cleanup_timer_state(start_time: float) -> None:
    """结束计时时清理该 start_time 对应的缓存，并做 LRU 兜底。"""

    with _tts_preload_lock:
        for k in [k for k in _tts_preload_cache if k[0] == start_time]:
            del _tts_preload_cache[k]
        sessions = sorted({k[0] for k in _tts_preload_cache})
        while len(sessions) > TIMER_STATE_MAX_SESSIONS:

            oldest = sessions.pop(0)
            for k in [k for k in _tts_preload_cache if k[0] == oldest]:
                del _tts_preload_cache[k]
    _voice_timer_state_by_start.pop(start_time, None)
    if len(_voice_timer_state_by_start) > TIMER_STATE_MAX_SESSIONS:
        for k in sorted(_voice_timer_state_by_start)[:-TIMER_STATE_MAX_SESSIONS]:
            _voice_timer_state_by_start.pop(k, None)


def _ingredient_from_msg(msg: str) -> str:

    """从事件 message 字段提取食材名称（格式：…【名称】…）。"""
    if not msg:
        return ""
    m = re.search(r"【([^】]+)】", msg)
    return m.group(1) if m else msg


def _phrases_for_events_at_time(events: list, time_seconds: int) -> List[str]:
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


def _do_tts_preload_one(start_time: float, time_seconds: int, plan_data: dict) -> None:
    """预加载某一秒的 TTS，写入 _tts_preload_cache。"""
    if not plan_data or not start_time or time_seconds is None:
        return
    events = (plan_data.get("timeline") or {}).get("events") or []
    phrases = _phrases_for_events_at_time(events, time_seconds)
    if not phrases:
        return
    combined = "。".join(phrases)
    html = tts.tts_phrase_to_audio_html(combined)

    if html:
        with _tts_preload_lock:
            _tts_preload_cache[(start_time, time_seconds)] = html


def preload_all_tts_for_plan(start_time: float, plan_data: dict) -> None:
    """后台线程：根据方案时间线一次性生成所有「下锅/捞出」时间点的 TTS。"""

    if not plan_data or not start_time:
        return
    events = (plan_data.get("timeline") or {}).get("events") or []
    if not events:
        return
    unique_seconds = sorted(set(e.get("time_seconds") for e in events if e.get("time_seconds") is not None))
    for t in unique_seconds:
        _do_tts_preload_one(start_time, t, plan_data)


def _build_timer_html(
    elapsed: int,
    total_seconds: int,
    show_put: bool,
    show_take: bool,
    name_put: str,
    name_take: str,

    next_put_info: Optional[Tuple[int, str]],
    next_take_info: Optional[Tuple[int, str]],
    items: list,
) -> str:
    """生成计时页的富文本 HTML 面板。"""
    import html as _html
    m_e, s_e = elapsed // 60, elapsed % 60
    m_t, s_t = total_seconds // 60, total_seconds % 60
    pct = min(100, int(elapsed / max(total_seconds, 1) * 100)) if total_seconds > 0 else 0
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
    status_rows_html = ""
    if items:
        cumulative = 0
        for item in items:
            iname = item.get("ingredient_name", "")
            cook = item.get("cooking_seconds", 0)
            put_t = item.get("start_offset_seconds", cumulative)
            take_t = put_t + cook
            cumulative = max(cumulative, put_t) + cook
            if elapsed < put_t:
                dot, badge, bg = "#ccc", f"<span style='color:#bbb'>等待（{put_t - elapsed}秒后下锅）</span>", "#fafafa"
            elif elapsed < take_t:
                done_pct = min(100, int((elapsed - put_t) / max(cook, 1) * 100))
                dot = "#e65c00"
                badge = (f"<span style='color:#e65c00'>进行中，还需 {take_t - elapsed} 秒</span>"
                         f"<div style='margin-top:4px;height:4px;background:#f0e0d0;border-radius:4px;overflow:hidden'>"
                         f"<div style='width:{done_pct}%;height:100%;background:#e65c00;border-radius:4px'></div></div>")
                bg = "#fff8f0"
            else:
                dot, badge, bg = "#2e7d32", "<span style='color:#2e7d32;font-weight:600'>✓ 已捞出</span>", "#f0fff4"
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


def timer_tick(
    plan_data: Any,
    start_time: float,
    last_put_sec: Optional[int],
    last_take_sec: Optional[int],
    is_paused: bool = False,
    paused_elapsed: int = 0,
    total_paused_duration: float = 0.0,
    excluded_ingredients: Optional[List[str]] = None,
) -> Tuple[str, int, int, str]:
    """每秒调用：计算当前进度，返回 (display_html, new_put_sec, new_take_sec, voice_html_out)。
    
    新增参数：
        is_paused: 计时器是否处于暂停状态
        paused_elapsed: 暂停时冻结的已过秒数
        total_paused_duration: 累计暂停总时长（秒），用于修正 elapsed
        excluded_ingredients: 不参与计时的食材名称列表
    """
    if not plan_data or not start_time or start_time <= 0:
        return (
            "<p style='color:#bbb;text-align:center;padding:40px;font-size:.95em'>等待开始…</p>",
            last_put_sec or -1,
            last_take_sec or -1,
            "",
        )

    # ── 暂停时使用冻结的 elapsed ──
    if is_paused:
        elapsed = paused_elapsed
    else:
        elapsed = int(time.time() - start_time - total_paused_duration)

    excluded_set = set(excluded_ingredients or [])

    state = _voice_timer_state_by_start.setdefault(
        start_time, {"last_voice_html": "", "voice_played_at_elapsed": -1}
    )
    last_voice_html = state.get("last_voice_html") or ""
    voice_played_at_elapsed = state.get("voice_played_at_elapsed", -1) or -1

    timeline = plan_data.get("timeline") or {}
    total_sec = timeline.get("total_duration_seconds") or 0
    events = timeline.get("events") or []
    items = timeline.get("items") or []

    # ── 过滤掉被排除的食材 ──
    if excluded_set:
        events = [e for e in events if e.get("item_name", "") not in excluded_set]
        items = [it for it in items if it.get("ingredient_name", "") not in excluded_set]
        # 重新计算 total_sec（仅基于未排除的事件）
        if events:
            total_sec = max(e["time_seconds"] for e in events)
        else:
            total_sec = 0
    put_events = [e for e in events if e.get("action") == "下锅"]
    take_events = [e for e in events if e.get("action") in ("捞出", "捞起")]
    put_due = [e for e in put_events if e["time_seconds"] <= elapsed]
    take_due = [e for e in take_events if e["time_seconds"] <= elapsed]
    cur_put = put_due[-1] if put_due else None
    cur_take = take_due[-1] if take_due else None
    next_put = next((e for e in put_events if e["time_seconds"] > elapsed), None)
    next_take = next((e for e in take_events if e["time_seconds"] > elapsed), None)
    show_put = bool(cur_put and elapsed < cur_put["time_seconds"] + TIMER_PROMPT_DURATION_SEC)
    show_take = bool(cur_take and elapsed < cur_take["time_seconds"] + TIMER_PROMPT_DURATION_SEC)
    new_put_sec = cur_put["time_seconds"] if cur_put else (last_put_sec or -1)
    new_take_sec = cur_take["time_seconds"] if cur_take else (last_take_sec or -1)
    last_put_sec = last_put_sec or -1
    last_take_sec = last_take_sec or -1
    name_put = (_ingredient_from_msg(cur_put.get("message")) or cur_put.get("item_name", "")) if cur_put else ""
    name_take = (_ingredient_from_msg(cur_take.get("message")) or cur_take.get("item_name", "")) if cur_take else ""
    next_put_info = (next_put["time_seconds"] - elapsed, _ingredient_from_msg(next_put.get("message")) or next_put.get("item_name", "")) if next_put else None
    next_take_info = (next_take["time_seconds"] - elapsed, _ingredient_from_msg(next_take.get("message")) or next_take.get("item_name", "")) if next_take else None
    display_html = _build_timer_html(
        elapsed, total_sec, show_put, show_take,
        name_put, name_take, next_put_info, next_take_info, items,
    )
    # ── 暂停时在顶部叠加暂停提示，并抑制语音播报 ──
    if is_paused:
        pause_banner = (
            '<div style="text-align:center;padding:12px 16px;margin:0 16px 8px;'
            'border-radius:10px;background:#fff3cd;border:1.5px solid #ffc107;'
            'color:#856404;font-weight:700;font-size:1em;letter-spacing:1px">'
            '⏸ 已暂停</div>'
        )
        # 把暂停提示插到最外层 div 内部顶部
        insert_pos = display_html.find('>') + 1  # 找到最外层 <div ...> 的结束
        if insert_pos > 1:
            display_html = display_html[:insert_pos] + pause_banner + display_html[insert_pos:]
        # 暂停时不播放语音
        return display_html, new_put_sec, new_take_sec, ""

    voice_put_new = bool(cur_put and cur_put["time_seconds"] > last_put_sec)
    voice_take_new = bool(cur_take and cur_take["time_seconds"] > last_take_sec)
    play_voice = voice_put_new or voice_take_new
    voice_html_out = ""
    if play_voice:
        phrases = []
        if voice_put_new and cur_put:
            phrases.append(f"现在请下锅，{name_put}")
        if voice_take_new and cur_take:
            phrases.append(f"现在请捞出，{name_take}")
        if phrases:
            event_sec = (cur_put["time_seconds"] if voice_put_new and cur_put else
                        cur_take["time_seconds"] if voice_take_new and cur_take else None)

            if event_sec is not None:
                with _tts_preload_lock:
                    voice_html_out = (_tts_preload_cache.pop((start_time, event_sec), None) or "").strip()
            if not voice_html_out or voice_html_out == "None":
                voice_html_out = tts.tts_phrase_to_audio_html("。".join(phrases))
            if not voice_html_out and tts.BEEP_B64:
                voice_html_out = f'<audio autoplay><source src="data:audio/wav;base64,{tts.BEEP_B64}" type="audio/wav"></audio>'
        else:
            if tts.BEEP_B64:
                voice_html_out = f'<audio autoplay><source src="data:audio/wav;base64,{tts.BEEP_B64}" type="audio/wav"></audio>'
        voice_html_out = (voice_html_out or "") + components.flash_overlay_html(TIMER_FLASH_DURATION_SEC)
        _voice_timer_state_by_start[start_time] = {"last_voice_html": voice_html_out, "voice_played_at_elapsed": elapsed}
    else:
        if (last_voice_html and voice_played_at_elapsed >= 0 and
                (elapsed - voice_played_at_elapsed) < TIMER_VOICE_KEEP_HTML_SEC):
            voice_html_out = last_voice_html
        _voice_timer_state_by_start[start_time] = {"last_voice_html": last_voice_html or "", "voice_played_at_elapsed": voice_played_at_elapsed}

    return display_html, new_put_sec, new_take_sec, voice_html_out
