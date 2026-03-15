# -*- coding: utf-8 -*-
"""
涮涮AI - 部署入口（ModelScope / Gradio）
平台约定入口文件名为 app.py。仅做配置加载与启动。
"""

import sys
import os

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from config import load_dotenv
from frontend.ui import launch_demo

if __name__ == "__main__":
    launch_demo()
