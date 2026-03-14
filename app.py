# -*- coding: utf-8 -*-
"""
<<<<<<< Updated upstream
涮涮AI — 部署入口
平台约定入口文件为 app.py（ModelScope / Gradio）。
.env 加载由 config.py 统一处理，此文件只做启动。
"""

import config  # noqa: F401  — 触发 .env 加载
from frontend import create_ui

if __name__ == "__main__":
    import gradio as gr
    demo = create_ui()
    demo.launch(server_name="0.0.0.0", server_port=7860)
=======
涮涮AI - 部署入口（ModelScope / Gradio）
平台约定入口文件名为 app.py。仅做配置加载与启动。
"""

import sys
import os

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from config import load_dotenv
from app_gradio import launch_demo

load_dotenv()

if __name__ == "__main__":
    launch_demo()
>>>>>>> Stashed changes
