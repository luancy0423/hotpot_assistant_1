# -*- coding: utf-8 -*-
"""
统一应用状态（建议 4：AppState 单一事实来源）
所有业务状态集中在一个 dataclass，由单一 gr.State 持有，减少回调参数与数据流分散。
"""

from dataclasses import dataclass, field
from typing import List, Any, Optional


@dataclass
class AppState:
    """应用全局状态。"""
    ingredients: List[list] = field(default_factory=list)   # 每项 [name, time_val, portion]
    current_step: int = -1   # -1=首页 0=食材 1=偏好 2=方案 3=计时
    plan_data: Optional[dict] = None
    plan_text: str = ""          # 方案纯文本，用于复制/二维码
    drawer_open: bool = False
    timer_start_time: float = 0  # 开始吃饭时的 time.time()，0 表示未开始
    last_beeped_put: int = -1    # 计时器已播报的下锅秒数
    last_beeped_take: int = -1   # 计时器已播报的捞出秒数
    search_just_selected: bool = False  # 搜索下拉刚选中，避免 name 变更再次触发搜索
    # ── 暂停/恢复计时 ──
    timer_paused: bool = False          # 计时器是否处于暂停状态
    paused_elapsed: int = 0             # 暂停时冻结的已用秒数
    total_paused_duration: float = 0.0  # 累计暂停的总时长（秒），用于修正 elapsed
    pause_began_at: float = 0.0         # 本次暂停开始的 time.time()，0 表示未暂停
    # ── 剔除不计时的菜 ──
    excluded_ingredients: List[str] = field(default_factory=list)  # 不参与计时的食材名称列表

    def _clone(self, **overrides) -> "AppState":
        """用当前字段值创建新实例，overrides 中的 key 覆盖对应字段。"""
        from dataclasses import fields as _fields
        kw = {f.name: getattr(self, f.name) for f in _fields(self)}
        kw.update(overrides)
        return AppState(**kw)

    def with_ingredients(self, items: List[list]) -> "AppState":
        return self._clone(ingredients=items)

    def with_step(self, step: int) -> "AppState":
        return self._clone(current_step=step)

    def with_plan(self, plan_data: Optional[dict]) -> "AppState":
        return self._clone(plan_data=plan_data)

    def with_plan_text(self, plan_text: str) -> "AppState":
        return self._clone(plan_text=plan_text)

    def with_timer_start(self, start_time: float) -> "AppState":
        return self._clone(
            timer_start_time=start_time,
            last_beeped_put=-1,
            last_beeped_take=-1,
            timer_paused=False,
            paused_elapsed=0,
            total_paused_duration=0.0,
            pause_began_at=0.0,
        )

    def with_last_beeped(self, put_sec: int, take_sec: int) -> "AppState":
        return self._clone(last_beeped_put=put_sec, last_beeped_take=take_sec)

    def with_search_just_selected(self, value: bool) -> "AppState":
        return self._clone(search_just_selected=value)

    # ── 暂停 / 恢复 ──────────────────────────────────────────────

    def with_timer_paused(self, paused_elapsed: int, pause_began_at: float) -> "AppState":
        """冻结计时器：记录当前已过秒数和暂停开始时刻。"""
        return self._clone(
            timer_paused=True,
            paused_elapsed=paused_elapsed,
            pause_began_at=pause_began_at,
        )

    def with_timer_resumed(self, added_paused_duration: float) -> "AppState":
        """恢复计时器：把本次暂停持续时长累加到 total_paused_duration。"""
        return self._clone(
            timer_paused=False,
            paused_elapsed=0,
            pause_began_at=0.0,
            total_paused_duration=self.total_paused_duration + added_paused_duration,
        )

    # ── 剔除 / 恢复食材计时 ──────────────────────────────────────

    def with_excluded_ingredients(self, excluded: List[str]) -> "AppState":
        return self._clone(excluded_ingredients=list(excluded))

    def with_ingredient_excluded(self, name: str) -> "AppState":
        """将指定食材加入排除列表（去重）。"""
        new_list = list(self.excluded_ingredients)
        if name and name not in new_list:
            new_list.append(name)
        return self._clone(excluded_ingredients=new_list)

    def with_ingredient_included(self, name: str) -> "AppState":
        """将指定食材从排除列表移除。"""
        new_list = [n for n in self.excluded_ingredients if n != name]
        return self._clone(excluded_ingredients=new_list)


def initial_app_state() -> AppState:
    return AppState(
        ingredients=[],
        current_step=-1,
        plan_data=None,
        plan_text="",
        drawer_open=False,
        timer_start_time=0,
        last_beeped_put=-1,
        last_beeped_take=-1,
        search_just_selected=False,
        timer_paused=False,
        paused_elapsed=0,
        total_paused_duration=0.0,
        pause_began_at=0.0,
        excluded_ingredients=[],
    )
