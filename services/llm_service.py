# -*- coding: utf-8 -*-
"""
涮涮AI - 大模型服务
使用大模型对涮菜顺序进行智能排序，替代固定规则。
支持任意 OpenAI 兼容接口（OpenAI / 阿里云 DashScope / 智谱 / 本地模型等）。
上下文（提示词、领域知识、少样本）由 context.context_loader 统一组装。
"""

import base64
import json
import re
import os
import socket
import ssl
import time
import sys
import urllib.request
import urllib.error
from typing import List, Optional, Dict, Any

# 确保项目根在 path，以便导入 context
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_SCRIPT_DIR)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# 默认模型与接口（可被环境变量覆盖）
DEFAULT_BASE_URL = os.environ.get("HOTPOT_LLM_BASE_URL", "https://api.openai.com/v1")
_DEFAULT_MODEL = os.environ.get("HOTPOT_LLM_MODEL", "").strip()
if not _DEFAULT_MODEL:
    _DEFAULT_MODEL = "gpt-3.5-turbo"
    if "siliconflow" in DEFAULT_BASE_URL.lower():
        _DEFAULT_MODEL = "Qwen/Qwen2.5-7B-Instruct"  # 硅基流动常用对话模型
DEFAULT_MODEL = _DEFAULT_MODEL

# 超时与重试（可环境变量覆盖）
def _get_llm_timeout():
    try:
        t = float(os.environ.get("HOTPOT_LLM_TIMEOUT", "120"))
        return max(30, min(300, t))
    except Exception:
        return 120.0

LLM_MAX_RETRIES = 3   # 排序接口最多重试次数（含首次）
LLM_RETRY_DELAY = 4   # 重试间隔（秒）


def _should_use_json_mode() -> bool:
    """
    是否为排序任务启用 JSON 模式（response_format=json_object）。
    通过环境变量 HOTPOT_LLM_JSON_MODE 控制：设为 "1"/"true"/"yes" 时启用。
    仅在所用模型 / 网关支持 OpenAI-style JSON Mode 时建议打开。
    """
    v = os.environ.get("HOTPOT_LLM_JSON_MODE", "").strip().lower()
    return v in ("1", "true", "yes", "on")


def _call_chat_completion(
    api_key: str,
    system_content: str,
    user_content: str,
    base_url: str = None,
    model: str = None,
    timeout: float = 120.0,
    max_tokens: int = 2048,
    force_json: bool = False,
) -> Optional[str]:
    """
    调用 OpenAI 兼容的 chat/completions 接口，返回 assistant 的 content。
    使用标准库 urllib，无额外依赖。
    """
    base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
    model = model or DEFAULT_MODEL
    url = f"{base_url}/chat/completions"

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_content or "你只输出合法 JSON。"},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.3,
        "max_tokens": max_tokens,
    }
    # 若启用 JSON 模式，则请求底层模型只返回 JSON 对象
    if force_json:
        body["response_format"] = {"type": "json_object"}
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="ignore")[:500]
            err = json.loads(body)
            msg = err.get("error", {}).get("message") if isinstance(err.get("error"), dict) else body
        except Exception:
            msg = body or str(e)
        raise ValueError(f"大模型接口 HTTP 错误 {e.code}：{msg}")
    except urllib.error.URLError as e:
        raise ValueError(f"大模型网络请求失败：{e.reason or str(e)}")
    except Exception as e:
        raise ValueError(f"大模型调用异常：{type(e).__name__} - {str(e)}")

    err_msg = result.get("error")
    if err_msg:
        if isinstance(err_msg, dict):
            err_msg = err_msg.get("message", str(err_msg))
        raise ValueError(f"大模型返回错误：{err_msg}")

    try:
        choices = result.get("choices") or []
        if not choices:
            raise ValueError("大模型返回为空（无 choices）")
        msg = choices[0].get("message") or {}
        raw_content = msg.get("content")
        # 兼容 content 为字符串或数组（如 [{"type":"text","text":"..."}]）
        if isinstance(raw_content, list):
            content = "".join(
                p.get("text", "") if isinstance(p, dict) else str(p)
                for p in raw_content
            )
        else:
            content = (raw_content or "")
        content = content.strip()
        if not content:
            finish = choices[0].get("finish_reason") or msg.get("finish_reason") or ""
            raise ValueError(
                "大模型返回内容为空"
                + (f"（finish_reason: {finish}，若为 length 可尝试减少食材数量或换更长上下文模型）" if finish else "，请检查模型与网络")
            )
        return content
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"解析大模型响应失败：{e}")


def _parse_order_from_response(
    response_text: str,
    valid_names: List[str],
) -> Optional[List[str]]:
    """
    从模型返回文本中解析出下锅顺序（食材名称列表）。
    兼容 JSON 被包在 markdown 代码块中的情况。
    """
    if not response_text or not valid_names:
        return None
    text = response_text.strip()
    # 尝试去掉 markdown 代码块
    for pattern in [r"```(?:json)?\s*([\s\S]*?)```", r"```\s*([\s\S]*?)```"]:
        m = re.search(pattern, text)
        if m:
            text = m.group(1).strip()
            break
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return None
    order = obj.get("下锅顺序")
    if not order or not isinstance(order, list):
        return None
    names = [str(x).strip() for x in order if x]
    valid_set = set(valid_names)
    if set(names) != valid_set:
        return None
    return names


def sort_cooking_order_by_llm(
    items: List[Any],
    broth_type: str,
    user_mode: str,
    api_key: str,
    base_url: str = None,
    model: str = None,
    user_preferences: Optional[Dict[str, Any]] = None,
) -> Optional[List[Any]]:
    """
    使用大模型对涮煮项进行排序，返回新的顺序列表。
    若调用失败或解析失败，返回 None（调用方应回退到规则排序）。
    user_preferences: 可选，用于注入用户偏好（锅底、模式、过敏原等）。
    """
    if not items or not api_key:
        return None
    try:
        from context.context_loader import build_sort_prompt
    except ImportError:
        build_sort_prompt = None
    if build_sort_prompt:
        system_content, user_content = build_sort_prompt(
            items,
            broth_type=broth_type,
            user_mode=user_mode,
            user_preferences=user_preferences,
        )
    else:
        system_content = "你只输出合法 JSON，不要 markdown 代码块或多余文字。"
        user_content = _fallback_build_sort_prompt(items, broth_type, user_mode)

    timeout_sec = _get_llm_timeout()
    last_error = None
    for attempt in range(LLM_MAX_RETRIES):
        try:
            content = _call_chat_completion(
                api_key=api_key,
                system_content=system_content,
                user_content=user_content,
                base_url=base_url,
                model=model,
                timeout=timeout_sec,
                force_json=_should_use_json_mode(),
            )
            if not content:
                raise ValueError("大模型返回内容为空")
            valid_names = [it.ingredient_name for it in items]
            ordered_names = _parse_order_from_response(content, valid_names)
            if not ordered_names:
                raise ValueError(
                    "大模型返回格式无法解析（需要 JSON 且包含「下锅顺序」数组，且食材名称与列表一致）。"
                )
            name_to_item = {it.ingredient_name: it for it in items}
            return [name_to_item[n] for n in ordered_names]
        except (TimeoutError, ValueError, urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            last_error = e
            is_timeout = (
                isinstance(e, TimeoutError)
                or (isinstance(e, urllib.error.URLError) and isinstance(getattr(e, "reason", None), socket.timeout))
            )
            if attempt < LLM_MAX_RETRIES - 1:
                time.sleep(LLM_RETRY_DELAY)
            else:
                if is_timeout:
                    raise ValueError(
                        f"大模型请求超时（已重试 {LLM_MAX_RETRIES} 次）。"
                        "可在 .env 中设置 HOTPOT_LLM_TIMEOUT=180 延长超时时间。"
                    ) from e
                raise
    if last_error:
        raise last_error
    raise ValueError("大模型排序失败")


# ============== 视觉模型：图片识别食材 ==============

VLM_INGREDIENTS_MODEL = os.environ.get("HOTPOT_VLM_MODEL", "Qwen/Qwen3-VL-32B-Instruct")


def _call_chat_completion_vision(
    api_key: str,
    image_base64: str,
    user_text: str,
    base_url: str = None,
    model: str = None,
    mime_type: str = "image/jpeg",
    timeout: float = 120.0,
) -> Optional[str]:
    """
    调用 OpenAI 兼容的多模态 chat/completions，上传图片 + 文本，返回 assistant 的 content。
    用于 VLM 识别图片中的火锅食材。
    """
    base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
    model = model or VLM_INGREDIENTS_MODEL
    url = f"{base_url}/chat/completions"
    data_url = f"data:{mime_type};base64,{image_base64}"
    body = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_url, "detail": "low"}},
                    {"type": "text", "text": user_text},
                ],
            }
        ],
        "temperature": 0.2,
        "max_tokens": 1024,
    }
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_err = ""
        try:
            body_err = e.read().decode("utf-8", errors="ignore")[:500]
            err = json.loads(body_err)
            msg = err.get("error", {}).get("message") if isinstance(err.get("error"), dict) else body_err
        except Exception:
            msg = body_err or str(e)
        raise ValueError(f"VLM 接口 HTTP 错误 {e.code}：{msg}")
    except urllib.error.URLError as e:
        raise ValueError(f"VLM 网络请求失败：{e.reason or str(e)}")
    except Exception as e:
        raise ValueError(f"VLM 调用异常：{type(e).__name__} - {str(e)}")

    err_msg = result.get("error")
    if err_msg:
        if isinstance(err_msg, dict):
            err_msg = err_msg.get("message", str(err_msg))
        raise ValueError(f"VLM 返回错误：{err_msg}")
    try:
        choices = result.get("choices") or []
        if not choices:
            raise ValueError("VLM 返回为空（无 choices）")
        content = (choices[0].get("message") or {}).get("content") or ""
        return content.strip()
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"解析 VLM 响应失败：{e}")


def recognize_ingredients_from_image(
    image_data: bytes,
    api_key: str = None,
    base_url: str = None,
    model: str = None,
    mime_type: str = "image/jpeg",
) -> List[str]:
    """
    使用 VLM 从图片中识别火锅食材，返回食材名称列表。
    api_key / base_url 未传时从环境变量读取（与文本 LLM 相同）。
    """
    api_key = (api_key or os.environ.get("HOTPOT_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise ValueError("未配置 API Key，请设置 HOTPOT_LLM_API_KEY 或 OPENAI_API_KEY")
    base_url = (base_url or os.environ.get("HOTPOT_LLM_BASE_URL") or "").strip() or None
    model = (model or os.environ.get("HOTPOT_VLM_MODEL") or VLM_INGREDIENTS_MODEL).strip() or VLM_INGREDIENTS_MODEL
    image_b64 = base64.b64encode(image_data).decode("ascii")
    prompt = """这是一张火锅相关图片（可能是菜单、菜品或餐桌）。请识别图中出现的、适合涮火锅的食材名称。
只输出一个 JSON 对象，不要其他说明或 markdown 代码块，格式如下：
{"ingredients": ["食材1", "食材2", "食材3", ...]}
例如：{"ingredients": ["肥牛", "毛肚", "鸭肠", "土豆"]}
若图中没有可识别的火锅食材，输出：{"ingredients": []}"""
    content = _call_chat_completion_vision(
        api_key=api_key,
        image_base64=image_b64,
        user_text=prompt,
        base_url=base_url,
        model=model,
        mime_type=mime_type,
    )
    if not content:
        return []
    text = content.strip()
    for pattern in [r"```(?:json)?\s*([\s\S]*?)```", r"```\s*([\s\S]*?)```"]:
        m = re.search(pattern, text)
        if m:
            text = m.group(1).strip()
            break
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return []
    ing = obj.get("ingredients")
    if not isinstance(ing, list):
        return []
    return [str(x).strip() for x in ing if x and str(x).strip()]


def _fallback_build_sort_prompt(
    items: List[Any],
    broth_type: str,
    user_mode: str,
) -> str:
    """context 不可用时的兜底：手写简短 user prompt。"""
    lines = [
        "当前锅底类型：" + broth_type,
        "用户模式：" + user_mode,
        "",
        "食材列表（名称、分类、建议涮煮时间秒、技巧）：",
    ]
    for i, it in enumerate(items, 1):
        lines.append(
            f"  {i}. {it.ingredient_name} | 分类:{it.category} | 时间:{it.cooking_seconds}秒 | {getattr(it, 'technique', '') or '无'}"
        )
    lines.extend([
        "",
        "请只输出一个 JSON：{\"下锅顺序\": [\"食材1\", \"食材2\", ...]}，必须包含且仅包含上述所有食材名称。",
    ])
    return "\n".join(lines)
