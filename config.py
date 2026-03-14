# -*- coding: utf-8 -*-
"""
涮涮AI — 全局配置
统一管理 .env 加载与 UI 常量，消除各入口文件的重复代码。
"""

import os
import sys

# ── 确保项目根在 sys.path ────────────────────────────────────────
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ── .env 加载（只执行一次）──────────────────────────────────────
_ENV_LOADED = False


def load_env() -> None:
    """读取项目根目录的 .env 文件，将 KEY=VALUE 写入环境变量（不覆盖已有值）。"""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    _ENV_LOADED = True
    env_path = os.path.join(_ROOT, ".env")
    if not os.path.isfile(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    k, v = k.strip(), v.strip().strip("'\"")
                    if k and os.environ.get(k) is None:
                        os.environ[k] = v
    except Exception:
        pass


# 模块导入时自动加载，无需外部显式调用
load_env()


# ── UI 选项常量（前端与后端共用）──────────────────────────────────
BROTH_CHOICES = [
    ("麻辣红汤", "SPICY"),
    ("清汤",     "CLEAR"),
    ("番茄锅",   "TOMATO"),
    ("菌汤",     "MUSHROOM"),
    ("骨汤",     "BONE"),
    ("鸳鸯锅",   "COMBO"),
]

TEXTURE_CHOICES = [
    ("标准", "STANDARD"),
    ("脆嫩", "CRISPY"),
    ("软嫩", "TENDER"),
    ("软烂", "SOFT"),
]

MODE_CHOICES = [
    ("普通",     "NORMAL"),
    ("老人模式", "ELDERLY"),
    ("儿童模式", "CHILD"),
    ("快手模式", "QUICK"),
]
