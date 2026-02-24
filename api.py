# -*- coding: utf-8 -*-
"""
涮涮AI - 主API接口
提供统一的对外接口，整合菜单输入、识别、方案生成等功能
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Union
from enum import Enum
import json

from data.ingredients_db import (
    INGREDIENTS_DATABASE,
    get_all_ingredients,
    get_ingredient_by_id,
    search_ingredient,
    get_ingredients_by_category,
    Category,
    BrothType,
    Texture
)
from data.menu_api import (
    MockMenuAPI,
    MockOrderAPI,
    RestaurantMenu,
    UserOrder
)
from services.recognition_service import (
    MockRecognitionService,
    RecognitionResult,
    create_recognition_service
)
from services.cooking_plan_service import (
    CookingPlanGenerator,
    CookingPlan,
    UserMode,
    quick_generate_plan,
    format_plan_for_display
)
from data.user_preferences import load_preferences, save_preferences

_DOTENV_LOADED = False


def _ensure_dotenv_loaded():
    """在需要读取大模型配置前加载项目根目录的 .env（只执行一次）。"""
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return
    _DOTENV_LOADED = True
    import os
    root = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(root, ".env")
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


class InputMethod(Enum):
    """输入方式"""
    MANUAL = "manual"           # 手动选择
    MENU_API = "menu_api"       # 商家菜单API
    OCR = "ocr"                 # 拍照识别
    VOICE = "voice"             # 语音识别
    TEXT = "text"               # 文本输入


@dataclass
class APIResponse:
    """统一API响应"""
    success: bool
    data: Optional[Dict] = None
    error: Optional[str] = None
    message: str = ""


class HotpotAssistantAPI:
    """涮涮AI 主API类"""
    
    def __init__(self, use_mock: bool = True):
        """
        初始化API
        
        Args:
            use_mock: 是否使用模拟服务（开发测试用）
        """
        self.use_mock = use_mock
        self.recognition_service = create_recognition_service(use_mock=use_mock)
        self.plan_generator = CookingPlanGenerator()
    
    # ============== 1. 菜单输入接口 ==============
    
    def input_from_menu_api(self, restaurant_id: str, item_ids: List[str] = None) -> APIResponse:
        """
        方式1: 通过商家菜单API输入
        
        Args:
            restaurant_id: 餐厅ID
            item_ids: 选择的菜品ID列表（可选，不传则返回菜单）
        
        Returns:
            APIResponse: 包含菜单或已选菜品的响应
        """
        try:
            menu = MockMenuAPI.get_menu(restaurant_id)
            if not menu:
                return APIResponse(
                    success=False,
                    error=f"餐厅 {restaurant_id} 不存在"
                )
            
            if item_ids:
                # 返回选中的菜品对应的食材
                ingredient_names = []
                for item in menu.menu_items:
                    if item.id in item_ids:
                        # 获取菜品对应的食材名称
                        for ing_id in item.ingredient_ids:
                            ing = get_ingredient_by_id(ing_id)
                            if ing:
                                ingredient_names.append(ing.name)
                
                return APIResponse(
                    success=True,
                    data={
                        "restaurant_name": menu.restaurant_name,
                        "selected_items": item_ids,
                        "ingredient_names": ingredient_names,
                        "input_method": InputMethod.MENU_API.value
                    },
                    message=f"已从{menu.restaurant_name}选择{len(ingredient_names)}种食材"
                )
            else:
                # 返回完整菜单供选择
                return APIResponse(
                    success=True,
                    data={
                        "restaurant_name": menu.restaurant_name,
                        "broth_options": [
                            {"id": b.id, "name": b.name, "price": b.price, "type": b.broth_type}
                            for b in menu.broth_options
                        ],
                        "menu_items": [
                            {
                                "id": item.id,
                                "name": item.name,
                                "category": item.category,
                                "price": item.price,
                                "description": item.description
                            }
                            for item in menu.menu_items
                        ]
                    },
                    message="获取菜单成功"
                )
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    def input_from_ocr(self, image_data: bytes = None, image_path: str = None) -> APIResponse:
        """
        方式2: 通过拍照/图片识别输入
        
        Args:
            image_data: 图片二进制数据
            image_path: 图片路径（模拟测试用）
        
        Returns:
            APIResponse: 识别出的食材列表
        """
        try:
            result = self.recognition_service.recognize_from_image(image_data, image_path)
            
            if not result.success:
                return APIResponse(
                    success=False,
                    error=result.error_message or "图片识别失败"
                )
            
            return APIResponse(
                success=True,
                data={
                    "ingredient_names": result.items,
                    "raw_text": result.raw_text,
                    "confidence": result.confidence,
                    "input_method": InputMethod.OCR.value
                },
                message=f"识别成功，共识别出{len(result.items)}种食材"
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    def input_from_voice(self, audio_data: bytes = None) -> APIResponse:
        """
        方式3: 通过语音输入
        
        Args:
            audio_data: 音频二进制数据
        
        Returns:
            APIResponse: 识别出的食材列表
        """
        try:
            result = self.recognition_service.recognize_from_voice(audio_data)
            
            if not result.success:
                return APIResponse(
                    success=False,
                    error=result.error_message or "语音识别失败"
                )
            
            return APIResponse(
                success=True,
                data={
                    "ingredient_names": result.items,
                    "transcript": result.raw_text,
                    "confidence": result.confidence,
                    "input_method": InputMethod.VOICE.value
                },
                message=f"识别成功：{result.raw_text}"
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    def input_from_text(self, text: str) -> APIResponse:
        """
        方式4: 通过文本输入
        用户直接输入"肥牛、毛肚、鸭肠"这样的文本
        
        Args:
            text: 用户输入的文本
        
        Returns:
            APIResponse: 解析出的食材列表
        """
        try:
            result = self.recognition_service.recognize_from_text(text)
            
            return APIResponse(
                success=True,
                data={
                    "ingredient_names": result.items,
                    "raw_text": text,
                    "input_method": InputMethod.TEXT.value
                },
                message=f"已解析出{len(result.items)}种食材"
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    def input_manual(self, ingredient_ids: List[str]) -> APIResponse:
        """
        方式5: 手动选择食材
        
        Args:
            ingredient_ids: 食材ID列表
        
        Returns:
            APIResponse: 选择的食材信息
        """
        try:
            names = []
            for ing_id in ingredient_ids:
                ing = get_ingredient_by_id(ing_id)
                if ing:
                    names.append(ing.name)
            
            return APIResponse(
                success=True,
                data={
                    "ingredient_names": names,
                    "ingredient_ids": ingredient_ids,
                    "input_method": InputMethod.MANUAL.value
                },
                message=f"已选择{len(names)}种食材"
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    # ============== 2. 涮煮方案生成接口 ==============
    
    def generate_cooking_plan(
        self,
        ingredient_names: List[str],
        broth_type: str = "SPICY",
        texture: str = "STANDARD",
        user_mode: str = "NORMAL",
        allergens_to_avoid: List[str] = None,
        use_llm_sort: bool = False,
        llm_api_key: str = None,
        llm_base_url: str = None,
        llm_model: str = None,
        user_preferences: dict = None,
        custom_ingredients: List[Dict] = None,
    ) -> APIResponse:
        """
        生成涮煮方案
        
        Args:
            ingredient_names: 食材名称列表
            broth_type: 锅底类型 (SPICY/CLEAR/TOMATO/MUSHROOM/BONE)
            texture: 口感偏好 (CRISPY/TENDER/SOFT/STANDARD)
            user_mode: 用户模式 (NORMAL/ELDERLY/CHILD/QUICK)
            allergens_to_avoid: 需要避免的过敏原
            use_llm_sort: 是否用大模型生成下锅顺序
            llm_api_key: 大模型 API Key（可选，也可设环境变量 HOTPOT_LLM_API_KEY）
            llm_base_url: 大模型接口地址（可选）
            llm_model: 模型名称（可选）
            user_preferences: 用户偏好（用于大模型上下文）；不传则自动从已保存偏好读取
            custom_ingredients: 特色/自定义食材（店内特有），每项至少 {"name": "xxx", "cooking_seconds": 90}，可选 category、technique、warning、priority
        
        Returns:
            APIResponse: 完整涮煮方案
        """
        prefs = user_preferences
        if prefs is None and use_llm_sort:
            r = self.get_user_preferences()
            if r.success and r.data:
                prefs = r.data
            else:
                prefs = {}
        if prefs is None:
            prefs = {}
        # 大模型 Key、Base URL 由系统预设：未传入时使用环境变量（生成前确保已加载 .env）
        import os
        if use_llm_sort:
            _ensure_dotenv_loaded()
        if use_llm_sort and not (llm_api_key or "").strip():
            llm_api_key = os.environ.get("HOTPOT_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
        if use_llm_sort and not (llm_base_url or "").strip():
            llm_base_url = os.environ.get("HOTPOT_LLM_BASE_URL") or ""
        if use_llm_sort and not (llm_model or "").strip():
            llm_model = os.environ.get("HOTPOT_LLM_MODEL") or ""
        try:
            plan = self.plan_generator.generate_plan(
                ingredient_names=ingredient_names,
                broth_type=BrothType[broth_type],
                texture_preference=Texture[texture],
                user_mode=UserMode[user_mode],
                allergens_to_avoid=allergens_to_avoid or [],
                use_llm_sort=use_llm_sort,
                llm_api_key=(llm_api_key or "").strip() or None,
                llm_base_url=(llm_base_url or "").strip() or None,
                llm_model=(llm_model or "").strip() or None,
                user_preferences=prefs,
                custom_ingredients=custom_ingredients or [],
            )
            
            # 转换为可序列化的字典
            plan_dict = {
                "timeline": {
                    "total_duration_seconds": plan.timeline.total_duration_seconds,
                    "total_duration_display": f"{plan.timeline.total_duration_seconds // 60}分{plan.timeline.total_duration_seconds % 60}秒",
                    "broth_type": plan.timeline.broth_type,
                    "user_mode": plan.timeline.user_mode,
                    "created_at": plan.timeline.created_at,
                    "items": [
                        {
                            "ingredient_id": item.ingredient_id,
                            "ingredient_name": item.ingredient_name,
                            "category": item.category,
                            "cooking_seconds": item.cooking_seconds,
                            "cooking_display": f"{item.cooking_seconds}秒" if item.cooking_seconds < 60 else f"{item.cooking_seconds // 60}分{item.cooking_seconds % 60}秒",
                            "technique": item.technique,
                            "warning": item.warning,
                            "dipping_sauce": item.dipping_sauce,
                            "priority": item.priority,
                            "start_offset_seconds": item.start_offset_seconds,
                            "is_must_cook_through": item.is_must_cook_through,
                            "purine_warning": item.purine_warning,
                            "allergens": item.allergens
                        }
                        for item in plan.timeline.items
                    ],
                    "events": plan.timeline.events
                },
                "health_tips": plan.health_tips,
                "safety_warnings": plan.safety_warnings,
                "sauce_recommendations": plan.sauce_recommendations
            }
            
            return APIResponse(
                success=True,
                data=plan_dict,
                message=f"方案生成成功，共{len(plan.timeline.items)}种食材，预计{plan.timeline.total_duration_seconds // 60}分钟"
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    # ============== 3. 辅助接口 ==============
    
    def get_available_ingredients(self, category: str = None) -> APIResponse:
        """获取可用食材列表"""
        try:
            if category:
                cat = Category[category.upper()]
                ingredients = get_ingredients_by_category(cat)
            else:
                ingredients = list(INGREDIENTS_DATABASE.values())
            
            return APIResponse(
                success=True,
                data={
                    "ingredients": [
                        {
                            "id": ing.id,
                            "name": ing.name,
                            "category": ing.category.value,
                            "aliases": ing.aliases
                        }
                        for ing in ingredients
                    ]
                }
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    def get_available_restaurants(self) -> APIResponse:
        """获取支持的餐厅列表"""
        try:
            restaurants = MockMenuAPI.get_restaurant_list()
            return APIResponse(
                success=True,
                data={"restaurants": restaurants}
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))
    
    def search_ingredients(self, keyword: str) -> APIResponse:
        """搜索食材"""
        try:
            results = search_ingredient(keyword)
            return APIResponse(
                success=True,
                data={
                    "results": [
                        {
                            "id": ing.id,
                            "name": ing.name,
                            "category": ing.category.value
                        }
                        for ing in results
                    ]
                }
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))

    # ============== 4. 用户偏好 ==============

    def get_user_preferences(self) -> APIResponse:
        """获取已保存的用户偏好（锅底、口感、模式、过敏原）。"""
        try:
            prefs = load_preferences()
            return APIResponse(
                success=True,
                data=prefs,
                message="已加载用户偏好"
            )
        except Exception as e:
            return APIResponse(success=False, error=str(e))

    def save_user_preferences(
        self,
        broth_type: str = "SPICY",
        texture: str = "STANDARD",
        user_mode: str = "NORMAL",
        allergens_to_avoid: List[str] = None,
    ) -> APIResponse:
        """保存当前设置为用户偏好。"""
        try:
            ok = save_preferences(
                broth_type=broth_type,
                texture=texture,
                user_mode=user_mode,
                allergens_to_avoid=allergens_to_avoid or [],
            )
            if ok:
                return APIResponse(
                    success=True,
                    data=load_preferences(),
                    message="偏好已保存，下次可一键加载"
                )
            return APIResponse(success=False, error="保存失败")
        except Exception as e:
            return APIResponse(success=False, error=str(e))


# ============== 快捷函数（用于演示）==============

def demo_full_workflow():
    """演示完整工作流程"""
    api = HotpotAssistantAPI(use_mock=True)
    
    print("=" * 60)
    print("🍲 涮涮AI 演示")
    print("=" * 60)
    
    # 方式1: 通过商家菜单API
    print("\n【方式1: 商家菜单API】")
    restaurants = api.get_available_restaurants()
    print(f"可用餐厅: {json.dumps(restaurants.data, ensure_ascii=False, indent=2)}")
    
    # 获取海底捞菜单
    menu = api.input_from_menu_api("haidilao_001")
    print(f"\n菜单获取: {menu.message}")
    
    # 选择菜品
    selected = api.input_from_menu_api(
        "haidilao_001",
        item_ids=["item_001", "item_005", "item_006", "item_009", "item_013", "item_015"]
    )
    print(f"选择结果: {selected.data['ingredient_names']}")
    
    # 方式2: OCR识别
    print("\n【方式2: 拍照识别（模拟）】")
    ocr_result = api.input_from_ocr()
    print(f"OCR识别: {ocr_result.message}")
    print(f"识别出: {ocr_result.data['ingredient_names']}")
    
    # 方式3: 语音识别
    print("\n【方式3: 语音识别（模拟）】")
    voice_result = api.input_from_voice()
    print(f"语音转写: {voice_result.data['transcript']}")
    print(f"识别出: {voice_result.data['ingredient_names']}")
    
    # 方式4: 文本输入
    print("\n【方式4: 文本输入】")
    text_result = api.input_from_text("我要肥牛、毛肚、鸭肠、虾滑、土豆、金针菇")
    print(f"解析出: {text_result.data['ingredient_names']}")
    
    # 生成涮煮方案
    print("\n" + "=" * 60)
    print("🔥 生成涮煮方案")
    print("=" * 60)
    
    ingredients = ["肥牛", "毛肚", "鸭肠", "虾滑", "土豆", "金针菇", "菠菜"]
    plan_result = api.generate_cooking_plan(
        ingredient_names=ingredients,
        broth_type="SPICY",
        texture="STANDARD",
        user_mode="NORMAL"
    )
    
    if plan_result.success:
        plan = plan_result.data
        print(f"\n总时长: {plan['timeline']['total_duration_display']}")
        print(f"锅底: {plan['timeline']['broth_type']}")
        
        print("\n📋 涮煮顺序:")
        for i, item in enumerate(plan['timeline']['items'], 1):
            print(f"  {i}. {item['ingredient_name']} - {item['cooking_display']}")
            if item['technique']:
                print(f"     技巧: {item['technique']}")
        
        print("\n⏱️ 时间线事件:")
        for event in plan['timeline']['events'][:10]:  # 只显示前10个
            print(f"  {event['time_seconds']:3d}秒 | {event['action']} | {event['message']}")
        
        print("\n🚨 安全提醒:")
        for warning in plan['safety_warnings']:
            print(f"  {warning}")
        
        print("\n💚 健康贴士:")
        for tip in plan['health_tips']:
            print(f"  {tip}")


if __name__ == "__main__":
    demo_full_workflow()
