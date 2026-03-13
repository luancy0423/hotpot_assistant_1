# -*- coding: utf-8 -*-
"""
涮涮AI - 核心涮煮方案生成服务
根据用户点的菜品，智能生成最佳涮煮顺序和时长
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
from datetime import datetime, timedelta
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.ingredients_db import (
    INGREDIENTS_DATABASE, 
    Ingredient, 
    Category, 
    Texture, 
    BrothType,
    get_ingredient_by_id,
    search_ingredient
)


class UserMode(Enum):
    """用户模式"""
    NORMAL = "普通模式"
    ELDERLY = "老人模式"      # 延长时间，确保熟透
    CHILD = "儿童模式"        # 延长时间，更软烂
    QUICK = "快手模式"        # 尽量快


@dataclass
class CookingItem:
    """单个涮煮项"""
    ingredient_id: str
    ingredient_name: str
    category: str
    cooking_seconds: int              # 涮煮时间(秒)
    technique: str                    # 涮煮技巧
    warning: Optional[str]            # 警告
    dipping_sauce: List[str]          # 推荐蘸料
    priority: int                     # 下锅顺序（越小越先）
    start_offset_seconds: int = 0     # 相对开始时间偏移
    is_must_cook_through: bool = False  # 是否必须煮熟（生食安全）
    purine_warning: bool = False      # 嘌呤警告
    allergens: List[str] = field(default_factory=list)


@dataclass
class CookingTimeline:
    """涮煮时间线"""
    total_duration_seconds: int
    items: List[CookingItem]
    broth_type: str
    user_mode: str
    created_at: str
    
    # 时间轴事件
    events: List[Dict] = field(default_factory=list)  # [{time: 0, action: "下锅", item: "脑花"}]


@dataclass
class CookingPlan:
    """完整涮煮方案"""
    timeline: CookingTimeline
    health_tips: List[str]            # 健康提示
    safety_warnings: List[str]        # 安全警告
    sauce_recommendations: Dict[str, List[str]]  # 蘸料推荐


class CookingPlanGenerator:
    """涮煮方案生成器"""
    
    # 用户模式时间调整系数
    MODE_MULTIPLIERS = {
        UserMode.NORMAL: 1.0,
        UserMode.ELDERLY: 1.5,    # 老人模式延长50%
        UserMode.CHILD: 1.3,      # 儿童模式延长30%
        UserMode.QUICK: 0.8,      # 快手模式缩短20%（不低于安全时间）
    }
    
    # 锅底时间调整系数
    BROTH_MULTIPLIERS = {
        BrothType.SPICY: 0.9,     # 麻辣锅温度高，稍快
        BrothType.CLEAR: 1.0,     # 清汤标准
        BrothType.TOMATO: 1.1,    # 番茄锅酸性，稍慢
        BrothType.MUSHROOM: 1.0,  # 菌汤标准
        BrothType.BONE: 1.0,      # 骨汤标准
        BrothType.COMBO: 0.95,    # 鸳鸯锅（红汤+清汤），取平均略偏红汤
    }
    
    def __init__(self):
        pass
    
    def generate_plan(
        self,
        ingredient_names: List[str],
        broth_type: BrothType = BrothType.SPICY,
        texture_preference: Texture = Texture.STANDARD,
        user_mode: UserMode = UserMode.NORMAL,
        allergens_to_avoid: List[str] = None,
        use_llm_sort: bool = False,
        llm_api_key: str = None,
        llm_base_url: str = None,
        llm_model: str = None,
        user_preferences: dict = None,
        custom_ingredients: List[Dict] = None,
    ) -> CookingPlan:
        """
        生成涮煮方案
        
        Args:
            ingredient_names: 食材名称列表
            broth_type: 锅底类型
            texture_preference: 口感偏好
            user_mode: 用户模式
            allergens_to_avoid: 需要避免的过敏原
            use_llm_sort: 是否使用大模型生成下锅顺序（否则用固定规则）
            llm_api_key: 大模型 API Key（use_llm_sort 时必填，也可用环境变量 HOTPOT_LLM_API_KEY）
            llm_base_url: 大模型接口地址（OpenAI 兼容，可选）
            llm_model: 模型名称（可选）
            user_preferences: 用户偏好（锅底、模式、过敏原等），用于大模型上下文
            custom_ingredients: 特色/自定义食材（店内特有、不在库中），每项至少含 name、cooking_seconds，可选 category、technique、warning、priority
        
        Returns:
            CookingPlan: 完整涮煮方案
        """
        allergens_to_avoid = allergens_to_avoid or []
        user_preferences = user_preferences or {}
        custom_ingredients = custom_ingredients or []
        
        # 1. 匹配食材
        matched_ingredients = self._match_ingredients(ingredient_names)
        
        # 2. 计算涮煮时间（库内食材）
        cooking_items = self._calculate_cooking_times(
            matched_ingredients, 
            broth_type, 
            texture_preference,
            user_mode
        )
        # 2b. 加入手动填写的特色食材
        custom_items = self._custom_ingredients_to_cooking_items(
            custom_ingredients, broth_type, user_mode
        )
        cooking_items = cooking_items + custom_items
        
        # 3. 排序（生成下锅顺序）：优先大模型，失败则回退规则
        sorted_items = self._resolve_cooking_order(
            cooking_items,
            broth_type,
            user_mode,
            use_llm_sort=use_llm_sort,
            llm_api_key=llm_api_key,
            llm_base_url=llm_base_url,
            llm_model=llm_model,
            user_preferences=user_preferences,
        )
        
        # 4. 生成时间线
        timeline = self._generate_timeline(sorted_items, broth_type, user_mode)
        
        # 5. 生成健康提示和安全警告
        health_tips = self._generate_health_tips(matched_ingredients, allergens_to_avoid)
        safety_warnings = self._generate_safety_warnings(matched_ingredients)
        if custom_items:
            custom_names = [c.ingredient_name for c in custom_items]
            safety_warnings.append(
                f"📌 以下为手动填写的特色食材，请按您填写的时间与提示操作：{', '.join(custom_names)}"
            )
        
        # 6. 蘸料推荐
        sauce_recommendations = self._generate_sauce_recommendations(matched_ingredients)
        
        return CookingPlan(
            timeline=timeline,
            health_tips=health_tips,
            safety_warnings=safety_warnings,
            sauce_recommendations=sauce_recommendations
        )
    
    def _match_ingredients(self, names: List[str]) -> List[Ingredient]:
        """根据名称匹配食材库中的食材"""
        matched = []
        for name in names:
            # 先精确匹配
            results = search_ingredient(name)
            if results:
                matched.append(results[0])
            else:
                # 如果没找到，尝试更模糊的匹配
                for ingredient in INGREDIENTS_DATABASE.values():
                    if name in ingredient.name or any(name in alias for alias in ingredient.aliases):
                        matched.append(ingredient)
                        break
        return matched
    
    def _calculate_cooking_times(
        self,
        ingredients: List[Ingredient],
        broth_type: BrothType,
        texture: Texture,
        user_mode: UserMode
    ) -> List[CookingItem]:
        """计算每个食材的涮煮时间"""
        items = []
        
        broth_multiplier = self.BROTH_MULTIPLIERS.get(broth_type, 1.0)
        mode_multiplier = self.MODE_MULTIPLIERS.get(user_mode, 1.0)
        
        for ingredient in ingredients:
            rule = ingredient.cooking_rule
            
            # 根据口感选择基础时间
            if texture == Texture.CRISPY:
                base_time = rule.crispy_seconds
            elif texture == Texture.TENDER:
                base_time = rule.tender_seconds
            elif texture == Texture.SOFT:
                base_time = rule.soft_seconds
            else:
                base_time = rule.base_seconds
            
            # 应用调整系数
            adjusted_time = int(base_time * broth_multiplier * mode_multiplier)
            
            # 确保不低于最低安全时间
            adjusted_time = max(adjusted_time, rule.min_safe_seconds)
            
            # 判断是否必须煮熟（主要是生肉、海鲜、内脏）
            must_cook_through = ingredient.category in [
                Category.MEAT, Category.OFFAL, Category.SEAFOOD, Category.MEATBALL, Category.OTHER
            ]
            
            items.append(CookingItem(
                ingredient_id=ingredient.id,
                ingredient_name=ingredient.name,
                category=ingredient.category.value,
                cooking_seconds=adjusted_time,
                technique=rule.technique or "",
                warning=rule.warning,
                dipping_sauce=ingredient.dipping_sauce,
                priority=ingredient.priority,
                is_must_cook_through=must_cook_through,
                purine_warning=ingredient.nutrition.purine_level == "高",
                allergens=ingredient.nutrition.allergens
            ))
        
        return items
    
    def _custom_ingredients_to_cooking_items(
        self,
        custom_ingredients: List[Dict],
        broth_type: BrothType,
        user_mode: UserMode,
    ) -> List[CookingItem]:
        """将手动填写的特色食材转为 CookingItem，并应用锅底/模式系数。"""
        if not custom_ingredients:
            return []
        broth_multiplier = self.BROTH_MULTIPLIERS.get(broth_type, 1.0)
        mode_multiplier = self.MODE_MULTIPLIERS.get(user_mode, 1.0)
        result = []
        for i, raw in enumerate(custom_ingredients):
            name = (raw.get("name") or "").strip()
            if not name:
                continue
            base_sec = int(raw.get("cooking_seconds", 120))
            min_safe = int(raw.get("min_safe_seconds", raw.get("cooking_seconds", 60)))
            min_safe = max(min_safe, 30)
            adjusted = int(base_sec * broth_multiplier * mode_multiplier)
            adjusted = max(adjusted, min_safe)
            cid = "custom_" + str(i) + "_" + name[:10].replace(" ", "_")
            category = (raw.get("category") or "其他").strip()
            if category not in ("肉类", "内脏类", "海鲜类", "丸滑类", "蔬菜类", "豆制品", "主食类", "菌菇类", "其他"):
                category = "其他"
            result.append(CookingItem(
                ingredient_id=cid,
                ingredient_name=name,
                category=category,
                cooking_seconds=adjusted,
                technique=(raw.get("technique") or "").strip(),
                warning=(raw.get("warning") or "").strip() or None,
                dipping_sauce=raw.get("dipping_sauce") or [],
                priority=int(raw.get("priority", 50)),
                start_offset_seconds=0,
                is_must_cook_through=True,
                purine_warning=False,
                allergens=raw.get("allergens") or [],
            ))
        return result
    
    def _resolve_cooking_order(
        self,
        cooking_items: List[CookingItem],
        broth_type: BrothType,
        user_mode: UserMode,
        use_llm_sort: bool = False,
        llm_api_key: str = None,
        llm_base_url: str = None,
        llm_model: str = None,
        user_preferences: dict = None,
    ) -> List[CookingItem]:
        """
        下锅顺序：优先大模型排序，无 API Key 或大模型调用失败时自动回退规则排序兜底。
        """
        import os
        key = (llm_api_key or os.environ.get("HOTPOT_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY") or "").strip()

        # 未请求大模型排序，或未配置 API Key → 直接使用规则兜底
        if not use_llm_sort or not key:
            return self._sort_by_priority(cooking_items)

        # 尝试大模型排序
        try:
            from services.llm_service import sort_cooking_order_by_llm
            ordered = sort_cooking_order_by_llm(
                cooking_items,
                broth_type=broth_type.value,
                user_mode=user_mode.value,
                api_key=key,
                base_url=llm_base_url,
                model=llm_model,
                user_preferences=user_preferences or {},
            )
            if ordered:
                return ordered
        except Exception:
            pass  # 大模型排序失败，回退规则排序

        # 大模型排序失败兜底
        return self._sort_by_priority(cooking_items)
    
    def _sort_by_priority(self, items: List[CookingItem]) -> List[CookingItem]:
        """
        按优先级排序（固定规则兜底）
        规则：
        1. 优先级数值越小越先下（脑花、丸子等需要长时间煮的先下）
        2. 同优先级按烹饪时间长的先下
        3. 蔬菜类最后下
        """
        return sorted(items, key=lambda x: (x.priority, -x.cooking_seconds))
    
    def _generate_timeline(
        self,
        sorted_items: List[CookingItem],
        broth_type: BrothType,
        user_mode: UserMode
    ) -> CookingTimeline:
        """生成时间线"""
        events = []
        current_time = 0
        
        # 策略：让所有食材尽量在差不多时间可以吃
        # 找出最长烹饪时间
        if not sorted_items:
            return CookingTimeline(
                total_duration_seconds=0,
                items=[],
                broth_type=broth_type.value,
                user_mode=user_mode.value,
                created_at=datetime.now().isoformat(),
                events=[]
            )
        
        max_cooking_time = max(item.cooking_seconds for item in sorted_items)
        
        # 计算每个食材的下锅时间偏移
        for item in sorted_items:
            # 让所有食材在同一时间点完成（第一批）
            # start_offset = max_cooking_time - item.cooking_seconds
            # 或者按顺序下锅，间隔一定时间
            item.start_offset_seconds = current_time
            
            # 添加下锅事件
            events.append({
                "time_seconds": current_time,
                "action": "下锅",
                "item_name": item.ingredient_name,
                "item_id": item.ingredient_id,
                "message": f"请将【{item.ingredient_name}】下锅"
            })
            
            # 添加捞起事件
            events.append({
                "time_seconds": current_time + item.cooking_seconds,
                "action": "捞起",
                "item_name": item.ingredient_name,
                "item_id": item.ingredient_id,
                "message": f"【{item.ingredient_name}】好了！快捞起来！"
            })
            
            # 下一个食材的下锅时间（错开一点避免手忙脚乱）
            # 快熟的可以稍后下，形成"流水线"
            if item.cooking_seconds > 60:
                current_time += 30  # 长时间的间隔30秒
            else:
                current_time += 10  # 短时间的间隔10秒
        
        # 按时间排序事件
        events.sort(key=lambda x: (x["time_seconds"], x["action"] == "捞起"))
        
        # 计算总时长
        total_duration = max(e["time_seconds"] for e in events) if events else 0
        
        return CookingTimeline(
            total_duration_seconds=total_duration,
            items=sorted_items,
            broth_type=broth_type.value,
            user_mode=user_mode.value,
            created_at=datetime.now().isoformat(),
            events=events
        )
    
    def _generate_health_tips(
        self, 
        ingredients: List[Ingredient],
        allergens_to_avoid: List[str]
    ) -> List[str]:
        """生成健康提示"""
        tips = []
        
        # 嘌呤警告
        high_purine_items = [i.name for i in ingredients if i.nutrition.purine_level == "高"]
        if high_purine_items:
            tips.append(f"⚠️ 以下食材嘌呤较高，痛风患者请适量：{', '.join(high_purine_items)}")
        
        # 过敏原警告
        for ingredient in ingredients:
            for allergen in ingredient.nutrition.allergens:
                if allergen in allergens_to_avoid:
                    tips.append(f"🚫 【{ingredient.name}】含有您标记的过敏原：{allergen}")
        
        # 一般性提示
        tips.append("💡 火锅汤底嘌呤含量会随时间升高，建议先吃菜后喝汤")
        tips.append("💧 记得多喝水，辣锅配凉茶更佳")
        
        return tips
    
    def _generate_safety_warnings(self, ingredients: List[Ingredient]) -> List[str]:
        """生成安全警告"""
        warnings = []
        
        # 必须煮熟的食材
        raw_items = [
            i.name for i in ingredients 
            if i.category in [Category.MEAT, Category.OFFAL, Category.SEAFOOD, Category.MEATBALL, Category.OTHER]
        ]
        if raw_items:
            warnings.append(f"🔥 以下食材必须完全煮熟：{', '.join(raw_items)}")
        
        # 特殊警告
        for ingredient in ingredients:
            if ingredient.cooking_rule.warning:
                warnings.append(f"⚡ {ingredient.name}：{ingredient.cooking_rule.warning}")
        
        return warnings
    
    # 补充蘸料池：每个食材在原有推荐外再多给 2 个建议，从此池中选取（避免与原有重复）
    _EXTRA_SAUCES_POOL: List[str] = [
        "辣椒酱", "香菜", "葱花", "醋", "蚝油", "花生碎", "芝麻", "腐乳", "韭花酱",
        "干碟", "油碟", "蒜泥", "沙茶酱", "麻酱", "香油", "芥末酱油", "甜辣酱",
        "蒜泥香油", "香油蒜泥", "辣椒面", "小米辣",
    ]

    def _generate_sauce_recommendations(self, ingredients: List[Ingredient]) -> Dict[str, List[str]]:
        """生成蘸料推荐：沿用食材原有推荐，每个食材再多给 2 个建议。"""
        recommendations = {}
        pool = list(self._EXTRA_SAUCES_POOL)

        for ingredient in ingredients:
            base = list(ingredient.dipping_sauce) if ingredient.dipping_sauce else []
            existing = set(base)
            added = 0
            for s in pool:
                if added >= 2:
                    break
                if s not in existing:
                    base.append(s)
                    existing.add(s)
                    added += 1
            if base:
                recommendations[ingredient.name] = base
        return recommendations


# ============== 便捷函数 ==============

def quick_generate_plan(
    ingredient_names: List[str],
    broth_type: str = "SPICY",
    texture: str = "STANDARD",
    mode: str = "NORMAL"
) -> CookingPlan:
    """
    快速生成涮煮方案
    
    Args:
        ingredient_names: 食材名称列表
        broth_type: 锅底类型 (SPICY/CLEAR/TOMATO/MUSHROOM/BONE)
        texture: 口感偏好 (CRISPY/TENDER/SOFT/STANDARD)
        mode: 用户模式 (NORMAL/ELDERLY/CHILD/QUICK)
    
    Returns:
        CookingPlan
    """
    generator = CookingPlanGenerator()
    
    return generator.generate_plan(
        ingredient_names=ingredient_names,
        broth_type=BrothType[broth_type],
        texture_preference=Texture[texture],
        user_mode=UserMode[mode]
    )


def format_plan_for_display(plan: CookingPlan) -> str:
    """将方案格式化为可读文本"""
    lines = []
    
    lines.append("=" * 50)
    lines.append("🍲 涮涮AI - 您的专属涮煮方案")
    lines.append("=" * 50)
    lines.append("")
    
    timeline = plan.timeline
    lines.append(f"🕐 预计总时长：{timeline.total_duration_seconds // 60}分{timeline.total_duration_seconds % 60}秒")
    lines.append(f"🍜 锅底类型：{timeline.broth_type}")
    lines.append(f"👤 模式：{timeline.user_mode}")
    lines.append("")
    
    lines.append("📋 涮煮顺序：")
    lines.append("-" * 40)
    
    for i, item in enumerate(timeline.items, 1):
        time_str = f"{item.cooking_seconds}秒" if item.cooking_seconds < 60 else f"{item.cooking_seconds // 60}分{item.cooking_seconds % 60}秒"
        lines.append(f"{i}. 【{item.ingredient_name}】")
        lines.append(f"   ⏱️ 涮煮时间：{time_str}")
        if item.technique:
            lines.append(f"   💡 技巧：{item.technique}")
        if item.warning:
            lines.append(f"   ⚠️ 注意：{item.warning}")
        lines.append(f"   🥢 推荐蘸料：{', '.join(item.dipping_sauce)}")
        lines.append("")
    
    if plan.safety_warnings:
        lines.append("🚨 安全提醒：")
        for warning in plan.safety_warnings:
            lines.append(f"   {warning}")
        lines.append("")
    
    if plan.health_tips:
        lines.append("💚 健康贴士：")
        for tip in plan.health_tips:
            lines.append(f"   {tip}")
    
    lines.append("")
    lines.append("=" * 50)
    lines.append("祝您用餐愉快！🎉")
    
    return "\n".join(lines)
