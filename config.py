# -*- coding: utf-8 -*-
"""
涮涮AI - 配置：.env 加载 + 全局常量
统一 app.py / api 等入口的 .env 与启动参数。
"""

import os

_ROOT = os.path.dirname(os.path.abspath(__file__))
_DOTENV_LOADED = False


def load_dotenv():
    """加载项目根目录 .env 到环境变量（不覆盖已有值），只执行一次。"""
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return
    _DOTENV_LOADED = True
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


# 部署 / 启动常量（app.py、frontend.ui 使用）
SERVER_NAME = "0.0.0.0"
SERVER_PORT = 7860
GRADIO_SHARE = os.environ.get("HOTPOT_GRADIO_SHARE", "").strip().lower() in ("1", "true", "yes")

# 锅底 / 口感 / 模式 选项（展示用中文，值为后端枚举）
BROTH_CHOICES = [
    ("麻辣红汤", "SPICY"),
    ("清汤", "CLEAR"),
    ("番茄锅", "TOMATO"),
    ("菌汤", "MUSHROOM"),
    ("骨汤", "BONE"),
    ("鸳鸯锅", "COMBO"),
]
TEXTURE_CHOICES = [
    ("标准", "STANDARD"),
    ("脆嫩", "CRISPY"),
    ("软嫩", "TENDER"),
    ("软烂", "SOFT"),
]
MODE_CHOICES = [
    ("普通", "NORMAL"),
    ("老人模式", "ELDERLY"),
    ("儿童模式", "CHILD"),
    ("快手模式", "QUICK"),
]
