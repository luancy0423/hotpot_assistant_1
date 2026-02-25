# -*- coding: utf-8 -*-
"""
涮涮AI - 上下文加载器
统一加载提示词模板、领域知识、少样本示例，支持版本切换。
"""

import os
import json
from typing import List, Any, Optional, Dict

# 上下文目录：本文件所在目录
_CONTEXT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROMPTS_DIR = os.path.join(_CONTEXT_DIR, "prompts")
_KNOWLEDGE_DIR = os.path.join(_CONTEXT_DIR, "knowledge")
_FEW_SHOT_DIR = os.path.join(_CONTEXT_DIR, "few_shot")


def _versioned_dir(base: str) -> str:
    """若设置 HOTPOT_PROMPT_VERSION，则返回 base/version，否则 base。"""
    version = os.environ.get("HOTPOT_PROMPT_VERSION", "").strip()
    if version:
        return os.path.join(base, version)
    return base


def load_prompt(name: str, part: str) -> str:
    """
    加载提示词模板。
    name: 如 "sort"
    part: 如 "system" 或 "user_template"
    返回文件内容，失败返回空字符串。
    """
    base = _versioned_dir(_PROMPTS_DIR)
    path = os.path.join(base, f"{name}_{part}.txt")
    if not os.path.isfile(path):
        path = os.path.join(_PROMPTS_DIR, f"{name}_{part}.txt")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def get_domain_knowledge(sections: Optional[List[str]] = None) -> str:
    """
    拼接领域知识。sections 可选 ["general_rules", "broth_mode_effect", "techniques", "safety_and_misc"]，
    默认全部按此顺序。
    """
    if sections is None:
        sections = ["general_rules", "broth_mode_effect", "techniques", "safety_and_misc"]
    base = _versioned_dir(_KNOWLEDGE_DIR)
    parts = []
    for name in sections:
        path = os.path.join(base, f"{name}.txt")
        if not os.path.isfile(path):
            path = os.path.join(_KNOWLEDGE_DIR, f"{name}.txt")
        try:
            with open(path, "r", encoding="utf-8") as f:
                parts.append(f.read().strip())
        except Exception:
            continue
    return "\n\n".join(parts) if parts else ""


def get_few_shot_sort_examples(
    broth_type: Optional[str] = None,
    user_mode: Optional[str] = None,
    max_examples: int = 2,
) -> str:
    """
    从 few_shot/sort_examples.json 读取示例并格式化为可注入的文本。
    会优先选择与当前锅底 / 用户模式更匹配的示例。
    """
    base = _versioned_dir(_FEW_SHOT_DIR)
    path = os.path.join(base, "sort_examples.json")
    if not os.path.isfile(path):
        path = os.path.join(_FEW_SHOT_DIR, "sort_examples.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            examples = json.load(f)
    except Exception:
        return ""
    if not isinstance(examples, list):
        return ""

    # 根据锅底 / 模式打分，优先选最匹配的 few-shot
    def _score(ex: Dict[str, Any]) -> int:
        score = 0
        if broth_type and ex.get("broth_type") == broth_type:
            score += 2
        if user_mode and ex.get("user_mode") == user_mode:
            score += 1
        return score

    indexed = []
    for idx, ex in enumerate(examples):
        if not isinstance(ex, dict) or "下锅顺序" not in ex:
            continue
        indexed.append((idx, _score(ex), ex))
    if not indexed:
        return ""
    # 先按分数降序，再按原始顺序升序，保证稳定
    indexed.sort(key=lambda t: (-t[1], t[0]))

    lines = []
    for i, (_, _, ex) in enumerate(indexed[:max_examples], 1):
        lines.append(f"示例{i}：锅底={ex.get('broth_type','')}，模式={ex.get('user_mode','')}")
        lines.append(f"  食材：{ex.get('ingredients','')}")
        lines.append(f"  输出：{json.dumps(ex['下锅顺序'], ensure_ascii=False)}")
        lines.append("")
    return "\n".join(lines).strip() if lines else ""


def format_user_preferences(prefs: Optional[Dict[str, Any]]) -> str:
    """将用户偏好格式化为「用户偏好与注意事项」段落。"""
    if not prefs:
        return "无特殊偏好，按通用原则即可。"
    parts = []
    if prefs.get("broth_type"):
        parts.append(f"锅底：{prefs['broth_type']}")
    if prefs.get("user_mode"):
        parts.append(f"用户模式：{prefs['user_mode']}")
    if prefs.get("allergens_to_avoid"):
        allergens = prefs["allergens_to_avoid"]
        if isinstance(allergens, list):
            parts.append(f"需避免的过敏原：{', '.join(allergens)}（排序时无需剔除，但可作参考）")
        else:
            parts.append(f"需避免的过敏原：{allergens}")
    if not parts:
        return "无特殊偏好，按通用原则即可。"
    return "；".join(parts) + "。"


def build_sort_prompt(
    items: List[Any],
    broth_type: str,
    user_mode: str,
    user_preferences: Optional[Dict[str, Any]] = None,
    include_knowledge: bool = True,
    include_few_shot: bool = True,
    max_few_shot: int = 2,
) -> tuple:
    """
    组装涮菜排序的 system 与 user 内容。
    返回 (system_str, user_str)。
    """
    system = load_prompt("sort", "system")
    if not system:
        system = "你只输出合法 JSON，不要 markdown 代码块或多余文字。"

    user_template = load_prompt("sort", "user_template")
    if not user_template:
        # 回退：简单内联
        user_template = (
            "当前锅底类型：{{BROTH_TYPE}}\n用户模式：{{USER_MODE}}\n\n"
            "食材列表：\n{{INGREDIENT_LIST}}\n\n"
            "请只输出：{\"下锅顺序\": [\"食材1\", \"食材2\", ...]}"
        )

    domain = get_domain_knowledge() if include_knowledge else ""
    # 领域知识并入 system，user 中仅保留简短提示，避免重复占用上下文
    if domain:
        system = system + "\n\n【领域知识参考】\n" + domain
        domain_for_user = "（领域知识已在系统提示中给出）"
    else:
        domain_for_user = ""

    few_shot = (
        get_few_shot_sort_examples(
            broth_type=broth_type,
            user_mode=user_mode,
            max_examples=max_few_shot,
        )
        if include_few_shot
        else "（无）"
    )
    prefs_text = format_user_preferences(user_preferences)

    # 食材列表
    ing_lines = []
    for i, it in enumerate(items, 1):
        name = getattr(it, "ingredient_name", str(it))
        cat = getattr(it, "category", "")
        sec = getattr(it, "cooking_seconds", 0)
        tech = getattr(it, "technique", "") or "无"
        ing_lines.append(f"  {i}. {name} | 分类:{cat} | 时间:{sec}秒 | {tech}")
    ingredient_list = "\n".join(ing_lines) if ing_lines else ""

    user_str = user_template.replace("{{DOMAIN_KNOWLEDGE}}", domain_for_user)
    user_str = user_str.replace("{{USER_PREFERENCES}}", prefs_text)
    user_str = user_str.replace("{{FEW_SHOT_EXAMPLES}}", few_shot)
    user_str = user_str.replace("{{BROTH_TYPE}}", broth_type)
    user_str = user_str.replace("{{USER_MODE}}", user_mode)
    user_str = user_str.replace("{{INGREDIENT_LIST}}", ingredient_list)

    return system, user_str
