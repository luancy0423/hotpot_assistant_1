# -*- coding: utf-8 -*-
"""
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
