# -*- coding: utf-8 -*-
"""
<<<<<<< Updated upstream
前端导航层
管理五个页面（首页/食材/偏好/方案/计时）的 step_state 状态机及可见性切换。
所有函数返回 (new_step, home_upd, step0_upd, step1_upd, step2_upd, step3_upd)。
=======
涮涮AI - 页面导航状态机
首页 / 步骤0 食材 / 步骤1 偏好 / 步骤2 方案 / 步骤3 计时的显隐与 step_state 更新。
>>>>>>> Stashed changes
"""

import gradio as gr

<<<<<<< Updated upstream
# step_state 取值约定：-1=首页  0=食材  1=偏好  2=方案  3=计时

_VIS_MAP = {
    -1: (True,  False, False, False, False),
     0: (False, True,  False, False, False),
     1: (False, False, True,  False, False),
     2: (False, False, False, True,  False),
     3: (False, False, False, False, True),
}


def _make(new_step: int):
    vis = _VIS_MAP.get(new_step, (True, False, False, False, False))
    return (new_step,) + tuple(gr.update(visible=v) for v in vis)


def nav_to_home():
    """直接跳回首页（step -1）。"""
    return _make(-1)


def nav_next_v4(step: int):
    """向后翻一页；首页→步骤0，其余步骤顺序递增。"""
    if step < 0:
        new = 0
    elif step < 3:
        new = step + 1
    else:
        new = step
    return _make(new)


def nav_prev_v4(step: int):
    """向前翻一页；步骤0→首页，首页保持首页。"""
    new = -1 if step <= 0 else step - 1
    return _make(new)


def nav_restart_v4(step: int):
    """重新开始 → 回首页。"""
    return nav_to_home()


def nav_back_timer_v4(step: int, start_time: float):
    """从计时页返回首页，同时清理内存缓存。"""
    from frontend.timer import cleanup_timer_state
    if start_time and start_time > 0:
        cleanup_timer_state(start_time)
    return nav_to_home()
=======
from frontend.timer import cleanup_timer_state


def nav_to_home():
    """回到首页（step_state=-1），显示 step_home，隐藏其他。"""
    return (
        -1,
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
    )


def nav_restart_v4(step):
    """重新开始 → 回到首页。"""
    return nav_to_home()


def nav_back_timer_v4(step, start_time):
    """从计时页返回首页，同时清理内存缓存。"""
    if start_time and start_time > 0:
        cleanup_timer_state(start_time)
    return nav_to_home()


def nav_next_v4(step):
    """下一步（含 step_home 输出版）。"""
    s = step
    if s < 0:
        new = 0
    elif s < 3:
        new = s + 1
    else:
        new = s
    _vis = {
        -1: (True, False, False, False, False),
        0: (False, True, False, False, False),
        1: (False, False, True, False, False),
        2: (False, False, False, True, False),
        3: (False, False, False, False, True),
    }.get(new, (False, True, False, False, False))
    return (new,) + tuple(gr.update(visible=v) for v in _vis)


def nav_prev_v4(step):
    """上一步（含 step_home 输出版）。"""
    s = step
    if s <= 0:
        new = -1
    else:
        new = s - 1
    _vis = {
        -1: (True, False, False, False, False),
        0: (False, True, False, False, False),
        1: (False, False, True, False, False),
        2: (False, False, False, True, False),
        3: (False, False, False, False, True),
    }.get(new, (True, False, False, False, False))
    return (new,) + tuple(gr.update(visible=v) for v in _vis)
>>>>>>> Stashed changes
