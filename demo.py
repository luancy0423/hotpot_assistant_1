#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
涮涮AI - 演示脚本
展示所有菜单输入方式和涮煮方案生成功能
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api import HotpotAssistantAPI
import json


def print_section(title: str):
    """打印分隔标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def demo_menu_api_input():
    """演示商家菜单API输入"""
    print_section("📱 方式1: 商家菜单API对接")
    
    api = HotpotAssistantAPI()
    
    # 1. 获取餐厅列表
    print("\n1️⃣ 获取支持的餐厅列表:")
    result = api.get_available_restaurants()
    for r in result.data['restaurants']:
        print(f"   - {r['name']} (ID: {r['id']}, 菜品数: {r['menu_item_count']})")
    
    # 2. 获取指定餐厅菜单
    print("\n2️⃣ 获取海底捞菜单:")
    result = api.input_from_menu_api("haidilao_001")
    
    print(f"   锅底选项:")
    for broth in result.data['broth_options']:
        print(f"   - {broth['name']} ¥{broth['price']} ({broth['type']})")
    
    print(f"\n   菜品列表 (部分):")
    for item in result.data['menu_items'][:8]:
        print(f"   - [{item['category']}] {item['name']} ¥{item['price']}")
    
    # 3. 选择菜品
    print("\n3️⃣ 用户选择菜品:")
    selected_ids = ["item_001", "item_005", "item_006", "item_009", "item_013", "item_021"]
    result = api.input_from_menu_api("haidilao_001", item_ids=selected_ids)
    print(f"   {result.message}")
    print(f"   对应食材: {result.data['ingredient_names']}")
    
    return result.data['ingredient_names']


def demo_ocr_input():
    """演示OCR拍照识别"""
    print_section("📷 方式2: 拍照识别 (OCR)")
    
    api = HotpotAssistantAPI()
    
    print("\n模拟场景: 用户拍摄火锅店菜单/小票照片")
    print("（实际使用时会调用百度/阿里OCR API）")
    
    # 模拟OCR识别
    result = api.input_from_ocr()
    
    print(f"\n识别结果:")
    print(f"   状态: {'✅ 成功' if result.success else '❌ 失败'}")
    print(f"   置信度: {result.data['confidence']:.0%}")
    print(f"   识别出的食材: {result.data['ingredient_names']}")
    print(f"\n   原始识别文本预览:")
    for line in result.data['raw_text'].split('\n')[:5]:
        if line.strip():
            print(f"   | {line.strip()}")
    
    return result.data['ingredient_names']


def demo_voice_input():
    """演示语音识别输入"""
    print_section("🎤 方式3: 语音识别")
    
    api = HotpotAssistantAPI()
    
    print("\n模拟场景: 用户语音说出想吃的菜品")
    print("（实际使用时会调用讯飞/百度语音API）")
    
    # 模拟语音识别
    result = api.input_from_voice()
    
    print(f"\n识别结果:")
    print(f"   语音转写: \"{result.data['transcript']}\"")
    print(f"   置信度: {result.data['confidence']:.0%}")
    print(f"   提取出的食材: {result.data['ingredient_names']}")
    
    return result.data['ingredient_names']


def demo_text_input():
    """演示文本输入"""
    print_section("⌨️ 方式4: 文本输入")
    
    api = HotpotAssistantAPI()
    
    user_input = "我要肥牛、毛肚、鸭肠、脑花、虾滑、土豆片、藕片、金针菇、菠菜，锅底要麻辣红汤"
    
    print(f"\n用户输入: \"{user_input}\"")
    
    result = api.input_from_text(user_input)
    
    print(f"\n解析结果:")
    print(f"   {result.message}")
    print(f"   食材列表: {result.data['ingredient_names']}")
    
    return result.data['ingredient_names']


def demo_manual_selection():
    """演示手动选择"""
    print_section("✋ 方式5: 手动选择")
    
    api = HotpotAssistantAPI()
    
    # 获取可用食材
    print("\n可选食材分类:")
    
    categories = ["MEAT", "OFFAL", "SEAFOOD", "VEGETABLE", "MUSHROOM"]
    for cat in categories:
        result = api.get_available_ingredients(category=cat)
        names = [i['name'] for i in result.data['ingredients']]
        print(f"   {cat}: {', '.join(names[:5])}...")
    
    # 用户选择
    selected_ids = ["feiniurou", "maodu", "yachang", "xiahua", "tudou", "jinzhengu"]
    result = api.input_manual(selected_ids)
    
    print(f"\n用户选择的食材ID: {selected_ids}")
    print(f"对应食材: {result.data['ingredient_names']}")
    
    return result.data['ingredient_names']


def demo_cooking_plan(ingredients: list):
    """演示涮煮方案生成"""
    print_section("🔥 涮煮方案生成")
    
    api = HotpotAssistantAPI()
    
    print(f"\n输入食材: {ingredients}")
    print(f"锅底类型: 麻辣红汤")
    print(f"口感偏好: 标准")
    print(f"用户模式: 普通")
    
    result = api.generate_cooking_plan(
        ingredient_names=ingredients,
        broth_type="SPICY",
        texture="STANDARD",
        user_mode="NORMAL"
    )
    
    if not result.success:
        print(f"❌ 生成失败: {result.error}")
        return
    
    plan = result.data
    
    print(f"\n{'─' * 50}")
    print(f"📊 方案概览")
    print(f"{'─' * 50}")
    print(f"   总时长: {plan['timeline']['total_duration_display']}")
    print(f"   食材数: {len(plan['timeline']['items'])}种")
    
    print(f"\n{'─' * 50}")
    print(f"📋 涮煮顺序 (按下锅优先级排列)")
    print(f"{'─' * 50}")
    
    for i, item in enumerate(plan['timeline']['items'], 1):
        print(f"\n   {i}. 【{item['ingredient_name']}】")
        print(f"      分类: {item['category']}")
        print(f"      时间: {item['cooking_display']}")
        if item['technique']:
            print(f"      技巧: {item['technique']}")
        if item['warning']:
            print(f"      ⚠️ 注意: {item['warning']}")
        print(f"      蘸料: {', '.join(item['dipping_sauce'])}")
        if item['is_must_cook_through']:
            print(f"      🔴 必须煮熟!")
        if item['purine_warning']:
            print(f"      ⚡ 高嘌呤")
    
    print(f"\n{'─' * 50}")
    print(f"⏱️ 时间线事件 (前15个)")
    print(f"{'─' * 50}")
    
    for event in plan['timeline']['events'][:15]:
        time_str = f"{event['time_seconds'] // 60:02d}:{event['time_seconds'] % 60:02d}"
        action_emoji = "⬇️" if event['action'] == "下锅" else "⬆️"
        print(f"   [{time_str}] {action_emoji} {event['message']}")
    
    print(f"\n{'─' * 50}")
    print(f"🚨 安全提醒")
    print(f"{'─' * 50}")
    for warning in plan['safety_warnings']:
        print(f"   {warning}")
    
    print(f"\n{'─' * 50}")
    print(f"💚 健康贴士")
    print(f"{'─' * 50}")
    for tip in plan['health_tips']:
        print(f"   {tip}")
    
    print(f"\n{'─' * 50}")
    print(f"🥢 蘸料推荐")
    print(f"{'─' * 50}")
    for food, sauces in plan['sauce_recommendations'].items():
        print(f"   {food}: {' / '.join(sauces)}")


def demo_different_modes():
    """演示不同用户模式"""
    print_section("👥 不同用户模式对比")
    
    api = HotpotAssistantAPI()
    
    ingredients = ["肥牛", "毛肚", "脑花"]
    modes = [
        ("NORMAL", "普通模式"),
        ("ELDERLY", "老人模式"),
        ("CHILD", "儿童模式"),
        ("QUICK", "快手模式"),
    ]
    
    print(f"\n测试食材: {ingredients}")
    print(f"\n{'食材':<10} | {'普通':>8} | {'老人':>8} | {'儿童':>8} | {'快手':>8}")
    print("-" * 55)
    
    results = {}
    for mode_key, mode_name in modes:
        result = api.generate_cooking_plan(
            ingredient_names=ingredients,
            broth_type="SPICY",
            user_mode=mode_key
        )
        for item in result.data['timeline']['items']:
            if item['ingredient_name'] not in results:
                results[item['ingredient_name']] = {}
            results[item['ingredient_name']][mode_key] = item['cooking_seconds']
    
    for food_name, times in results.items():
        row = f"{food_name:<10}"
        for mode_key, _ in modes:
            t = times.get(mode_key, 0)
            row += f" | {t:>6}秒"
        print(row)


def main():
    """主函数"""
    print("\n" + "🍲" * 30)
    print("      涮涮AI - 智能火锅助手 演示")
    print("🍲" * 30)
    
    # 演示所有输入方式
    print("\n\n" + "█" * 60)
    print("  第一部分: 菜单输入方式演示")
    print("█" * 60)
    
    ingredients1 = demo_menu_api_input()
    ingredients2 = demo_ocr_input()
    ingredients3 = demo_voice_input()
    ingredients4 = demo_text_input()
    ingredients5 = demo_manual_selection()
    
    # 使用文本输入的结果演示涮煮方案
    print("\n\n" + "█" * 60)
    print("  第二部分: 涮煮方案生成演示")
    print("█" * 60)
    
    demo_cooking_plan(ingredients4)
    
    # 演示不同模式
    print("\n\n" + "█" * 60)
    print("  第三部分: 个性化模式演示")
    print("█" * 60)
    
    demo_different_modes()
    
    print("\n\n" + "🎉" * 20)
    print("      演示完成！祝您火锅愉快！")
    print("🎉" * 20 + "\n")


if __name__ == "__main__":
    main()
