# 🍲 涮涮AI - 智能火锅助手

> 扫码火锅菜单 → AI自动生成食材最佳涮煮顺序+时长 → 手机定时提醒 → 再也不煮老、煮错、煮漏食材

## 项目概述

这是一个黑客松项目的后端原型，实现了智能火锅助手的核心功能：
- 多种菜单输入方式（API、OCR、语音、文本）
- 智能涮煮方案生成
- 个性化模式支持

## 项目结构

```
hotpot_assistant/
├── api.py                      # 主API入口，统一对外接口
├── app.py                      # ModelScope 约定入口（见官方部署教程）
├── frontend/                   # Gradio Web 界面（ui.py = 组件+事件绑定）
├── demo.py                     # 演示脚本
├── requirements.txt            # Python 依赖（含 gradio）
├── README.md                   # 项目说明
│
├── context/                    # 上下文工程（提示词、领域知识、少样本）
│   ├── prompts/                # 排序等 system/user 模板
│   ├── knowledge/              # 火锅原则、锅底与技巧
│   ├── few_shot/               # 排序示例 JSON
│   └── context_loader.py      # 统一加载与组装
│
├── data/                       # 数据层
│   ├── ingredients_db.py       # 食材数据库（25+种常见火锅食材）
│   └── menu_api.py             # 模拟商家菜单API
│
└── services/                   # 服务层
    ├── recognition_service.py  # OCR/语音识别服务（模拟+真实API预留）
    ├── cooking_plan_service.py # 涮煮方案生成核心算法
    └── llm_service.py          # 大模型涮菜顺序排序（OpenAI 兼容接口）
```

## 核心功能

### 1. 菜单输入方式

| 方式 | 说明 | 实现状态 |
|------|------|----------|
| 商家API | 对接火锅店点餐系统 | ✅ 模拟实现 |
| OCR识别 | 拍摄菜单/小票照片 | ✅ 模拟实现 |
| 语音识别 | 语音说出菜品 | ✅ 模拟实现 |
| 文本输入 | 直接输入文字 | ✅ 完整实现 |
| 手动选择 | 从列表勾选 | ✅ 完整实现 |

### 2. 食材数据库

包含 25+ 种常见火锅食材：
- **肉类**: 肥牛、肥羊、牛肉片
- **内脏**: 毛肚、鸭肠、黄喉、脑花
- **海鲜**: 虾滑、鲜虾
- **丸滑**: 牛肉丸、鱼丸
- **蔬菜**: 土豆、藕片、菠菜、生菜、冬瓜
- **豆制品**: 老豆腐、嫩豆腐、腐竹
- **菌菇**: 金针菇、香菇、平菇
- **主食**: 方便面、年糕

每种食材包含：
- 涮煮时间（脆/嫩/软烂三档）
- 最低安全时间
- 涮煮技巧和注意事项
- 嘌呤水平和过敏原
- 推荐蘸料

### 3. 涮煮方案生成

智能排序规则：
- 需要长时间炖煮的先下（如脑花、丸子）
- 内脏类快速涮煮（七上八下）
- 蔬菜类最后下锅
- 确保所有食材同时可食用

支持的锅底类型：
- 麻辣红汤（时间系数 0.9）
- 清汤（标准）
- 番茄锅（时间系数 1.1）
- 菌汤、骨汤

支持的用户模式：
- 普通模式（标准时间）
- 老人模式（延长 50%）
- 儿童模式（延长 30%）
- 快手模式（缩短 20%，但不低于安全时间）

### 4. 涮菜顺序：大模型 vs 固定规则

- **固定规则（默认）**：按食材优先级与涮煮时间排序（脑花/丸子先下，蔬菜后下）。
- **大模型智能排序**：勾选「使用AI智能排序」并配置 API Key 后，由大模型根据锅底、用户模式、每样食材的分类与时间，生成推荐下锅顺序；调用失败时自动回退到固定规则。
- 支持任意 **OpenAI 兼容** 接口（OpenAI / 阿里云 DashScope / 智谱 / 本地模型等），通过 `base_url` 与 `model` 配置。环境变量：`HOTPOT_LLM_API_KEY`、`HOTPOT_LLM_BASE_URL`、`HOTPOT_LLM_MODEL`。
- **上下文工程**：提示词、领域知识、少样本示例统一放在 `context/`，由 `context_loader` 组装；启用 AI 排序时会自动注入已保存的用户偏好。可选环境变量 `HOTPOT_PROMPT_VERSION` 切换模板版本。

## Gradio 部署（Web 界面）

**部署条件：Gradio。** 安装依赖后运行 Gradio 应用即可在浏览器中使用。

```bash
# 安装依赖
pip install -r requirements.txt

# 启动 Web 界面（默认 http://0.0.0.0:7860）
python app.py
```

- 本机访问：浏览器打开 **http://127.0.0.1:7860**
- 局域网访问：已绑定 `0.0.0.0`，同一网络设备可通过本机 IP:7860 访问
- 需公网分享时可修改为 `demo.launch(..., share=True)` 获取临时公网链接

界面功能：输入食材（文本）、选择锅底/口感/用户模式 → 一键生成涮煮顺序、时间线、安全提醒与健康贴士。

### ModelScope 部署

- **入口文件**：平台约定为 **`app.py`**，本项目已提供（内部调用 Gradio 并 `demo.launch()`）。
- **完整步骤**（注册、创建 Studio、克隆/推送、必须文件清单、常见问题）：见 **[docs/MODELSCOPE_部署指南.md](docs/MODELSCOPE_部署指南.md)**。
- **简要流程**：在 ModelScope 创建 Gradio 创空间 → 复制带 Token 的克隆地址 → 本机 `git remote add modelscope <地址>` → `git add app.py api.py frontend/ requirements.txt data/ services/ context/` → `git commit` → `git push modelscope master`（或 `main`）。
- 更多说明请参阅 [ModelScope 文档中心](https://www.modelscope.cn)。

## 快速开始（API 调用）

```python
from api import HotpotAssistantAPI

# 初始化
api = HotpotAssistantAPI(use_mock=True)

# 方式1: 文本输入
result = api.input_from_text("肥牛、毛肚、鸭肠、虾滑、土豆、金针菇")
ingredients = result.data['ingredient_names']

# 生成涮煮方案
plan = api.generate_cooking_plan(
    ingredient_names=ingredients,
    broth_type="SPICY",      # 锅底类型
    texture="STANDARD",      # 口感偏好
    user_mode="NORMAL"       # 用户模式
)

# 查看方案
print(plan.data['timeline']['items'])      # 涮煮顺序
print(plan.data['timeline']['events'])     # 时间线事件
print(plan.data['safety_warnings'])        # 安全提醒
print(plan.data['health_tips'])            # 健康贴士
```

## 运行演示

```bash
cd hotpot_assistant
python demo.py
```

## 测试方案

| 方式 | 命令 / 操作 | 说明 |
|------|--------------|------|
| **一键自动化测试** | `python run_tests.py` | 不依赖 pytest，覆盖：文本输入、方案生成（规则/特色/混合）、用户偏好、上下文加载、特色食材解析、食材库与 JSON 导出。全部通过则退出码 0。 |
| **完整功能演示** | `python demo.py` | 依次演示：商家菜单、OCR、语音、文本、手动选择五种输入，以及涮煮方案生成、多模式对比。 |
| **界面测试** | `python app.py` 后浏览器打开 http://127.0.0.1:7860 | 手动验证：输入食材、特色食材、偏好保存/加载、生成方案与时间线展示。 |
| **ModelScope 部署** | 推送后由平台构建并打开 Studio | 验证线上环境与 `app.py` 入口是否正常。 |

推荐顺序：先跑 `python run_tests.py` 确认核心逻辑无 regression，再跑 `python demo.py` 看完整流程，最后用 Gradio 做一次界面与交互测试。

## API 接口说明

### 输入接口

```python
# 商家菜单API
api.input_from_menu_api(restaurant_id, item_ids=None)

# OCR识别
api.input_from_ocr(image_data=None, image_path=None)

# 语音识别
api.input_from_voice(audio_data=None)

# 文本输入
api.input_from_text(text)

# 手动选择
api.input_manual(ingredient_ids)
```

### 方案生成接口

```python
api.generate_cooking_plan(
    ingredient_names: List[str],     # 食材名称列表
    broth_type: str = "SPICY",       # SPICY/CLEAR/TOMATO/MUSHROOM/BONE
    texture: str = "STANDARD",       # CRISPY/TENDER/SOFT/STANDARD
    user_mode: str = "NORMAL",       # NORMAL/ELDERLY/CHILD/QUICK
    allergens_to_avoid: List[str] = None,  # 需要避免的过敏原
    custom_ingredients: List[Dict] = None   # 特色/店内食材，每项 {"name": "xxx", "cooking_seconds": 90}
)
```

### 辅助接口

```python
# 获取可用食材列表
api.get_available_ingredients(category=None)

# 获取餐厅列表
api.get_available_restaurants()

# 搜索食材
api.search_ingredients(keyword)
```

## 返回数据结构

### 涮煮方案

```json
{
  "timeline": {
    "total_duration_seconds": 312,
    "total_duration_display": "5分12秒",
    "items": [
      {
        "ingredient_name": "脑花",
        "cooking_seconds": 162,
        "cooking_display": "2分42秒",
        "technique": "轻放入锅，不要搅动，慢慢炖煮",
        "warning": "必须完全煮熟，表面变白凝固",
        "dipping_sauce": ["香油蒜泥", "干碟"],
        "is_must_cook_through": true,
        "purine_warning": true
      }
    ],
    "events": [
      {"time_seconds": 0, "action": "下锅", "item_name": "脑花"},
      {"time_seconds": 162, "action": "捞起", "item_name": "脑花"}
    ]
  },
  "health_tips": ["嘌呤警告...", "多喝水..."],
  "safety_warnings": ["必须煮熟...", "注意事项..."],
  "sauce_recommendations": {"脑花": ["香油蒜泥", "干碟"]}
}
```

## 后续扩展

### 接入真实 OCR API

```python
# 在 recognition_service.py 中实现 RealOCRService
class RealOCRService:
    def __init__(self, provider="baidu", api_key="xxx", secret_key="xxx"):
        # 初始化百度/阿里/腾讯 OCR
        pass
    
    def recognize(self, image_data):
        # 调用真实 API
        pass
```

### 接入真实语音识别 API

```python
# 在 recognition_service.py 中实现 RealVoiceService
class RealVoiceService:
    def __init__(self, provider="xunfei", api_key="xxx"):
        # 初始化讯飞/百度语音
        pass
```

### 扩展食材库

在 `ingredients_db.py` 中添加新食材：

```python
INGREDIENTS_DATABASE["new_ingredient"] = Ingredient(
    id="new_ingredient",
    name="新食材",
    aliases=["别名1", "别名2"],
    category=Category.MEAT,
    cooking_rule=CookingRule(
        base_seconds=30,
        crispy_seconds=20,
        tender_seconds=30,
        soft_seconds=60,
        min_safe_seconds=15,
        technique="涮煮技巧",
        warning="注意事项"
    ),
    nutrition=NutritionInfo(purine_level="中"),
    dipping_sauce=["推荐蘸料"],
    priority=50
)
```

## 技术栈

- Python 3.8+
- **Gradio**：Web 界面与部署
- 核心逻辑纯 Python，无其他必选依赖
- 模块化设计，易于扩展

## 黑客松亮点

1. **场景明确**: 火锅聚餐刚需，人人都能理解
2. **体验闭环**: 扫码 → 点菜 → 涮 → 提醒 → 分享
3. **轻量原型**: 几小时可跑通完整流程
4. **可扩展**: 预留真实API接口，随时可对接
5. **商业价值**: 可对接火锅店、点餐系统

## License

MIT
