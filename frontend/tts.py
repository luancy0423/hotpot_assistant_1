# -*- coding: utf-8 -*-
"""
<<<<<<< Updated upstream
前端 TTS 层（语音合成）
负责将文字转为语音 WAV base64，及生成可在 Gradio HTML 组件中 autoplay 的 <audio> 标签。
支持阿里云千问 TTS（需 DASHSCOPE_API_KEY），无 Key 时静默降级为哔声兜底。
"""

import base64
import io
import os
import struct

# ── 环境变量 ────────────────────────────────────────────────────
_TTS_ALIYUN_WS_URL = os.environ.get("HOTPOT_TTS_WS_URL", "wss://dashscope.aliyuncs.com/api-ws/v1/realtime")
_TTS_ALIYUN_MODEL  = os.environ.get("HOTPOT_TTS_MODEL",  "qwen3-tts-flash-realtime")


# ── 哔声兜底（模块加载时生成一次）──────────────────────────────

def make_beep_wav_base64(duration_sec: float = 0.15, sample_rate: int = 44100, freq: int = 880) -> str:
    """生成短促提示音 WAV 的 base64，用于 HTML audio autoplay。"""
=======
涮涮AI - TTS 语音合成
提示音 WAV、阿里云千问 TTS 实时合成、文案转 <audio> HTML。
"""

import os
import base64
import struct
import io


def make_beep_wav_base64(duration_sec: float = 0.15, sample_rate: int = 44100, freq: int = 880) -> str:
    """生成短促提示音 WAV 的 base64，用于 HTML audio。"""
>>>>>>> Stashed changes
    import math
    n = int(sample_rate * duration_sec)
    with io.BytesIO() as raw:
        for i in range(n):
            t = i / sample_rate
<<<<<<< Updated upstream
            v = int(32767 * 0.3 * (1 - i / n) * math.sin(2 * math.pi * freq * t))
=======
            v = int(32767 * 0.3 * (1 - i / n) * math.sin(2 * 3.14159265 * freq * t))
>>>>>>> Stashed changes
            raw.write(struct.pack("<h", max(-32768, min(32767, v))))
        pcm = raw.getvalue()
    with io.BytesIO() as wav:
        wav.write(b"RIFF")
        wav.write(struct.pack("<I", 36 + len(pcm)))
        wav.write(b"WAVEfmt ")
        wav.write(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
        wav.write(b"data")
        wav.write(struct.pack("<I", len(pcm)))
        wav.write(pcm)
        wav.seek(0)
        return base64.b64encode(wav.read()).decode("ascii")


<<<<<<< Updated upstream
BEEP_B64: str = make_beep_wav_base64()


# ── PCM → WAV ────────────────────────────────────────────────────

def pcm_to_wav_base64(pcm_bytes: bytes, sample_rate: int = 24000,
                      sample_width: int = 2, channels: int = 1) -> str:
    """将 PCM 裸流转为 WAV 并 base64 编码（用于阿里云 TTS 返回的 PCM）。"""
    n_frames  = len(pcm_bytes) // (sample_width * channels)
=======
BEEP_B64 = make_beep_wav_base64()

TTS_WS_URL = os.environ.get("HOTPOT_TTS_WS_URL", "wss://dashscope.aliyuncs.com/api-ws/v1/realtime")
TTS_MODEL = os.environ.get("HOTPOT_TTS_MODEL", "qwen3-tts-flash-realtime")


def pcm_to_wav_base64(pcm_bytes: bytes, sample_rate: int = 24000, sample_width: int = 2, channels: int = 1) -> str:
    """将 PCM 裸流转为 WAV 并 base64 编码。"""
    n_frames = len(pcm_bytes) // (sample_width * channels)
>>>>>>> Stashed changes
    data_size = n_frames * sample_width * channels
    with io.BytesIO() as wav:
        wav.write(b"RIFF")
        wav.write(struct.pack("<I", 36 + data_size))
        wav.write(b"WAVEfmt ")
        wav.write(struct.pack("<IHHIIHH", 16, 1, channels, sample_rate,
<<<<<<< Updated upstream
                              sample_rate * sample_width * channels,
                              sample_width * channels, sample_width * 8))
=======
                              sample_rate * sample_width * channels, sample_width * channels, sample_width * 8))
>>>>>>> Stashed changes
        wav.write(b"data")
        wav.write(struct.pack("<I", data_size))
        wav.write(pcm_bytes[:data_size])
        wav.seek(0)
        return base64.b64encode(wav.read()).decode("ascii")


<<<<<<< Updated upstream
# ── 阿里云千问 TTS ───────────────────────────────────────────────

def tts_aliyun_phrase_to_wav_base64(phrase: str):
    """
    调用阿里云千问 TTS 实时合成，返回 WAV base64 字符串；失败返回 None。
    需配置 DASHSCOPE_API_KEY 环境变量。
    """
    if not phrase or not phrase.strip():
        return None
    api_key = (os.environ.get("DASHSCOPE_API_KEY") or "").strip()
    if not api_key:
        return None
=======
def tts_aliyun_phrase_to_wav_base64(phrase: str) -> str:
    """
    使用阿里云千问 TTS 实时合成，将中文文案转为语音。
    需配置 DASHSCOPE_API_KEY。返回 WAV base64，失败返回 None。
    """
    if not phrase or not phrase.strip():
        return ""
    api_key = (os.environ.get("DASHSCOPE_API_KEY") or "").strip()
    if not api_key:
        return ""
>>>>>>> Stashed changes
    try:
        import threading
        import dashscope
        from dashscope.audio.qwen_tts_realtime import QwenTtsRealtime, QwenTtsRealtimeCallback, AudioFormat

<<<<<<< Updated upstream
        class _Collector(QwenTtsRealtimeCallback):
            def __init__(self):
                self.event = threading.Event()
                self.chunks = []
=======
        class _CollectCallback(QwenTtsRealtimeCallback):
            def __init__(self):
                self.complete_event = threading.Event()
                self.pcm_chunks = []
>>>>>>> Stashed changes

            def on_open(self):
                pass

<<<<<<< Updated upstream
            def on_close(self, code, msg):
                self.event.set()

            def on_event(self, resp):
                try:
                    if resp.get("type") == "response.audio.delta" and resp.get("delta"):
                        self.chunks.append(base64.b64decode(resp["delta"]))
                    if resp.get("type") == "session.finished":
                        self.event.set()
                except Exception:
                    pass

            def wait(self, timeout=15):
                self.event.wait(timeout=timeout)

        dashscope.api_key = api_key
        cb = _Collector()
        client = QwenTtsRealtime(model=_TTS_ALIYUN_MODEL, callback=cb, url=_TTS_ALIYUN_WS_URL)
=======
            def on_close(self, close_status_code, close_msg):
                self.complete_event.set()

            def on_event(self, response):
                try:
                    if response.get("type") == "response.audio.delta" and response.get("delta"):
                        self.pcm_chunks.append(base64.b64decode(response["delta"]))
                    if response.get("type") == "session.finished":
                        self.complete_event.set()
                except Exception:
                    pass

            def wait_for_finished(self, timeout=15):
                self.complete_event.wait(timeout=timeout)

        dashscope.api_key = api_key
        callback = _CollectCallback()
        client = QwenTtsRealtime(model=TTS_MODEL, callback=callback, url=TTS_WS_URL)
>>>>>>> Stashed changes
        client.connect()
        client.update_session(voice="Cherry", response_format=AudioFormat.PCM_24000HZ_MONO_16BIT, mode="server_commit")
        client.append_text(phrase.strip())
        client.finish()
<<<<<<< Updated upstream
        cb.wait()
        if not cb.chunks:
            return None
        return pcm_to_wav_base64(b"".join(cb.chunks), sample_rate=24000, sample_width=2, channels=1)
    except Exception:
        return None


def tts_phrase_to_audio_html(phrase: str) -> str:
    """将文案转为 TTS 语音，返回可 autoplay 的 <audio> HTML；失败返回空字符串。"""
=======
        callback.wait_for_finished()
        if not callback.pcm_chunks:
            return ""
        pcm_data = b"".join(callback.pcm_chunks)
        return pcm_to_wav_base64(pcm_data, sample_rate=24000, sample_width=2, channels=1)
    except Exception:
        return ""


def tts_phrase_to_audio_html(phrase: str) -> str:
    """将一句中文文案转为 TTS 语音，返回可 autoplay 的 <audio> HTML。"""
>>>>>>> Stashed changes
    if not phrase or not phrase.strip():
        return ""
    wav_b64 = tts_aliyun_phrase_to_wav_base64(phrase.strip())
    if wav_b64:
        return f'<audio autoplay><source src="data:audio/wav;base64,{wav_b64}" type="audio/wav"></audio>'
    return ""
