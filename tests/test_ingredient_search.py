# -*- coding: utf-8 -*-
"""
涮涮AI - 智能食材搜索模块单元测试
"""

from data.ingredients_db import search_ingredient
from data.ingredient_search import (
    chinese_to_pinyin,
    get_pinyin_initials,
    levenshtein_distance,
    similarity_ratio,
    cosine_similarity,
    smart_search_ingredient,
    text_to_query_vector,
    get_ingredient_vector,
)
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_pinyin_conversion():
    """测试拼音转换"""
    print("\n=== 测试拼音转换 ===")

    test_cases = [
        ("毛肚", "maodu"),
        ("肥牛", "feiniu"),
        ("鸭肠", "yachang"),
        ("虾滑", "xiahua"),
        ("牛肉丸", "niurouwan"),
    ]

    for chinese, expected_pinyin in test_cases:
        result = chinese_to_pinyin(chinese)
        status = "✓" if result == expected_pinyin else "✗"
        print(f"  {status} {chinese} -> {result} (期望: {expected_pinyin})")


def test_pinyin_initials():
    """测试拼音首字母"""
    print("\n=== 测试拼音首字母 ===")

    test_cases = [
        ("毛肚", "md"),
        ("肥牛", "fn"),
        ("鸭肠", "yc"),
        ("虾滑", "xh"),
    ]

    for chinese, expected_initials in test_cases:
        result = get_pinyin_initials(chinese)
        status = "✓" if result == expected_initials else "✗"
        print(f"  {status} {chinese} -> {result} (期望: {expected_initials})")


def test_levenshtein_distance():
    """测试编辑距离"""
    print("\n=== 测试编辑距离 ===")

    test_cases = [
        ("毛杜", "毛肚", 1),  # 杜->肚，1次替换
        ("鸭长", "鸭肠", 1),  # 长->肠，1次替换
        ("肥年", "肥牛", 1),  # 年->牛，1次替换
        ("same", "same", 0),  # 相同，0次
    ]

    for s1, s2, expected in test_cases:
        result = levenshtein_distance(s1, s2)
        status = "✓" if result == expected else "✗"
        print(f"  {status} distance('{s1}', '{s2}') = {result} (期望: {expected})")


def test_similarity_ratio():
    """测试相似度计算"""
    print("\n=== 测试相似度计算 ===")

    test_cases = [
        ("毛杜", "毛肚", 0.5),  # 1/2 相同
        ("鸭长", "鸭肠", 0.5),
        ("same", "same", 1.0),
    ]

    for s1, s2, expected_min in test_cases:
        result = similarity_ratio(s1, s2)
        status = "✓" if result >= expected_min else "✗"
        print(f"  {status} similarity('{s1}', '{s2}') = {result:.2f}")


def test_smart_search():
    """测试智能搜索"""
    print("\n=== 测试智能搜索 ===")

    test_cases = [
        # (查询词, 期望第一个结果, 匹配类型)
        ("毛肚", "毛肚", "精确匹配"),
        ("maodu", "毛肚", "拼音匹配"),
        ("md", "毛肚", "首字母匹配"),
        ("毛杜", "毛肚", "拼音/错别字"),
        ("鸭长", "鸭肠", "拼音/错别字"),
        ("feiniu", "肥牛卷", "拼音匹配"),
        ("肥牛", "肥牛卷", "精确匹配"),
        ("虾", "虾滑", "精确匹配"),
        ("豆腐", "老豆腐", "精确匹配"),
    ]

    for query, expected_first, match_type in test_cases:
        results = smart_search_ingredient(query, top_k=3)
        if results:
            actual_first = results[0].ingredient.name
            status = "✓" if actual_first == expected_first else "✗"
            print(
                f"  {status} '{query}' -> {actual_first} (期望: {expected_first}) [{match_type}]")
        else:
            print(f"  ✗ '{query}' -> 无结果 (期望: {expected_first})")


def test_semantic_search():
    """测试语义相似度搜索"""
    print("\n=== 测试语义相似度 ===")

    # 测试分类语义匹配
    test_cases = [
        ("牛", ["肉类"]),  # 应该匹配肉类
        ("虾", ["海鲜类"]),  # 应该匹配海鲜
        ("豆腐", ["豆制品"]),  # 应该匹配豆制品
    ]

    for query, expected_categories in test_cases:
        results = smart_search_ingredient(query, top_k=5)
        if results:
            top_category = results[0].ingredient.category.value
            status = "✓" if top_category in expected_categories else "✗"
            print(f"  {status} '{query}' -> 分类: {top_category}")


def test_backward_compatibility():
    """测试与原接口的兼容性"""
    print("\n=== 测试向后兼容性 ===")

    # 测试默认启用智能搜索
    results = search_ingredient("毛肚")
    status = "✓" if len(results) > 0 and results[0].name == "毛肚" else "✗"
    print(f"  {status} search_ingredient('毛肚') 默认启用智能搜索")

    # 测试禁用智能搜索
    results_old = search_ingredient("毛肚", use_smart_search=False)
    status = "✓" if len(results_old) > 0 else "✗"
    print(f"  {status} search_ingredient('毛肚', use_smart_search=False) 回退模式")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("智能食材搜索模块单元测试")
    print("=" * 60)

    test_pinyin_conversion()
    test_pinyin_initials()
    test_levenshtein_distance()
    test_similarity_ratio()
    test_smart_search()
    test_semantic_search()
    test_backward_compatibility()

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
