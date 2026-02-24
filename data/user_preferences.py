# -*- coding: utf-8 -*-
"""
涮涮AI - 用户偏好持久化
将锅底、口感、用户模式、过敏原等保存到本地 JSON，下次可一键加载。
"""

import json
import os
from typing import Dict, List, Any, Optional

# 偏好文件路径（放在 data 目录下）
_PREFS_DIR = os.path.dirname(os.path.abspath(__file__))
_PREFS_FILE = os.path.join(_PREFS_DIR, "user_preferences.json")

_DEFAULT_PREFS: Dict[str, Any] = {
    "broth_type": "SPICY",
    "texture": "STANDARD",
    "user_mode": "NORMAL",
    "allergens_to_avoid": [],
}


def load_preferences() -> Dict[str, Any]:
    """
    从本地文件加载用户偏好。
    若文件不存在或读取出错，返回默认偏好。
    """
    if not os.path.isfile(_PREFS_FILE):
        return _DEFAULT_PREFS.copy()
    try:
        with open(_PREFS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 只保留已知字段，避免脏数据
        return {
            "broth_type": data.get("broth_type", _DEFAULT_PREFS["broth_type"]),
            "texture": data.get("texture", _DEFAULT_PREFS["texture"]),
            "user_mode": data.get("user_mode", _DEFAULT_PREFS["user_mode"]),
            "allergens_to_avoid": data.get("allergens_to_avoid", [])
            if isinstance(data.get("allergens_to_avoid"), list)
            else _DEFAULT_PREFS["allergens_to_avoid"],
        }
    except Exception:
        return _DEFAULT_PREFS.copy()


def save_preferences(
    broth_type: str = "SPICY",
    texture: str = "STANDARD",
    user_mode: str = "NORMAL",
    allergens_to_avoid: Optional[List[str]] = None,
) -> bool:
    """
    将当前偏好写入本地文件。
    返回是否保存成功。
    """
    data = {
        "broth_type": broth_type,
        "texture": texture,
        "user_mode": user_mode,
        "allergens_to_avoid": allergens_to_avoid or [],
    }
    try:
        with open(_PREFS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False
