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

    def with_ingredients(self, items: List[list]) -> "AppState":
        return AppState(
            ingredients=items,
            current_step=self.current_step,
            plan_data=self.plan_data,
            plan_text=self.plan_text,
            drawer_open=self.drawer_open,
            timer_start_time=self.timer_start_time,
            last_beeped_put=self.last_beeped_put,
            last_beeped_take=self.last_beeped_take,
            search_just_selected=self.search_just_selected,
        )

    def with_step(self, step: int) -> "AppState":
        return AppState(
            ingredients=self.ingredients,
            current_step=step,
            plan_data=self.plan_data,
            plan_text=self.plan_text,
            drawer_open=self.drawer_open,
            timer_start_time=self.timer_start_time,
            last_beeped_put=self.last_beeped_put,
            last_beeped_take=self.last_beeped_take,
            search_just_selected=self.search_just_selected,
        )

    def with_plan(self, plan_data: Optional[dict]) -> "AppState":
        return AppState(
            ingredients=self.ingredients,
            current_step=self.current_step,
            plan_data=plan_data,
            plan_text=self.plan_text,
            drawer_open=self.drawer_open,
            timer_start_time=self.timer_start_time,
            last_beeped_put=self.last_beeped_put,
            last_beeped_take=self.last_beeped_take,
            search_just_selected=self.search_just_selected,
        )

    def with_plan_text(self, plan_text: str) -> "AppState":
        return AppState(
            ingredients=self.ingredients,
            current_step=self.current_step,
            plan_data=self.plan_data,
            plan_text=plan_text,
            drawer_open=self.drawer_open,
            timer_start_time=self.timer_start_time,
            last_beeped_put=self.last_beeped_put,
            last_beeped_take=self.last_beeped_take,
            search_just_selected=self.search_just_selected,
        )

    def with_timer_start(self, start_time: float) -> "AppState":
        return AppState(
            ingredients=self.ingredients,
            current_step=self.current_step,
            plan_data=self.plan_data,
            plan_text=self.plan_text,
            drawer_open=self.drawer_open,
            timer_start_time=start_time,
            last_beeped_put=-1,
            last_beeped_take=-1,
            search_just_selected=self.search_just_selected,
        )

    def with_last_beeped(self, put_sec: int, take_sec: int) -> "AppState":
        return AppState(
            ingredients=self.ingredients,
            current_step=self.current_step,
            plan_data=self.plan_data,
            plan_text=self.plan_text,
            drawer_open=self.drawer_open,
            timer_start_time=self.timer_start_time,
            last_beeped_put=put_sec,
            last_beeped_take=take_sec,
            search_just_selected=self.search_just_selected,
        )

    def with_search_just_selected(self, value: bool) -> "AppState":
        return AppState(
            ingredients=self.ingredients,
            current_step=self.current_step,
            plan_data=self.plan_data,
            plan_text=self.plan_text,
            drawer_open=self.drawer_open,
            timer_start_time=self.timer_start_time,
            last_beeped_put=self.last_beeped_put,
            last_beeped_take=self.last_beeped_take,
            search_just_selected=value,
        )


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
    )
