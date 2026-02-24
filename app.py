# -*- coding: utf-8 -*-
"""
涮涮AI - ModelScope / Gradio 部署入口
平台约定入口文件名为 app.py，见官方部署教程。
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 加载 .env：若存在则把 KEY=VALUE 写入环境变量（不覆盖已有值）
_root = os.path.dirname(os.path.abspath(__file__))
_env_path = os.path.join(_root, ".env")
if os.path.isfile(_env_path):
    with open(_env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip("'\"")
                if k and os.environ.get(k) is None:
                    os.environ[k] = v

from app_gradio import create_ui

if __name__ == "__main__":
    demo = create_ui()
    # 开放访问：0.0.0.0 允许本机以外访问；ModelScope 等平台会接管端口时仍可生效
    demo.launch(server_name="0.0.0.0")
