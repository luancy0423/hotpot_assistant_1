# -*- coding: utf-8 -*-
"""
前端导航层
管理五个页面（首页/食材/偏好/方案/计时），基于 AppState.current_step 与可见性切换。
所有函数接收 app_state，返回 (new_app_state, home_upd, step0_upd, step1_upd, step2_upd, step3_upd)。
"""

import gradio as gr

from frontend.state import AppState

# current_step: -1=首页  0=食材  1=偏好  2=方案  3=计时
_VIS_MAP = {
    -1: (True,  False, False, False, False),
     0: (False, True,  False, False, False),
     1: (False, False, True,  False, False),
     2: (False, False, False, True,  False),
     3: (False, False, False, False, True),
}


def _make(app_state: AppState, new_step: int):
    vis = _VIS_MAP.get(new_step, (True, False, False, False, False))
    return (app_state.with_step(new_step),) + tuple(gr.update(visible=v) for v in vis)


def nav_to_home(app_state: AppState):
    """直接跳回首页（step -1）。"""
    return _make(app_state, -1)


def nav_next_v4(app_state: AppState):
    """向后翻一页；首页→步骤0，其余步骤顺序递增。"""
    step = app_state.current_step
    if step < 0:
        new = 0
    elif step < 3:
        new = step + 1
    else:
        new = step
    return _make(app_state, new)


def nav_prev_v4(app_state: AppState):
    """向前翻一页；步骤0→首页，首页保持首页。"""
    step = app_state.current_step
    new = -1 if step <= 0 else step - 1
    return _make(app_state, new)


def nav_restart_v4(app_state: AppState):
    """重新开始 → 回首页。"""
    return nav_to_home(app_state)


def nav_back_timer_v4(app_state: AppState):
    """从计时页返回首页，同时清理该次计时的内存缓存。"""
    from frontend.timer import cleanup_timer_state
    if app_state and getattr(app_state, "timer_start_time", 0) and app_state.timer_start_time > 0:
        cleanup_timer_state(app_state.timer_start_time)
    return nav_to_home(app_state)
