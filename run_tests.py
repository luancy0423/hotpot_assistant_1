#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
涮涮AI - 快速自动化测试
不依赖 pytest，直接运行：python run_tests.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run(name: str, fn):
    try:
        fn()
        print(f"  ✅ {name}")
        return True
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        return False

def test_api_text_input():
    """文本输入 → 解析食材"""
    from api import HotpotAssistantAPI
    api = HotpotAssistantAPI(use_mock=True)
    r = api.input_from_text("肥牛、毛肚、鸭肠")
    assert r.success and "肥牛" in r.data["ingredient_names"] and len(r.data["ingredient_names"]) >= 2

def test_api_generate_plan_rule():
    """生成涮煮方案（固定规则排序）"""
    from api import HotpotAssistantAPI
    api = HotpotAssistantAPI(use_mock=True)
    r = api.generate_cooking_plan(
        ingredient_names=["脑花", "毛肚", "肥牛", "菠菜"],
        broth_type="SPICY",
        user_mode="NORMAL",
    )
    assert r.success
    items = r.data["timeline"]["items"]
    assert len(items) == 4
    names = [x["ingredient_name"] for x in items]
    assert "脑花" in names and "毛肚" in names
    assert r.data["timeline"]["total_duration_seconds"] > 0
    assert len(r.data["safety_warnings"]) > 0

def test_api_custom_ingredients():
    """特色食材：仅自定义 → 生成方案"""
    from api import HotpotAssistantAPI
    api = HotpotAssistantAPI(use_mock=True)
    r = api.generate_cooking_plan(
        ingredient_names=[],
        custom_ingredients=[
            {"name": "田鸡", "cooking_seconds": 90},
            {"name": "蛇段", "cooking_seconds": 120},
        ],
        broth_type="SPICY",
        user_mode="NORMAL",
    )
    assert r.success
    names = [x["ingredient_name"] for x in r.data["timeline"]["items"]]
    assert "田鸡" in names and "蛇段" in names
    assert any("特色" in w for w in r.data["safety_warnings"])

def test_api_mixed_common_and_custom():
    """常见食材 + 特色食材 混合"""
    from api import HotpotAssistantAPI
    api = HotpotAssistantAPI(use_mock=True)
    r = api.generate_cooking_plan(
        ingredient_names=["毛肚", "肥牛"],
        custom_ingredients=[{"name": "田鸡", "cooking_seconds": 90}],
        broth_type="CLEAR",
        user_mode="NORMAL",
    )
    assert r.success
    names = [x["ingredient_name"] for x in r.data["timeline"]["items"]]
    assert "毛肚" in names and "肥牛" in names and "田鸡" in names
    assert len(r.data["timeline"]["items"]) == 3

def test_user_preferences():
    """用户偏好：保存与读取"""
    from api import HotpotAssistantAPI
    from data.user_preferences import load_preferences, save_preferences
    save_preferences(broth_type="TOMATO", texture="TENDER", user_mode="NORMAL", allergens_to_avoid=[])
    prefs = load_preferences()
    assert prefs.get("broth_type") == "TOMATO"
    api = HotpotAssistantAPI(use_mock=True)
    r = api.get_user_preferences()
    assert r.success and r.data.get("broth_type") == "TOMATO"

def test_context_loader():
    """上下文工程：模板与知识加载"""
    from context.context_loader import load_prompt, get_domain_knowledge, build_sort_prompt
    system = load_prompt("sort", "system")
    assert system and "JSON" in system
    knowledge = get_domain_knowledge()
    assert "下锅" in knowledge or "涮" in knowledge
    # 构造一个简单 items 列表（仅需 name, category, cooking_seconds, technique）
    class FakeItem:
        ingredient_name = "脑花"
        category = "内脏类"
        cooking_seconds = 180
        technique = "慢煮"
    sys_str, user_str = build_sort_prompt([FakeItem()], "红汤/麻辣", "普通模式", None)
    assert sys_str and user_str and "脑花" in user_str

def test_parse_custom_ingredients():
    """Gradio 解析：特色食材文本框"""
    from app_gradio import _parse_custom_ingredients
    text = "田鸡 90\n蛇段 2分钟\n牛蛙, 120"
    out, msg = _parse_custom_ingredients(text)
    assert len(out) == 3
    assert out[0]["name"] == "田鸡" and out[0]["cooking_seconds"] == 90
    assert out[1]["name"] == "蛇段" and out[1]["cooking_seconds"] == 120
    assert out[2]["name"] == "牛蛙" and out[2]["cooking_seconds"] == 120
    out2, msg2 = _parse_custom_ingredients("只有名称")
    assert len(out2) == 1 and out2[0]["name"] == "只有名称" and out2[0]["cooking_seconds"] == 120

def test_ingredients_db_and_export():
    """食材库与 JSON 导出"""
    from data.ingredients_db import INGREDIENTS_DATABASE, get_ingredient_by_id, search_ingredient, export_cooking_times_to_json
    assert len(INGREDIENTS_DATABASE) >= 30
    ing = get_ingredient_by_id("maodu")
    assert ing and ing.name == "毛肚"
    results = search_ingredient("鸭血")
    assert results and any(i.name == "鸭血" for i in results)
    path = export_cooking_times_to_json()
    assert os.path.isfile(path)
    import json
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "ingredients" in data and len(data["ingredients"]) >= 30

def main():
    print("\n🍲 涮涮AI - 自动化测试\n")
    tests = [
        ("API 文本输入", test_api_text_input),
        ("API 生成方案(规则)", test_api_generate_plan_rule),
        ("API 仅特色食材", test_api_custom_ingredients),
        ("API 常见+特色混合", test_api_mixed_common_and_custom),
        ("用户偏好 保存/读取", test_user_preferences),
        ("上下文 loader", test_context_loader),
        ("解析特色食材输入", test_parse_custom_ingredients),
        ("食材库与 JSON 导出", test_ingredients_db_and_export),
    ]
    ok = 0
    for name, fn in tests:
        if run(name, fn):
            ok += 1
    print(f"\n通过 {ok}/{len(tests)} 项\n")
    sys.exit(0 if ok == len(tests) else 1)

if __name__ == "__main__":
    main()
