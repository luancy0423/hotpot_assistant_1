# -*- coding: utf-8 -*-
"""
涮涮AI - 商家菜单API模拟
模拟火锅店的菜单数据接口
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import json

class MenuItemSize(Enum):
    """菜品规格"""
    SMALL = "小份"
    REGULAR = "中份"
    LARGE = "大份"

@dataclass
class MenuItem:
    """菜单项"""
    id: str                          # 菜品ID
    name: str                        # 菜品名称
    category: str                    # 分类
    price: float                     # 价格
    size: MenuItemSize = MenuItemSize.REGULAR
    description: str = ""            # 描述
    image_url: str = ""              # 图片URL
    ingredient_ids: List[str] = field(default_factory=list)  # 对应的食材ID
    is_available: bool = True        # 是否可售
    spicy_level: int = 0             # 辣度 0-5

@dataclass
class BrothOption:
    """锅底选项"""
    id: str
    name: str
    price: float
    broth_type: str                  # 对应BrothType
    spicy_level: int = 0
    description: str = ""

@dataclass 
class RestaurantMenu:
    """餐厅完整菜单"""
    restaurant_id: str
    restaurant_name: str
    menu_items: List[MenuItem]
    broth_options: List[BrothOption]
    updated_at: str

# ============== 模拟餐厅数据 ==============

MOCK_RESTAURANTS: Dict[str, RestaurantMenu] = {
    "haidilao_001": RestaurantMenu(
        restaurant_id="haidilao_001",
        restaurant_name="海底捞火锅(朝阳店)",
        broth_options=[
            BrothOption("broth_001", "麻辣锅底", 88.0, "SPICY", spicy_level=4, description="川味经典"),
            BrothOption("broth_002", "清汤锅底", 68.0, "CLEAR", description="滋补养生"),
            BrothOption("broth_003", "番茄锅底", 78.0, "TOMATO", description="酸甜开胃"),
            BrothOption("broth_004", "菌汤锅底", 88.0, "MUSHROOM", description="鲜香醇厚"),
        ],
        menu_items=[
            # 肉类
            MenuItem("item_001", "精品肥牛", "肉类", 58.0, description="雪花纹理，入口即化", ingredient_ids=["feiniurou"]),
            MenuItem("item_002", "M5和牛", "肉类", 128.0, description="顶级和牛", ingredient_ids=["feiniurou"]),
            MenuItem("item_003", "精品肥羊", "肉类", 52.0, ingredient_ids=["feiyangrou"]),
            MenuItem("item_004", "鲜切牛肉", "肉类", 68.0, ingredient_ids=["niuroupian"]),
            # 内脏
            MenuItem("item_005", "极品鲜毛肚", "内脏", 68.0, description="七上八下，脆嫩爽口", ingredient_ids=["maodu"]),
            MenuItem("item_006", "脆鸭肠", "内脏", 38.0, ingredient_ids=["yachang"]),
            MenuItem("item_007", "鲜黄喉", "内脏", 42.0, ingredient_ids=["huanghou"]),
            MenuItem("item_008", "猪脑花", "内脏", 28.0, description="绵软香滑", ingredient_ids=["naohua"]),
            # 海鲜
            MenuItem("item_009", "手打虾滑", "海鲜", 48.0, ingredient_ids=["xiahua"]),
            MenuItem("item_010", "基围虾", "海鲜", 88.0, ingredient_ids=["xianxia"]),
            # 丸类
            MenuItem("item_011", "潮汕牛肉丸", "丸类", 38.0, ingredient_ids=["niurouwan"]),
            MenuItem("item_012", "墨鱼丸", "丸类", 32.0, ingredient_ids=["yuwan"]),
            # 蔬菜
            MenuItem("item_013", "土豆片", "蔬菜", 16.0, ingredient_ids=["tudou"]),
            MenuItem("item_014", "藕片", "蔬菜", 18.0, ingredient_ids=["oujie"]),
            MenuItem("item_015", "菠菜", "蔬菜", 14.0, ingredient_ids=["bocai"]),
            MenuItem("item_016", "生菜", "蔬菜", 12.0, ingredient_ids=["shengcai"]),
            MenuItem("item_017", "冬瓜", "蔬菜", 14.0, ingredient_ids=["dongguapian"]),
            # 豆制品
            MenuItem("item_018", "老豆腐", "豆制品", 14.0, ingredient_ids=["laodoufu"]),
            MenuItem("item_019", "嫩豆腐", "豆制品", 12.0, ingredient_ids=["nendoufu"]),
            MenuItem("item_020", "腐竹", "豆制品", 16.0, ingredient_ids=["fuzhu"]),
            # 菌菇
            MenuItem("item_021", "金针菇", "菌菇", 16.0, ingredient_ids=["jinzhengu"]),
            MenuItem("item_022", "香菇", "菌菇", 18.0, ingredient_ids=["xianggu"]),
            MenuItem("item_023", "平菇", "菌菇", 14.0, ingredient_ids=["pinggu"]),
            # 主食
            MenuItem("item_024", "火锅面", "主食", 12.0, ingredient_ids=["fangbianmian"]),
            MenuItem("item_025", "年糕", "主食", 18.0, ingredient_ids=["niangao"]),
        ],
        updated_at="2024-01-15T10:00:00Z"
    ),
    
    "xiaolongkan_001": RestaurantMenu(
        restaurant_id="xiaolongkan_001", 
        restaurant_name="小龙坎火锅(三里屯店)",
        broth_options=[
            BrothOption("broth_101", "牛油麻辣锅", 98.0, "SPICY", spicy_level=5, description="正宗川渝牛油"),
            BrothOption("broth_102", "鸳鸯锅底", 108.0, "SPICY", spicy_level=3, description="一锅两味"),
            BrothOption("broth_103", "清油锅底", 88.0, "SPICY", spicy_level=3, description="清爽麻辣"),
        ],
        menu_items=[
            MenuItem("item_101", "鲜毛肚", "内脏", 72.0, ingredient_ids=["maodu"]),
            MenuItem("item_102", "极品肥牛", "肉类", 62.0, ingredient_ids=["feiniurou"]),
            MenuItem("item_103", "鸭肠", "内脏", 42.0, ingredient_ids=["yachang"]),
            MenuItem("item_104", "牛肉丸", "丸类", 36.0, ingredient_ids=["niurouwan"]),
            MenuItem("item_105", "老豆腐", "豆制品", 16.0, ingredient_ids=["laodoufu"]),
            MenuItem("item_106", "土豆片", "蔬菜", 14.0, ingredient_ids=["tudou"]),
            MenuItem("item_107", "金针菇", "菌菇", 14.0, ingredient_ids=["jinzhengu"]),
        ],
        updated_at="2024-01-15T10:00:00Z"
    )
}

# ============== 模拟API接口 ==============

class MockMenuAPI:
    """模拟商家菜单API"""
    
    @staticmethod
    def get_restaurant_list() -> List[Dict]:
        """获取餐厅列表"""
        return [
            {
                "id": menu.restaurant_id,
                "name": menu.restaurant_name,
                "menu_item_count": len(menu.menu_items)
            }
            for menu in MOCK_RESTAURANTS.values()
        ]
    
    @staticmethod
    def get_menu(restaurant_id: str) -> Optional[RestaurantMenu]:
        """获取餐厅完整菜单"""
        return MOCK_RESTAURANTS.get(restaurant_id)
    
    @staticmethod
    def get_menu_items(restaurant_id: str, category: str = None) -> List[MenuItem]:
        """获取菜品列表，可按分类筛选"""
        menu = MOCK_RESTAURANTS.get(restaurant_id)
        if not menu:
            return []
        
        items = menu.menu_items
        if category:
            items = [item for item in items if item.category == category]
        return items
    
    @staticmethod
    def get_broth_options(restaurant_id: str) -> List[BrothOption]:
        """获取锅底选项"""
        menu = MOCK_RESTAURANTS.get(restaurant_id)
        return menu.broth_options if menu else []
    
    @staticmethod
    def search_menu_item(restaurant_id: str, keyword: str) -> List[MenuItem]:
        """搜索菜品"""
        menu = MOCK_RESTAURANTS.get(restaurant_id)
        if not menu:
            return []
        
        keyword = keyword.lower()
        return [
            item for item in menu.menu_items
            if keyword in item.name.lower() or keyword in item.description.lower()
        ]

# 模拟用户订单数据
@dataclass
class OrderItem:
    """订单项"""
    menu_item_id: str
    menu_item_name: str
    quantity: int
    ingredient_ids: List[str]

@dataclass 
class UserOrder:
    """用户订单"""
    order_id: str
    restaurant_id: str
    broth_type: str
    items: List[OrderItem]
    created_at: str

# 模拟订单
MOCK_ORDERS: Dict[str, UserOrder] = {
    "order_001": UserOrder(
        order_id="order_001",
        restaurant_id="haidilao_001",
        broth_type="SPICY",
        items=[
            OrderItem("item_001", "精品肥牛", 1, ["feiniurou"]),
            OrderItem("item_005", "极品鲜毛肚", 1, ["maodu"]),
            OrderItem("item_006", "脆鸭肠", 1, ["yachang"]),
            OrderItem("item_009", "手打虾滑", 1, ["xiahua"]),
            OrderItem("item_013", "土豆片", 1, ["tudou"]),
            OrderItem("item_015", "菠菜", 1, ["bocai"]),
            OrderItem("item_021", "金针菇", 1, ["jinzhengu"]),
        ],
        created_at="2024-01-15T18:30:00Z"
    )
}

class MockOrderAPI:
    """模拟订单API"""
    
    @staticmethod
    def get_order(order_id: str) -> Optional[UserOrder]:
        """获取订单详情"""
        return MOCK_ORDERS.get(order_id)
    
    @staticmethod
    def create_order(restaurant_id: str, broth_type: str, item_ids: List[str]) -> UserOrder:
        """创建订单"""
        import uuid
        from datetime import datetime
        
        menu = MOCK_RESTAURANTS.get(restaurant_id)
        if not menu:
            raise ValueError(f"Restaurant {restaurant_id} not found")
        
        items = []
        for item_id in item_ids:
            menu_item = next((i for i in menu.menu_items if i.id == item_id), None)
            if menu_item:
                items.append(OrderItem(
                    menu_item_id=menu_item.id,
                    menu_item_name=menu_item.name,
                    quantity=1,
                    ingredient_ids=menu_item.ingredient_ids
                ))
        
        order = UserOrder(
            order_id=f"order_{uuid.uuid4().hex[:8]}",
            restaurant_id=restaurant_id,
            broth_type=broth_type,
            items=items,
            created_at=datetime.now().isoformat()
        )
        
        MOCK_ORDERS[order.order_id] = order
        return order
