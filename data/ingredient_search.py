# -*- coding: utf-8 -*-
"""
涮涮AI - 智能食材搜索模块
支持：语义相似度、拼音匹配、错别字纠正
"""

from data.ingredients_db import Ingredient, INGREDIENTS_DATABASE
import re
import os
import sys
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from difflib import SequenceMatcher

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ==================== 1. 拼音转换 ====================

# 简化的汉字-拼音映射表（常用火锅食材相关汉字）
# 实际项目中可使用 pypinyin 库，这里为减少依赖使用内置映射
PINYIN_MAP = {
    # === 常用字 ===
    '毛': 'mao', '肥': 'fei', '瘦': 'shou', '嫩': 'nen', '鲜': 'xian', '老': 'lao',
    '香': 'xiang', '麻': 'ma', '辣': 'la', '清': 'qing', '红': 'hong', '白': 'bai',
    '黑': 'hei', '青': 'qing', '金': 'jin', '银': 'yin', '紫': 'zi', '绿': 'lv',
    '杜': 'du',  # 错别字"毛杜"的杜
    '长': 'chang', '常': 'chang',  # 错别字"鸭长"的长

    # === 肉类 ===
    '牛': 'niu', '羊': 'yang', '猪': 'zhu', '鸡': 'ji', '鸭': 'ya', '鹅': 'e',
    '肉': 'rou', '卷': 'juan', '片': 'pian', '排': 'pai', '骨': 'gu', '蹄': 'ti',
    '五': 'wu', '花': 'hua', '梅': 'mei', '里': 'li', '脊': 'ji', '胸': 'xiong',
    '腿': 'tui', '颈': 'jing', '舌': 'she', '肚': 'du', '脏': 'zang',

    # === 内脏类 ===
    '肠': 'chang', '肝': 'gan', '腰': 'yao', '脑': 'nao', '胗': 'zhen', '肫': 'zhun',
    '喉': 'hou', '血': 'xue', '掌': 'zhang', '爪': 'zhao', '凤': 'feng',

    # === 海鲜类 ===
    '虾': 'xia', '鱼': 'yu', '蟹': 'xie', '贝': 'bei', '鱿': 'you', '墨': 'mo',
    '蛏': 'cheng', '蛤': 'ge', '蚌': 'bang', '扇': 'shan', '蚝': 'hao', '螺': 'luo',
    '鲍': 'bao', '参': 'shen', '翅': 'chi', '仁': 'ren', '滑': 'hua',

    # === 丸滑类 ===
    '丸': 'wan', '球': 'qiu', '福': 'fu', '袋': 'dai', '籽': 'zi', '撒': 'sa',
    '尿': 'niao', '爆': 'bao', '浆': 'jiang', '芝': 'zhi', '士': 'shi', '心': 'xin',

    # === 蔬菜类 ===
    '菠': 'bo', '菜': 'cai', '生': 'sheng', '油': 'you', '麦': 'mai', '娃': 'wa',
    '茼': 'tong', '蒿': 'hao', '莴': 'wo', '苣': 'ju', '笋': 'sun', '萝': 'luo',
    '卜': 'bo', '冬': 'dong', '瓜': 'gua', '南': 'nan', '黄': 'huang', '丝': 'si',
    '藕': 'ou', '莲': 'lian', '玉': 'yu', '米': 'mi', '山': 'shan',
    '药': 'yao', '土': 'tu', '芹': 'qin', '韭': 'jiu', '葱': 'cong',
    '姜': 'jiang', '蒜': 'suan', '椒': 'jiao', '番': 'fan', '茄': 'qie',

    # === 菌菇类 ===
    '菇': 'gu', '蘑': 'mo', '耳': 'er', '菌': 'jun', '猴': 'hou',
    '头': 'tou', '杏': 'xing', '茶': 'cha', '树': 'shu', '枞': 'cong', '平': 'ping',
    '针': 'zhen', '草': 'cao', '口': 'kou', '双': 'shuang', '孢': 'bao', '秀': 'xiu',
    '珍': 'zhen',

    # === 豆制品 ===
    '豆': 'dou', '腐': 'fu', '皮': 'pi', '竹': 'zhu', '千': 'qian', '张': 'zhang',
    '泡': 'pao', '冻': 'dong', '芽': 'ya', '苗': 'miao', '浆': 'jiang', '干': 'gan',

    # === 主食类 ===
    '面': 'mian', '粉': 'fen', '米': 'mi', '饭': 'fan', '年': 'nian', '糕': 'gao',
    '饺': 'jiao', '馄': 'hun', '饨': 'tun', '抄': 'chao', '手': 'shou', '云': 'yun',
    '吞': 'tun', '扁': 'bian', '食': 'shi', '粿': 'guo', '条': 'tiao', '河': 'he',
    '宽': 'kuan', '细': 'xi', '龙': 'long', '乌': 'wu', '拉': 'la', '意': 'yi',
    '大': 'da', '利': 'li', '通': 'tong', '心': 'xin',

    # === 其他 ===
    '蛋': 'dan', '鹌': 'an', '鹑': 'chun', '海': 'hai', '带': 'dai', '裙': 'qun',
    '昆': 'kun', '布': 'bu', '紫': 'zi', '苔': 'tai',
    '凉': 'liang', '龟': 'gui', '苓': 'ling', '膏': 'gao',

    # === 数字/英文 ===
    'M': 'm', 'm': 'm',
}


def chinese_to_pinyin(text: str) -> str:
    """
    将中文文本转换为拼音（无音调）
    示例："毛肚" -> "maodu"
    """
    result = []
    for char in text:
        if char in PINYIN_MAP:
            result.append(PINYIN_MAP[char])
        elif char.isalpha():
            result.append(char.lower())
        # 数字和其他字符忽略
    return ''.join(result)


def get_pinyin_initials(text: str) -> str:
    """
    获取拼音首字母
    示例："毛肚" -> "md"
    """
    result = []
    for char in text:
        if char in PINYIN_MAP:
            pinyin = PINYIN_MAP[char]
            if pinyin:
                result.append(pinyin[0])
        elif char.isalpha():
            result.append(char.lower())
    return ''.join(result)


# ==================== 2. 编辑距离（错别字纠正） ====================

def levenshtein_distance(s1: str, s2: str) -> int:
    """
    计算两个字符串的编辑距离（Levenshtein Distance）
    用于错别字纠正，如 "毛杜" -> "毛肚"
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def similarity_ratio(s1: str, s2: str) -> float:
    """
    计算两个字符串的相似度（0-1）
    使用 SequenceMatcher，综合考虑编辑距离和字符顺序
    """
    return SequenceMatcher(None, s1, s2).ratio()


# ==================== 3. 语义相似度（Embedding） ====================

# 预计算的食材语义向量（简化版）
# 实际项目中可使用 sentence-transformers 等库生成
# 这里使用基于分类和关键词的简化向量

CATEGORY_VECTORS = {
    '肉类': [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    '内脏类': [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    '海鲜类': [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    '丸滑类': [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
    '蔬菜类': [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0],
    '豆制品': [0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
    '菌菇类': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
    '主食类': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
    '其他': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
}


def get_ingredient_vector(ingredient: Ingredient) -> List[float]:
    """
    获取食材的语义向量
    基于分类 + 关键词特征
    """
    base_vector = CATEGORY_VECTORS.get(ingredient.category.value, [0.0] * 8)

    # 扩展向量维度，加入更多特征
    # [分类8维, 烹饪时间归一化, 是否高嘌呤, 是否有过敏原, 优先级归一化]

    # 烹饪时间归一化（假设最大600秒）
    time_normalized = ingredient.cooking_rule.base_seconds / 600.0

    # 高嘌呤特征
    high_purine = 1.0 if ingredient.nutrition.purine_level == "高" else 0.0

    # 过敏原特征
    has_allergen = 1.0 if ingredient.nutrition.allergens else 0.0

    # 优先级归一化（假设1-100）
    priority_normalized = ingredient.priority / 100.0

    extended = base_vector + [time_normalized,
                              high_purine, has_allergen, priority_normalized]
    return extended


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """
    计算两个向量的余弦相似度
    """
    if len(v1) != len(v2):
        return 0.0

    dot_product = sum(a * b for a, b in zip(v1, v2))
    magnitude1 = sum(a * a for a in v1) ** 0.5
    magnitude2 = sum(b * b for b in v2) ** 0.5

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)


def text_to_query_vector(text: str) -> List[float]:
    """
    将用户输入文本转换为查询向量
    基于关键词匹配和规则推断
    """
    text_lower = text.lower()

    # 分类关键词映射
    category_scores = [0.0] * 8

    # 肉类关键词
    if any(kw in text_lower for kw in ['肉', '牛', '羊', '猪', '鸡', '鸭']):
        category_scores[0] = 1.0  # 肉类

    # 内脏关键词
    if any(kw in text_lower for kw in ['肚', '肠', '肝', '腰', '脑', '胗', '喉', '血']):
        category_scores[1] = 1.0  # 内脏类

    # 海鲜关键词
    if any(kw in text_lower for kw in ['虾', '鱼', '蟹', '贝', '鱿', '墨', '蛏', '花甲']):
        category_scores[2] = 1.0  # 海鲜类

    # 丸滑关键词
    if any(kw in text_lower for kw in ['丸', '滑', '福袋']):
        category_scores[3] = 1.0  # 丸滑类

    # 蔬菜关键词
    if any(kw in text_lower for kw in ['菜', '菇', '笋', '瓜', '萝卜', '豆苗']):
        category_scores[4] = 1.0  # 蔬菜类

    # 豆制品关键词
    if any(kw in text_lower for kw in ['豆腐', '豆皮', '腐竹', '千张', '豆泡']):
        category_scores[5] = 1.0  # 豆制品

    # 菌菇关键词（也是蔬菜的子类）
    if any(kw in text_lower for kw in ['菇', '耳', '蘑']):
        category_scores[6] = 1.0  # 菌菇类
        category_scores[4] = 0.5  # 也部分属于蔬菜

    # 主食关键词
    if any(kw in text_lower for kw in ['面', '粉', '米', '年糕', '饺', '馄饨', '抄手']):
        category_scores[7] = 1.0  # 主食类

    # 扩展特征（未知，设为0.5默认值）
    extended = category_scores + [0.5, 0.5, 0.5, 0.5]
    return extended


# ==================== 4. 智能搜索主函数 ====================

@dataclass
class SearchResult:
    """搜索结果项"""
    ingredient: Ingredient
    match_score: float  # 综合匹配分数
    # 匹配类型：exact(精确), pinyin(拼音), typo(错别字纠正), semantic(语义相似)
    match_type: str


def smart_search_ingredient(
    keyword: str,
    enable_pinyin: bool = True,
    enable_typo: bool = True,
    enable_semantic: bool = True,
    top_k: int = 5,
    typo_threshold: float = 0.6,
    semantic_threshold: float = 0.5
) -> List[SearchResult]:
    """
    智能搜索食材

    综合使用多种匹配策略：
    1. 精确匹配（名称或别名包含）
    2. 拼音匹配（支持全拼和首字母）
    3. 错别字纠正（编辑距离）
    4. 语义相似度（向量余弦相似度）

    Args:
        keyword: 用户输入的关键词
        enable_pinyin: 是否启用拼音匹配
        enable_typo: 是否启用错别字纠正
        enable_semantic: 是否启用语义相似度
        top_k: 返回最多多少个结果
        typo_threshold: 错别字纠正相似度阈值
        semantic_threshold: 语义相似度阈值

    Returns:
        按匹配分数排序的 SearchResult 列表
    """
    if not keyword or not keyword.strip():
        return []

    keyword = keyword.strip()
    keyword_lower = keyword.lower()
    keyword_pinyin = chinese_to_pinyin(keyword) if enable_pinyin else ""
    keyword_initials = get_pinyin_initials(keyword) if enable_pinyin else ""

    results: Dict[str, SearchResult] = {}

    # 预计算查询向量（用于语义匹配）
    query_vector = text_to_query_vector(keyword) if enable_semantic else None

    for ingredient in INGREDIENTS_DATABASE.values():
        scores = []
        match_types = []

        # 1. 精确匹配（最高优先级）
        name_lower = ingredient.name.lower()
        aliases_lower = [a.lower() for a in ingredient.aliases]

        if keyword_lower == name_lower or keyword_lower in name_lower:
            scores.append(1.0)
            match_types.append("exact")
        elif any(keyword_lower == alias or keyword_lower in alias for alias in aliases_lower):
            scores.append(0.95)
            match_types.append("exact")

        # 2. 拼音匹配
        if enable_pinyin:
            name_pinyin = chinese_to_pinyin(ingredient.name)
            aliases_pinyin = [chinese_to_pinyin(a) for a in ingredient.aliases]

            # 全拼匹配
            if keyword_pinyin == name_pinyin or keyword_pinyin in name_pinyin:
                scores.append(0.9)
                match_types.append("pinyin")
            elif any(keyword_pinyin == alias_py or keyword_pinyin in alias_py for alias_py in aliases_pinyin):
                scores.append(0.85)
                match_types.append("pinyin")

            # 首字母匹配
            name_initials = get_pinyin_initials(ingredient.name)
            if keyword_initials == name_initials:
                scores.append(0.8)
                match_types.append("pinyin")

        # 3. 错别字纠正（编辑距离）
        if enable_typo and len(keyword) >= 2:
            # 只对比长度相近的
            if abs(len(keyword) - len(ingredient.name)) <= 2:
                typo_sim = similarity_ratio(keyword_lower, name_lower)
                if typo_sim >= typo_threshold:
                    scores.append(typo_sim * 0.7)  # 错别字匹配的权重稍低
                    match_types.append("typo")

            # 别名也检查
            for alias in aliases_lower:
                if abs(len(keyword) - len(alias)) <= 2:
                    alias_sim = similarity_ratio(keyword_lower, alias)
                    if alias_sim >= typo_threshold:
                        scores.append(alias_sim * 0.65)
                        match_types.append("typo")

        # 4. 语义相似度
        if enable_semantic and query_vector:
            ing_vector = get_ingredient_vector(ingredient)
            semantic_sim = cosine_similarity(query_vector, ing_vector)
            if semantic_sim >= semantic_threshold:
                scores.append(semantic_sim * 0.5)  # 语义匹配权重较低
                match_types.append("semantic")

        # 取最高分数
        if scores:
            best_score = max(scores)
            best_type = match_types[scores.index(best_score)]

            # 只保留分数高于阈值的
            if best_score >= 0.3:
                ing_id = ingredient.id
                if ing_id not in results or results[ing_id].match_score < best_score:
                    results[ing_id] = SearchResult(
                        ingredient=ingredient,
                        match_score=best_score,
                        match_type=best_type
                    )

    # 按分数排序，返回 top_k
    sorted_results = sorted(
        results.values(), key=lambda x: x.match_score, reverse=True)
    return sorted_results[:top_k]


def search_ingredient_with_fallback(keyword: str) -> List[Ingredient]:
    """
    兼容原接口的智能搜索（返回 Ingredient 列表）
    优先使用 smart_search，无结果时回退到原搜索
    """
    smart_results = smart_search_ingredient(keyword, top_k=5)

    if smart_results:
        return [r.ingredient for r in smart_results]

    # 回退到原始简单搜索
    from data.ingredients_db import search_ingredient as original_search
    return original_search(keyword)


# ==================== 5. 便捷函数 ====================

def explain_match(result: SearchResult) -> str:
    """
    解释匹配原因（用于调试或用户反馈）
    """
    ing = result.ingredient
    match_type_names = {
        "exact": "精确匹配",
        "pinyin": "拼音匹配",
        "typo": "智能纠错",
        "semantic": "语义相似"
    }
    type_name = match_type_names.get(result.match_type, result.match_type)
    return f"{ing.name}（{type_name}，置信度{result.match_score:.2f}）"


# 测试代码
if __name__ == "__main__":
    # 测试用例
    test_cases = [
        "毛肚",      # 精确匹配
        "maodu",     # 拼音匹配
        "md",        # 首字母匹配
        "毛杜",      # 错别字
        "牛",        # 语义：肉类
        "虾",        # 语义：海鲜
        "豆腐",      # 语义：豆制品
        "鸭长",      # 错别字
        "feiniu",    # 拼音
    ]

    print("=" * 60)
    print("智能食材搜索测试")
    print("=" * 60)

    for query in test_cases:
        print(f"\n🔍 查询: '{query}'")
        results = smart_search_ingredient(query, top_k=3)
        if results:
            for r in results:
                print(f"   ✓ {explain_match(r)}")
        else:
            print("   ✗ 无匹配结果")
