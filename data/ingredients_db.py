# -*- coding: utf-8 -*-
"""
涮涮AI - 火锅食材数据库
包含常见火锅食材的涮煮时间、注意事项、营养信息等
"""

import os
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict

class Category(Enum):
    """食材分类"""
    MEAT = "肉类"           # 牛羊肉等
    OFFAL = "内脏类"        # 毛肚、鸭肠、脑花、鸭血等
    SEAFOOD = "海鲜类"      # 虾、鱼片、贝类等
    MEATBALL = "丸滑类"     # 各种丸子、虾滑等
    VEGETABLE = "蔬菜类"    # 青菜、土豆等
    TOFU = "豆制品"         # 豆腐、腐竹等
    NOODLE = "主食类"       # 面条、年糕、苕粉等
    MUSHROOM = "菌菇类"     # 各种菇类
    OTHER = "其他"          # 蛋类、海藻等

class Texture(Enum):
    """口感偏好"""
    CRISPY = "脆"      # 脆嫩
    TENDER = "嫩"      # 软嫩
    SOFT = "软烂"      # 炖烂
    STANDARD = "标准"  # 正常

class BrothType(Enum):
    """锅底类型"""
    SPICY = "红汤/麻辣"
    CLEAR = "清汤"
    TOMATO = "番茄"
    MUSHROOM = "菌汤"
    BONE = "骨汤"

@dataclass
class CookingRule:
    """涮煮规则"""
    base_seconds: int                           # 基础涮煮时间(秒)
    crispy_seconds: int                         # 脆口时间
    tender_seconds: int                         # 软嫩时间
    soft_seconds: int                           # 软烂时间
    min_safe_seconds: int                       # 最低安全时间(必须熟透)
    technique: Optional[str] = None             # 涮煮技巧
    warning: Optional[str] = None               # 警告提示

@dataclass 
class NutritionInfo:
    """营养信息"""
    purine_level: str = "低"                    # 嘌呤水平: 低/中/高
    calories_per_100g: int = 0                  # 每100g热量
    allergens: List[str] = field(default_factory=list)  # 过敏原

@dataclass
class Ingredient:
    """食材完整信息"""
    id: str                                     # 唯一标识
    name: str                                   # 食材名称
    aliases: List[str]                          # 别名
    category: Category                          # 分类
    cooking_rule: CookingRule                   # 涮煮规则
    nutrition: NutritionInfo                    # 营养信息
    dipping_sauce: List[str]                    # 推荐蘸料
    priority: int = 50                          # 下锅优先级(越小越先下)
    broth_time_modifier: Dict[BrothType, float] = field(default_factory=dict)  # 不同锅底时间系数

# ============== 食材数据库 ==============

INGREDIENTS_DATABASE: Dict[str, Ingredient] = {
    # ========== 肉类 ==========
    "feiniurou": Ingredient(
        id="feiniurou",
        name="肥牛卷",
        aliases=["肥牛", "雪花肥牛", "M5肥牛", "牛肉卷"],
        category=Category.MEAT,
        cooking_rule=CookingRule(
            base_seconds=8,
            crispy_seconds=5,
            tender_seconds=8,
            soft_seconds=15,
            min_safe_seconds=5,
            technique="筷子夹住涮动，变色即可捞起",
            warning="久煮会变老变柴"
        ),
        nutrition=NutritionInfo(purine_level="中", calories_per_100g=250),
        dipping_sauce=["沙茶酱", "麻酱", "蒜泥香油"],
        priority=30,
        broth_time_modifier={BrothType.SPICY: 0.9, BrothType.CLEAR: 1.0}
    ),
    
    "feiyangrou": Ingredient(
        id="feiyangrou", 
        name="肥羊卷",
        aliases=["羊肉卷", "羊肉片", "精品羊肉"],
        category=Category.MEAT,
        cooking_rule=CookingRule(
            base_seconds=10,
            crispy_seconds=6,
            tender_seconds=10,
            soft_seconds=18,
            min_safe_seconds=6,
            technique="涮至变色微卷即可",
            warning="羊肉膻味重，建议配蒜泥"
        ),
        nutrition=NutritionInfo(purine_level="中", calories_per_100g=280),
        dipping_sauce=["麻酱", "韭花酱", "腐乳"],
        priority=32
    ),
    
    "niuroupian": Ingredient(
        id="niuroupian",
        name="嫩牛肉",
        aliases=["牛肉片", "吊龙", "匙柄", "牛舌"],
        category=Category.MEAT,
        cooking_rule=CookingRule(
            base_seconds=12,
            crispy_seconds=8,
            tender_seconds=12,
            soft_seconds=20,
            min_safe_seconds=8,
            technique="厚切牛肉需多涮几秒"
        ),
        nutrition=NutritionInfo(purine_level="中", calories_per_100g=190),
        dipping_sauce=["沙茶酱", "蒜泥香油"],
        priority=35
    ),
    
    # ========== 内脏类 ==========
    "maodu": Ingredient(
        id="maodu",
        name="毛肚",
        aliases=["黑毛肚", "金毛肚", "鲜毛肚", "牛百叶"],
        category=Category.OFFAL,
        cooking_rule=CookingRule(
            base_seconds=15,
            crispy_seconds=10,
            tender_seconds=15,
            soft_seconds=30,
            min_safe_seconds=10,
            technique="七上八下，筷子夹住涮15下",
            warning="超过30秒会变硬如橡皮"
        ),
        nutrition=NutritionInfo(purine_level="高", calories_per_100g=72),
        dipping_sauce=["香油蒜泥", "油碟"],
        priority=20,  # 优先级高，适合先下
    ),
    
    "yachang": Ingredient(
        id="yachang",
        name="鸭肠",
        aliases=["脆鸭肠", "鲜鸭肠"],
        category=Category.OFFAL,
        cooking_rule=CookingRule(
            base_seconds=12,
            crispy_seconds=8,
            tender_seconds=12,
            soft_seconds=20,
            min_safe_seconds=8,
            technique="快速涮烫，卷曲即捞",
            warning="煮太久会失去脆感"
        ),
        nutrition=NutritionInfo(purine_level="高", calories_per_100g=129),
        dipping_sauce=["香油蒜泥", "干碟"],
        priority=22
    ),
    
    "huanghou": Ingredient(
        id="huanghou",
        name="黄喉",
        aliases=["猪黄喉", "牛黄喉"],
        category=Category.OFFAL,
        cooking_rule=CookingRule(
            base_seconds=20,
            crispy_seconds=15,
            tender_seconds=20,
            soft_seconds=40,
            min_safe_seconds=15,
            technique="比毛肚稍久，脆脆的口感",
            warning="煮太久变韧"
        ),
        nutrition=NutritionInfo(purine_level="高", calories_per_100g=95),
        dipping_sauce=["香油蒜泥"],
        priority=25
    ),
    
    "naohua": Ingredient(
        id="naohua",
        name="脑花",
        aliases=["猪脑花", "猪脑"],
        category=Category.OFFAL,
        cooking_rule=CookingRule(
            base_seconds=180,
            crispy_seconds=150,
            tender_seconds=180,
            soft_seconds=240,
            min_safe_seconds=150,
            technique="轻放入锅，不要搅动，慢慢炖煮",
            warning="必须完全煮熟，表面变白凝固"
        ),
        nutrition=NutritionInfo(purine_level="高", calories_per_100g=131),
        dipping_sauce=["香油蒜泥", "干碟"],
        priority=10  # 最先下锅
    ),
    
    # ========== 海鲜类 ==========
    "xiahua": Ingredient(
        id="xiahua",
        name="虾滑",
        aliases=["手打虾滑", "鲜虾滑"],
        category=Category.SEAFOOD,
        cooking_rule=CookingRule(
            base_seconds=90,
            crispy_seconds=60,
            tender_seconds=90,
            soft_seconds=120,
            min_safe_seconds=60,
            technique="勺子挖成球状下锅，浮起即熟",
            warning="生虾滑必须完全煮熟"
        ),
        nutrition=NutritionInfo(purine_level="高", calories_per_100g=87, allergens=["虾"]),
        dipping_sauce=["芥末酱油", "沙茶酱"],
        priority=40
    ),
    
    "xianxia": Ingredient(
        id="xianxia",
        name="鲜虾",
        aliases=["基围虾", "大虾", "活虾"],
        category=Category.SEAFOOD,
        cooking_rule=CookingRule(
            base_seconds=120,
            crispy_seconds=90,
            tender_seconds=120,
            soft_seconds=180,
            min_safe_seconds=90,
            technique="虾身变红弯曲即可",
            warning="必须完全变色才能食用"
        ),
        nutrition=NutritionInfo(purine_level="高", calories_per_100g=93, allergens=["虾"]),
        dipping_sauce=["芥末酱油", "蒜泥"],
        priority=45
    ),
    
    # ========== 丸滑类 ==========
    "niurouwan": Ingredient(
        id="niurouwan",
        name="牛肉丸",
        aliases=["手打牛丸", "潮汕牛肉丸"],
        category=Category.MEATBALL,
        cooking_rule=CookingRule(
            base_seconds=180,
            crispy_seconds=150,
            tender_seconds=180,
            soft_seconds=240,
            min_safe_seconds=150,
            technique="丸子浮起后再煮1-2分钟",
            warning="内部必须热透"
        ),
        nutrition=NutritionInfo(purine_level="中", calories_per_100g=220),
        dipping_sauce=["沙茶酱", "辣椒酱"],
        priority=15
    ),
    
    "yuwan": Ingredient(
        id="yuwan",
        name="鱼丸",
        aliases=["鱼蛋", "墨鱼丸", "包心鱼丸"],
        category=Category.MEATBALL,
        cooking_rule=CookingRule(
            base_seconds=150,
            crispy_seconds=120,
            tender_seconds=150,
            soft_seconds=200,
            min_safe_seconds=120,
            technique="浮起后煮1分钟"
        ),
        nutrition=NutritionInfo(purine_level="中", calories_per_100g=150, allergens=["鱼"]),
        dipping_sauce=["甜辣酱"],
        priority=18
    ),
    
    # ========== 蔬菜类 ==========
    "tudou": Ingredient(
        id="tudou",
        name="土豆片",
        aliases=["土豆", "马铃薯", "洋芋"],
        category=Category.VEGETABLE,
        cooking_rule=CookingRule(
            base_seconds=180,
            crispy_seconds=120,
            tender_seconds=180,
            soft_seconds=300,
            min_safe_seconds=120,
            technique="切薄片更易熟",
            warning="太厚可能外熟内生"
        ),
        nutrition=NutritionInfo(purine_level="低", calories_per_100g=77),
        dipping_sauce=["麻酱", "干碟"],
        priority=60
    ),
    
    "oujie": Ingredient(
        id="oujie",
        name="藕片",
        aliases=["莲藕", "藕"],
        category=Category.VEGETABLE,
        cooking_rule=CookingRule(
            base_seconds=180,
            crispy_seconds=120,
            tender_seconds=180,
            soft_seconds=360,
            min_safe_seconds=90,
            technique="脆藕少煮，粉藕多煮",
        ),
        nutrition=NutritionInfo(purine_level="低", calories_per_100g=74),
        dipping_sauce=["麻酱", "干碟"],
        priority=55
    ),
    
    "bocai": Ingredient(
        id="bocai",
        name="菠菜",
        aliases=["菠菜", "青菜"],
        category=Category.VEGETABLE,
        cooking_rule=CookingRule(
            base_seconds=30,
            crispy_seconds=20,
            tender_seconds=30,
            soft_seconds=60,
            min_safe_seconds=15,
            technique="烫软即可，保持翠绿"
        ),
        nutrition=NutritionInfo(purine_level="中", calories_per_100g=23),
        dipping_sauce=["麻酱", "蒜泥"],
        priority=80  # 最后下
    ),
    
    "shengcai": Ingredient(
        id="shengcai",
        name="生菜",
        aliases=["莴苣叶", "唛仔菜"],
        category=Category.VEGETABLE,
        cooking_rule=CookingRule(
            base_seconds=15,
            crispy_seconds=8,
            tender_seconds=15,
            soft_seconds=30,
            min_safe_seconds=8,
            technique="快烫即起，保持脆嫩"
        ),
        nutrition=NutritionInfo(purine_level="低", calories_per_100g=15),
        dipping_sauce=["麻酱"],
        priority=85
    ),
    
    "dongguapian": Ingredient(
        id="dongguapian",
        name="冬瓜",
        aliases=["冬瓜片"],
        category=Category.VEGETABLE,
        cooking_rule=CookingRule(
            base_seconds=240,
            crispy_seconds=180,
            tender_seconds=240,
            soft_seconds=420,
            min_safe_seconds=150,
            technique="煮至半透明，入味即可"
        ),
        nutrition=NutritionInfo(purine_level="低", calories_per_100g=12),
        dipping_sauce=["麻酱"],
        priority=50
    ),
    
    # ========== 豆制品 ==========
    "laodoufu": Ingredient(
        id="laodoufu",
        name="老豆腐",
        aliases=["北豆腐", "卤水豆腐"],
        category=Category.TOFU,
        cooking_rule=CookingRule(
            base_seconds=300,
            crispy_seconds=240,
            tender_seconds=300,
            soft_seconds=480,
            min_safe_seconds=180,
            technique="煮久入味，不易碎"
        ),
        nutrition=NutritionInfo(purine_level="低", calories_per_100g=81),
        dipping_sauce=["麻酱", "干碟"],
        priority=25
    ),
    
    "nendoufu": Ingredient(
        id="nendoufu",
        name="嫩豆腐",
        aliases=["内酯豆腐", "日本豆腐"],
        category=Category.TOFU,
        cooking_rule=CookingRule(
            base_seconds=120,
            crispy_seconds=90,
            tender_seconds=120,
            soft_seconds=180,
            min_safe_seconds=60,
            technique="轻放轻拿，容易碎"
        ),
        nutrition=NutritionInfo(purine_level="低", calories_per_100g=55),
        dipping_sauce=["酱油"],
        priority=70
    ),
    
    "fuzhu": Ingredient(
        id="fuzhu",
        name="腐竹",
        aliases=["干腐竹", "鲜腐竹"],
        category=Category.TOFU,
        cooking_rule=CookingRule(
            base_seconds=180,
            crispy_seconds=120,
            tender_seconds=180,
            soft_seconds=300,
            min_safe_seconds=90,
            technique="干腐竹需提前泡软"
        ),
        nutrition=NutritionInfo(purine_level="中", calories_per_100g=459),
        dipping_sauce=["麻酱"],
        priority=45
    ),
    
    # ========== 菌菇类 ==========
    "jinzhengu": Ingredient(
        id="jinzhengu",
        name="金针菇",
        aliases=["金针菇"],
        category=Category.MUSHROOM,
        cooking_rule=CookingRule(
            base_seconds=120,
            crispy_seconds=90,
            tender_seconds=120,
            soft_seconds=180,
            min_safe_seconds=90,
            technique="整把下锅，煮软即可",
            warning="难消化，细嚼慢咽"
        ),
        nutrition=NutritionInfo(purine_level="中", calories_per_100g=32),
        dipping_sauce=["麻酱", "干碟"],
        priority=50
    ),
    
    "xianggu": Ingredient(
        id="xianggu",
        name="香菇",
        aliases=["冬菇", "花菇"],
        category=Category.MUSHROOM,
        cooking_rule=CookingRule(
            base_seconds=240,
            crispy_seconds=180,
            tender_seconds=240,
            soft_seconds=360,
            min_safe_seconds=180,
            technique="十字切花，更易入味"
        ),
        nutrition=NutritionInfo(purine_level="高", calories_per_100g=34),
        dipping_sauce=["麻酱"],
        priority=35
    ),
    
    "pinggu": Ingredient(
        id="pinggu",
        name="平菇",
        aliases=["秀珍菇", "凤尾菇"],
        category=Category.MUSHROOM,
        cooking_rule=CookingRule(
            base_seconds=150,
            crispy_seconds=120,
            tender_seconds=150,
            soft_seconds=240,
            min_safe_seconds=120,
            technique="撕成小块更入味"
        ),
        nutrition=NutritionInfo(purine_level="中", calories_per_100g=26),
        dipping_sauce=["麻酱"],
        priority=48
    ),
    
    # ========== 主食类 ==========
    "fangbianmian": Ingredient(
        id="fangbianmian",
        name="方便面",
        aliases=["泡面", "火锅面"],
        category=Category.NOODLE,
        cooking_rule=CookingRule(
            base_seconds=180,
            crispy_seconds=120,
            tender_seconds=180,
            soft_seconds=300,
            min_safe_seconds=120,
            technique="等汤底精华，最后下"
        ),
        nutrition=NutritionInfo(purine_level="低", calories_per_100g=473),
        dipping_sauce=["直接吃"],
        priority=90
    ),
    
    "niangao": Ingredient(
        id="niangao",
        name="年糕",
        aliases=["韩式年糕", "宁波年糕"],
        category=Category.NOODLE,
        cooking_rule=CookingRule(
            base_seconds=240,
            crispy_seconds=180,
            tender_seconds=240,
            soft_seconds=360,
            min_safe_seconds=180,
            technique="煮软糯有嚼劲"
        ),
        nutrition=NutritionInfo(purine_level="低", calories_per_100g=154),
        dipping_sauce=["直接吃"],
        priority=88
    ),
    # ========== 联网检索补充（常见火锅食材）==========
    "yaxue": Ingredient(
        id="yaxue",
        name="鸭血",
        aliases=["血旺", "鸭血旺", "鲜鸭血"],
        category=Category.OFFAL,
        cooking_rule=CookingRule(
            base_seconds=300,
            crispy_seconds=180,
            tender_seconds=300,
            soft_seconds=600,
            min_safe_seconds=300,
            technique="煮至无血水、质地紧实",
            warning="必须完全煮熟，中心无血色"
        ),
        nutrition=NutritionInfo(purine_level="中", calories_per_100g=49),
        dipping_sauce=["干碟", "香油蒜泥"],
        priority=12
    ),
    "malaniurou": Ingredient(
        id="malaniurou",
        name="麻辣牛肉",
        aliases=["麻辣牛肉片", "腌牛肉"],
        category=Category.MEAT,
        cooking_rule=CookingRule(
            base_seconds=180,
            crispy_seconds=120,
            tender_seconds=180,
            soft_seconds=240,
            min_safe_seconds=120,
            technique="腌渍过可稍久煮，变色熟透即可",
            warning="含辣椒需注意辣度"
        ),
        nutrition=NutritionInfo(purine_level="中", calories_per_100g=200),
        dipping_sauce=["干碟", "香油"],
        priority=38
    ),
    "niushe": Ingredient(
        id="niushe",
        name="牛舌",
        aliases=["牛舌片", "厚切牛舌"],
        category=Category.MEAT,
        cooking_rule=CookingRule(
            base_seconds=30,
            crispy_seconds=20,
            tender_seconds=30,
            soft_seconds=60,
            min_safe_seconds=20,
            technique="薄切涮烫变色即可，厚切需多煮",
            warning="久煮会变韧"
        ),
        nutrition=NutritionInfo(purine_level="中", calories_per_100g=224),
        dipping_sauce=["香油蒜泥", "干碟"],
        priority=33
    ),
    "qingsun": Ingredient(
        id="qingsun",
        name="青笋",
        aliases=["莴笋", "莴笋片", "莴苣"],
        category=Category.VEGETABLE,
        cooking_rule=CookingRule(
            base_seconds=60,
            crispy_seconds=40,
            tender_seconds=60,
            soft_seconds=300,
            min_safe_seconds=40,
            technique="薄片快熟，煮至微软保持脆感",
            warning="煮太久易烂"
        ),
        nutrition=NutritionInfo(purine_level="低", calories_per_100g=14),
        dipping_sauce=["麻酱", "蒜泥"],
        priority=65
    ),
    "xiangcai": Ingredient(
        id="xiangcai",
        name="香菜",
        aliases=["芫荽", "香荽"],
        category=Category.VEGETABLE,
        cooking_rule=CookingRule(
            base_seconds=15,
            crispy_seconds=8,
            tender_seconds=15,
            soft_seconds=30,
            min_safe_seconds=8,
            technique="烫一下即可，保持清香"
        ),
        nutrition=NutritionInfo(purine_level="低", calories_per_100g=23),
        dipping_sauce=["麻酱", "直接吃"],
        priority=82
    ),
    "sunjian": Ingredient(
        id="sunjian",
        name="笋尖",
        aliases=["竹笋尖", "嫩笋", "笋片"],
        category=Category.VEGETABLE,
        cooking_rule=CookingRule(
            base_seconds=300,
            crispy_seconds=180,
            tender_seconds=300,
            soft_seconds=480,
            min_safe_seconds=120,
            technique="煮至入味，脆嫩或软糯视喜好"
        ),
        nutrition=NutritionInfo(purine_level="低", calories_per_100g=27),
        dipping_sauce=["麻酱", "干碟"],
        priority=52
    ),
    "haibaicai": Ingredient(
        id="haibaicai",
        name="海白菜",
        aliases=["海带芽", "裙带菜"],
        category=Category.OTHER,
        cooking_rule=CookingRule(
            base_seconds=300,
            crispy_seconds=120,
            tender_seconds=300,
            soft_seconds=420,
            min_safe_seconds=90,
            technique="泡发后下锅，煮软入味即可",
            warning="碘含量高，甲亢患者少食"
        ),
        nutrition=NutritionInfo(purine_level="低", calories_per_100g=16),
        dipping_sauce=["麻酱", "蒜泥"],
        priority=48
    ),
    "haidai": Ingredient(
        id="haidai",
        name="海带",
        aliases=["海带片", "海带结", "昆布"],
        category=Category.OTHER,
        cooking_rule=CookingRule(
            base_seconds=300,
            crispy_seconds=180,
            tender_seconds=300,
            soft_seconds=600,
            min_safe_seconds=120,
            technique="干海带需泡发，煮软糯",
            warning="碘含量高，不宜过量"
        ),
        nutrition=NutritionInfo(purine_level="低", calories_per_100g=64),
        dipping_sauce=["麻酱", "蒜泥"],
        priority=42
    ),
    "shaofen": Ingredient(
        id="shaofen",
        name="苕粉",
        aliases=["红薯粉", "宽粉", "火锅粉"],
        category=Category.NOODLE,
        cooking_rule=CookingRule(
            base_seconds=300,
            crispy_seconds=180,
            tender_seconds=300,
            soft_seconds=480,
            min_safe_seconds=180,
            technique="煮至透明软滑，不宜久煮易糊",
            warning="易糊锅，最后下或单独煮"
        ),
        nutrition=NutritionInfo(purine_level="低", calories_per_100g=337),
        dipping_sauce=["麻酱", "醋"],
        priority=86
    ),
    "wucanrou": Ingredient(
        id="wucanrou",
        name="午餐肉",
        aliases=["火腿午餐肉", "罐头午餐肉"],
        category=Category.MEATBALL,
        cooking_rule=CookingRule(
            base_seconds=60,
            crispy_seconds=45,
            tender_seconds=60,
            soft_seconds=120,
            min_safe_seconds=45,
            technique="切片下锅，煮热即可",
            warning="含盐高，不宜多食"
        ),
        nutrition=NutritionInfo(purine_level="低", calories_per_100g=229),
        dipping_sauce=["干碟", "直接吃"],
        priority=42
    ),
    "anchuandan": Ingredient(
        id="anchuandan",
        name="鹌鹑蛋",
        aliases=["鹌鹑蛋"],
        category=Category.OTHER,
        cooking_rule=CookingRule(
            base_seconds=180,
            crispy_seconds=120,
            tender_seconds=180,
            soft_seconds=300,
            min_safe_seconds=120,
            technique="带壳或剥壳下锅，煮透心",
            warning="必须煮熟透"
        ),
        nutrition=NutritionInfo(purine_level="低", calories_per_100g=158),
        dipping_sauce=["干碟", "麻酱"],
        priority=35
    ),
}

def get_all_ingredients() -> Dict[str, Ingredient]:
    """获取所有食材"""
    return INGREDIENTS_DATABASE

def get_ingredient_by_id(ingredient_id: str) -> Optional[Ingredient]:
    """根据ID获取食材"""
    return INGREDIENTS_DATABASE.get(ingredient_id)

def search_ingredient(keyword: str) -> List[Ingredient]:
    """模糊搜索食材（名称或别名）"""
    results = []
    keyword = keyword.lower().strip()
    for ingredient in INGREDIENTS_DATABASE.values():
        if keyword in ingredient.name.lower():
            results.append(ingredient)
        elif any(keyword in alias.lower() for alias in ingredient.aliases):
            results.append(ingredient)
    return results

def get_ingredients_by_category(category: Category) -> List[Ingredient]:
    """按分类获取食材"""
    return [i for i in INGREDIENTS_DATABASE.values() if i.category == category]


def export_cooking_times_to_json(filepath: str = None) -> str:
    """
    将涮煮时间数据导出为 JSON，便于大模型或外部程序读取。
    默认写入同目录下 火锅食材涮煮时间.json
    """
    import json
    if filepath is None:
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "火锅食材涮煮时间.json")
    out = {
        "description": "火锅食材涮煮时间数据库。时间单位：秒。base_seconds=标准涮煮时间，crispy_seconds=脆嫩，tender_seconds=软嫩，soft_seconds=软烂，min_safe_seconds=最低安全时间(必须熟透)。priority=建议下锅优先级，数值越小越先下。",
        "ingredients": []
    }
    for ing in INGREDIENTS_DATABASE.values():
        out["ingredients"].append({
            "id": ing.id,
            "name": ing.name,
            "aliases": ing.aliases,
            "category": ing.category.value,
            "base_seconds": ing.cooking_rule.base_seconds,
            "crispy_seconds": ing.cooking_rule.crispy_seconds,
            "tender_seconds": ing.cooking_rule.tender_seconds,
            "soft_seconds": ing.cooking_rule.soft_seconds,
            "min_safe_seconds": ing.cooking_rule.min_safe_seconds,
            "technique": ing.cooking_rule.technique,
            "warning": ing.cooking_rule.warning,
            "priority": ing.priority,
        })
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return filepath
