# -*- coding: utf-8 -*-
"""
涮涮AI - 模拟识别服务
包含OCR图像识别和语音识别的模拟实现
后续可替换为真实API调用（百度、阿里、讯飞等）
"""

import re
import random
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

@dataclass
class RecognitionResult:
    """识别结果"""
    success: bool
    items: List[str]           # 识别出的食材名称列表
    confidence: float          # 置信度 0-1
    raw_text: str              # 原始识别文本
    error_message: str = ""

@dataclass
class OCRResult:
    """OCR识别结果"""
    success: bool
    text_blocks: List[Dict]    # 文字块列表 [{text, position, confidence}]
    detected_items: List[str]  # 识别出的菜品
    error_message: str = ""

@dataclass
class VoiceResult:
    """语音识别结果"""
    success: bool
    transcript: str            # 转写文本
    items: List[str]           # 提取出的食材
    confidence: float
    error_message: str = ""

# 食材关键词映射表（用于从文本中提取食材）
INGREDIENT_KEYWORDS = {
    # 肉类
    "肥牛": ["肥牛", "牛肉卷", "雪花牛肉", "M5", "和牛"],
    "肥羊": ["羊肉", "肥羊", "羊肉卷", "羔羊"],
    "牛肉片": ["牛肉片", "鲜切牛肉", "吊龙", "匙柄"],
    "麻辣牛肉": ["麻辣牛肉", "麻辣牛肉片", "腌牛肉"],
    "牛舌": ["牛舌", "牛舌片", "厚切牛舌"],
    # 内脏
    "毛肚": ["毛肚", "牛百叶", "黑毛肚", "金毛肚"],
    "鸭肠": ["鸭肠", "脆鸭肠"],
    "黄喉": ["黄喉", "猪黄喉", "牛黄喉"],
    "脑花": ["脑花", "猪脑", "猪脑花"],
    "鸭血": ["鸭血", "血旺", "鸭血旺", "鲜鸭血"],
    # 海鲜
    "虾滑": ["虾滑", "手打虾滑"],
    "鲜虾": ["基围虾", "大虾", "活虾", "鲜虾"],
    # 丸类
    "牛肉丸": ["牛肉丸", "牛丸", "潮汕牛丸"],
    "鱼丸": ["鱼丸", "鱼蛋", "墨鱼丸"],
    "午餐肉": ["午餐肉", "火腿午餐肉", "罐头午餐肉"],
    # 蔬菜
    "土豆": ["土豆", "土豆片", "马铃薯", "洋芋"],
    "藕片": ["藕片", "莲藕", "藕"],
    "菠菜": ["菠菜"],
    "生菜": ["生菜", "莴苣"],
    "冬瓜": ["冬瓜"],
    "青笋": ["青笋", "莴笋", "莴笋片", "莴苣"],
    "香菜": ["香菜", "芫荽", "香荽"],
    "笋尖": ["笋尖", "竹笋尖", "嫩笋", "笋片"],
    # 豆制品
    "老豆腐": ["老豆腐", "北豆腐"],
    "嫩豆腐": ["嫩豆腐", "日本豆腐", "内酯豆腐"],
    "腐竹": ["腐竹"],
    # 菌菇
    "金针菇": ["金针菇"],
    "香菇": ["香菇", "冬菇", "花菇"],
    "平菇": ["平菇", "秀珍菇"],
    # 主食
    "方便面": ["方便面", "火锅面", "泡面"],
    "年糕": ["年糕"],
    "苕粉": ["苕粉", "红薯粉", "宽粉", "火锅粉"],
    # 其他
    "海带": ["海带", "海带片", "海带结", "昆布"],
    "海白菜": ["海白菜", "海带芽", "裙带菜"],
    "鹌鹑蛋": ["鹌鹑蛋"],
}

# 锅底关键词
BROTH_KEYWORDS = {
    "SPICY": ["红汤", "麻辣", "牛油", "红油", "辣锅"],
    "CLEAR": ["清汤", "白汤", "骨汤", "清水"],
    "TOMATO": ["番茄", "西红柿"],
    "MUSHROOM": ["菌汤", "菌菇"],
}


class MockOCRService:
    """模拟OCR服务"""
    
    # 预设的模拟菜单图片识别结果
    MOCK_MENU_TEXTS = [
        """
        【精品肉类】
        精品肥牛 ¥58
        M5和牛 ¥128
        精品肥羊 ¥52
        鲜切牛肉 ¥68
        
        【特色内脏】
        极品鲜毛肚 ¥68
        脆鸭肠 ¥38
        鲜黄喉 ¥42
        猪脑花 ¥28
        
        【海鲜丸滑】
        手打虾滑 ¥48
        基围虾 ¥88
        潮汕牛肉丸 ¥38
        墨鱼丸 ¥32
        """,
        """
        === 今日已点 ===
        肥牛卷 x1
        毛肚 x1
        鸭肠 x2
        虾滑 x1
        土豆片 x1
        金针菇 x1
        菠菜 x1
        ---
        锅底: 麻辣红汤
        """,
        """
        小票
        海底捞火锅
        ----------------
        麻辣锅底 88元
        精品肥牛 58元
        鲜毛肚 68元
        脆鸭肠 38元
        虾滑 48元
        土豆片 16元
        生菜 12元
        金针菇 16元
        ----------------
        合计: 344元
        """,
    ]
    
    @classmethod
    def recognize_image(cls, image_data: bytes = None, image_path: str = None) -> OCRResult:
        """
        模拟OCR识别菜单/小票图片
        
        Args:
            image_data: 图片二进制数据
            image_path: 图片路径（用于模拟，实际会忽略）
        
        Returns:
            OCRResult: 识别结果
        """
        # 随机选择一个模拟结果
        mock_text = random.choice(cls.MOCK_MENU_TEXTS)
        
        # 从文本中提取食材
        detected_items = cls._extract_ingredients(mock_text)
        
        # 构造文字块（模拟真实OCR返回格式）
        text_blocks = []
        for i, line in enumerate(mock_text.strip().split('\n')):
            if line.strip():
                text_blocks.append({
                    "text": line.strip(),
                    "position": {"x": 10, "y": 20 + i * 30, "width": 200, "height": 25},
                    "confidence": random.uniform(0.85, 0.99)
                })
        
        return OCRResult(
            success=True,
            text_blocks=text_blocks,
            detected_items=detected_items,
            error_message=""
        )
    
    @classmethod
    def recognize_menu_photo(cls, image_data: bytes = None) -> RecognitionResult:
        """
        专门识别火锅菜单照片，直接返回食材列表
        """
        ocr_result = cls.recognize_image(image_data)
        
        if not ocr_result.success:
            return RecognitionResult(
                success=False,
                items=[],
                confidence=0,
                raw_text="",
                error_message=ocr_result.error_message
            )
        
        raw_text = "\n".join([block["text"] for block in ocr_result.text_blocks])
        
        return RecognitionResult(
            success=True,
            items=ocr_result.detected_items,
            confidence=0.92,
            raw_text=raw_text
        )
    
    @staticmethod
    def _extract_ingredients(text: str) -> List[str]:
        """从文本中提取食材名称"""
        detected = []
        text_lower = text.lower()
        
        for ingredient_name, keywords in INGREDIENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    if ingredient_name not in detected:
                        detected.append(ingredient_name)
                    break
        
        return detected
    
    @staticmethod
    def detect_broth_type(text: str) -> Optional[str]:
        """从文本中检测锅底类型"""
        for broth_type, keywords in BROTH_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    return broth_type
        return None


class MockVoiceService:
    """模拟语音识别服务"""
    
    # 预设的语音识别结果模拟
    MOCK_TRANSCRIPTS = [
        "我要肥牛、毛肚、鸭肠，再来一份虾滑，要麻辣锅底",
        "来一份牛肉丸、土豆片、金针菇，还有菠菜和生菜",
        "点个脑花、黄喉、腐竹，锅底要番茄的",
        "我们要肥牛、肥羊、毛肚、鸭肠、虾滑、土豆、藕片、金针菇，锅底鸳鸯的",
        "来份毛肚脆一点的，再要肥牛、鸭肠",
    ]
    
    @classmethod
    def recognize_audio(cls, audio_data: bytes = None, audio_path: str = None) -> VoiceResult:
        """
        模拟语音识别
        
        Args:
            audio_data: 音频二进制数据
            audio_path: 音频文件路径
        
        Returns:
            VoiceResult: 识别结果
        """
        # 随机选择一个模拟转写结果
        transcript = random.choice(cls.MOCK_TRANSCRIPTS)
        
        # 提取食材
        items = cls._extract_ingredients_from_speech(transcript)
        
        return VoiceResult(
            success=True,
            transcript=transcript,
            items=items,
            confidence=0.88
        )
    
    @classmethod
    def recognize_realtime(cls, audio_stream=None) -> VoiceResult:
        """
        模拟实时语音识别（流式）
        实际应用中会是一个生成器，逐字返回
        """
        return cls.recognize_audio()
    
    @staticmethod
    def _extract_ingredients_from_speech(text: str) -> List[str]:
        """从语音转写文本中提取食材"""
        detected = []
        
        for ingredient_name, keywords in INGREDIENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    if ingredient_name not in detected:
                        detected.append(ingredient_name)
                    break
        
        return detected


class MockRecognitionService:
    """统一识别服务入口"""
    
    def __init__(self):
        self.ocr_service = MockOCRService()
        self.voice_service = MockVoiceService()
    
    def recognize_from_image(self, image_data: bytes = None, image_path: str = None) -> RecognitionResult:
        """从图片识别食材"""
        return self.ocr_service.recognize_menu_photo(image_data)
    
    def recognize_from_voice(self, audio_data: bytes = None) -> RecognitionResult:
        """从语音识别食材"""
        voice_result = self.voice_service.recognize_audio(audio_data)
        
        return RecognitionResult(
            success=voice_result.success,
            items=voice_result.items,
            confidence=voice_result.confidence,
            raw_text=voice_result.transcript,
            error_message=voice_result.error_message
        )
    
    def recognize_from_text(self, text: str) -> RecognitionResult:
        """从纯文本中提取食材（用户手动输入）"""
        items = []
        
        for ingredient_name, keywords in INGREDIENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    if ingredient_name not in items:
                        items.append(ingredient_name)
                    break
        
        # 检测锅底
        broth = MockOCRService.detect_broth_type(text)
        
        return RecognitionResult(
            success=True,
            items=items,
            confidence=1.0,  # 文本输入置信度最高
            raw_text=text
        )


# ============== 真实API接口预留 ==============

class RealOCRService:
    """
    真实OCR服务接口（预留）
    可接入：百度OCR、阿里云OCR、腾讯OCR、微信OCR
    """
    
    def __init__(self, provider: str = "baidu", api_key: str = "", secret_key: str = ""):
        self.provider = provider
        self.api_key = api_key
        self.secret_key = secret_key
    
    def recognize(self, image_data: bytes) -> OCRResult:
        """
        调用真实OCR API
        
        TODO: 实现真实API调用
        - 百度OCR: https://ai.baidu.com/tech/ocr
        - 阿里云: https://ai.aliyun.com/ocr
        - 腾讯云: https://cloud.tencent.com/product/ocr
        """
        raise NotImplementedError("请配置真实OCR API密钥")


class RealVoiceService:
    """
    真实语音识别服务接口（预留）
    可接入：百度语音、讯飞、阿里云、微信语音
    """
    
    def __init__(self, provider: str = "xunfei", api_key: str = ""):
        self.provider = provider
        self.api_key = api_key
    
    def recognize(self, audio_data: bytes) -> VoiceResult:
        """
        调用真实语音识别API
        
        TODO: 实现真实API调用
        - 讯飞: https://www.xfyun.cn/
        - 百度语音: https://ai.baidu.com/tech/speech
        - 阿里云: https://ai.aliyun.com/nls
        """
        raise NotImplementedError("请配置真实语音识别API密钥")


# 工厂函数：根据配置返回相应服务
def create_recognition_service(use_mock: bool = True, ocr_config: dict = None, voice_config: dict = None):
    """
    创建识别服务实例
    
    Args:
        use_mock: 是否使用模拟服务（开发测试用）
        ocr_config: OCR配置 {"provider": "baidu", "api_key": "xxx"}
        voice_config: 语音配置
    
    Returns:
        识别服务实例
    """
    if use_mock:
        return MockRecognitionService()
    else:
        # TODO: 返回真实服务实例
        raise NotImplementedError("真实API服务尚未实现")
