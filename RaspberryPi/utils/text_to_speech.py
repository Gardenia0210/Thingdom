#!/usr/bin/env python3

import asyncio
import websockets
import json
import ssl
import os
import sys
import logging
from datetime import datetime
from typing import Optional, Callable

from config import (
    MINIMAX_API_KEY,
    TTS_MODEL,
    TTS_VOICE_ID,
    TTS_SPEED,
    TTS_VOLUME,
    TTS_PITCH,
    TTS_SAMPLE_RATE,
    TTS_BITRATE,
    TTS_FORMAT,
    TTS_CHANNEL,
    OUTPUT_DIR,
    DEBUG_LOG
)

logging.basicConfig(
    level=logging.DEBUG if DEBUG_LOG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TextToSpeech:

    def __init__(self,
                 api_key: Optional[str] = None,
                 model: Optional[str] = None,
                 voice_id: Optional[str] = None,
                 speed: Optional[float] = None,
                 volume: Optional[float] = None,
                 pitch: Optional[int] = None,
                 sample_rate: Optional[int] = None,
                 bitrate: Optional[int] = None,
                 audio_format: Optional[str] = None,
                 channel: Optional[int] = None):

        self.api_key = api_key or MINIMAX_API_KEY
        self.model = model or TTS_MODEL
        self.voice_id = voice_id or TTS_VOICE_ID
        self.speed = speed if speed is not None else TTS_SPEED
        self.volume = volume if volume is not None else TTS_VOLUME
        self.pitch = pitch if pitch is not None else TTS_PITCH
        self.sample_rate = sample_rate or TTS_SAMPLE_RATE
        self.bitrate = bitrate or TTS_BITRATE
        self.audio_format = audio_format or TTS_FORMAT
        self.channel = channel or TTS_CHANNEL

        self.websocket = None
        self._ensure_output_dir()

        if not self.api_key:
            raise ValueError("API密钥未设置，请在config.py中设置MINIMAX_API_KEY或传入api_key参数")

    def _ensure_output_dir(self):

        if OUTPUT_DIR:

            abs_output_dir = os.path.abspath(OUTPUT_DIR)
            os.makedirs(abs_output_dir, exist_ok=True)
            logger.debug(f"输出目录已确保存在: {abs_output_dir}")

    async def _establish_connection(self):

        url = "wss://api.minimaxi.com/ws/v1/t2a_v2"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        ssl_context = ssl.create_default_context()

        try:
            logger.info("正在建立WebSocket连接...")
            ws = await websockets.connect(url, additional_headers=headers, ssl=ssl_context)
            connected = json.loads(await asyncio.wait_for(ws.recv(), 30))

            if connected.get("event") == "connected_success":
                logger.info("WebSocket连接成功")
                return ws
            else:
                logger.error(f"连接失败: {connected}")
                return None

        except Exception as e:
            logger.exception(f"建立连接异常: {e}")
            return None

    async def _start_task(self, websocket) -> bool:

        try:
            voice_setting = {
                "voice_id": self.voice_id,
                "speed": self.speed,
                "vol": self.volume,
                "pitch": self.pitch,
                "english_normalization": False
            }

            audio_setting = {
                "sample_rate": self.sample_rate,
                "bitrate": self.bitrate,
                "format": self.audio_format,
                "channel": self.channel
            }

            start_msg = {
                "event": "task_start",
                "model": self.model,
                "voice_setting": voice_setting,
                "audio_setting": audio_setting
            }

            await websocket.send(json.dumps(start_msg))
            response = json.loads(await asyncio.wait_for(websocket.recv(), 30))

            success = response.get("event") == "task_started"
            if not success:
                logger.error(f"任务启动失败: {response}")
            else:
                logger.info("任务启动成功")

            return success

        except Exception as e:
            logger.exception(f"启动任务异常: {e}")
            return False

    async def _synthesize_text(self,
                               websocket,
                               text: str,
                               progress_callback: Optional[Callable[[int, int], None]] = None) -> Optional[bytes]:

        try:
            await websocket.send(json.dumps({"event": "task_continue", "text": text}))

            chunk_counter = 0
            audio_data = b""

            while True:
                try:
                    response = json.loads(await asyncio.wait_for(websocket.recv(), 30))

                    if "data" in response and "audio" in response["data"]:
                        audio_hex = response["data"]["audio"]
                        if audio_hex:
                            chunk_counter += 1
                            audio_bytes = bytes.fromhex(audio_hex)
                            audio_data += audio_bytes

                            if progress_callback:
                                try:
                                    progress_callback(chunk_counter, -1)
                                except Exception as e:
                                    logger.warning(f"进度回调异常: {e}")

                            logger.debug(f"收到第 {chunk_counter} 段音频，大小: {len(audio_bytes)} 字节")

                    if response.get("is_final"):
                        logger.info(f"音频合成完成，共 {chunk_counter} 段，总大小: {len(audio_data)} 字节")
                        return audio_data

                except websockets.exceptions.ConnectionClosed:
                    logger.error("WebSocket连接已关闭")
                    return None
                except Exception as e:
                    logger.exception(f"接收数据异常: {e}")
                    return None

        except Exception as e:
            logger.exception(f"合成文本异常: {e}")
            return None

    async def _close_connection(self, websocket):

        if websocket:
            try:
                await websocket.send(json.dumps({"event": "task_finish"}))
                await websocket.close()
                logger.info("WebSocket连接已关闭")
            except Exception as e:
                logger.warning(f"关闭连接异常: {e}")

    async def synthesize_async(self,
                              text: str,
                              output_path: Optional[str] = None,
                              progress_callback: Optional[Callable[[int, int], None]] = None) -> Optional[str]:

        if not text or not text.strip():
            logger.error("文本内容为空")
            return None

        websocket = None
        try:

            websocket = await self._establish_connection()
            if not websocket:
                return None

            if not await self._start_task(websocket):
                return None

            audio_data = await self._synthesize_text(websocket, text, progress_callback)
            if not audio_data:
                return None

            if not output_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"tts_{timestamp}.{self.audio_format}"
                if OUTPUT_DIR:

                    abs_output_dir = os.path.abspath(OUTPUT_DIR)
                    output_path = os.path.join(abs_output_dir, filename)
                else:
                    output_path = filename
            else:

                if not os.path.isabs(output_path) and OUTPUT_DIR:
                    abs_output_dir = os.path.abspath(OUTPUT_DIR)
                    output_path = os.path.join(abs_output_dir, output_path)

            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            try:
                with open(output_path, "wb") as f:
                    f.write(audio_data)
                logger.info(f"音频文件已保存: {output_path}")
                return output_path
            except Exception as e:
                logger.exception(f"保存文件异常: {e}")
                return None

        except Exception as e:
            logger.exception(f"合成过程异常: {e}")
            return None
        finally:
            if websocket:
                await self._close_connection(websocket)

    def synthesize(self,
                   text: str,
                   output_path: Optional[str] = None,
                   progress_callback: Optional[Callable[[int, int], None]] = None) -> Optional[str]:

        if sys.platform == 'linux':
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            return loop.run_until_complete(
                self.synthesize_async(text, output_path, progress_callback)
            )
        else:
            return asyncio.run(
                self.synthesize_async(text, output_path, progress_callback)
            )

def synthesize_text(text: str,
                    output_path: Optional[str] = None,
                    **kwargs) -> Optional[str]:

    tts = TextToSpeech(**kwargs)
    return tts.synthesize(text, output_path)
