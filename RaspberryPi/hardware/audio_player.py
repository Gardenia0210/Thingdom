#!/usr/bin/env python3

import subprocess
import os
import sys
import logging
from typing import Optional, List

from config import DEBUG_LOG

logging.basicConfig(
    level=logging.DEBUG if DEBUG_LOG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AudioPlayer:

    def __init__(self, audio_device: Optional[str] = None):

        if audio_device is None:

            audio_device = self._detect_best_audio_device()

        self.audio_device = audio_device
        self.mpv_process = None
        self._mpv_installed = None
        logger.debug(f"音频播放器初始化，使用设备: {self.audio_device}")

    def _detect_best_audio_device(self) -> str:

        try:

            result = subprocess.run(
                ['pactl', 'list', 'short', 'sinks'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0 and result.stdout.strip():
                sinks = []
                for line in result.stdout.strip().split('\n'):
                    if line.strip():

                        parts = line.split('\t')
                        if len(parts) >= 2:
                            sink_name = parts[1].strip()
                            if sink_name:
                                sinks.append(sink_name)

                if sinks:

                    for sink in sinks:
                        sink_lower = sink.lower()

                        if any(keyword in sink_lower for keyword in ['blue', 'bluetooth', 'bt']):
                            device = f"pulse/{sink}"
                            logger.info(f"检测到蓝牙音频设备: {device}")
                            return device

                    device = f"pulse/{sinks[0]}"
                    logger.info(f"使用音频输出设备: {device}")
                    return device
            else:
                logger.debug("pactl 未返回音频输出列表，使用默认设备")
        except FileNotFoundError:
            logger.warning("pactl 命令未找到，使用默认音频设备")
        except subprocess.TimeoutExpired:
            logger.warning("检测音频设备超时，使用默认设备")
        except Exception as e:
            logger.warning(f"检测音频设备时出错: {e}")

        logger.debug("使用默认音频设备: pulse")
        return "pulse"

    def check_mpv_installed(self) -> bool:

        if self._mpv_installed is not None:
            return self._mpv_installed

        try:
            result = subprocess.run(
                ['mpv', '--version'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=True
            )
            self._mpv_installed = True
            logger.debug("MPV播放器已安装")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            self._mpv_installed = False
            logger.warning("MPV播放器未安装")
            return False

    def play_file(self,
                  file_path: str,
                  volume: Optional[float] = None,
                  wait: bool = True,
                  delete_after_play: bool = True) -> bool:

        if not self.check_mpv_installed():
            logger.error("MPV播放器未安装！请运行: sudo apt update && sudo apt install -y mpv")
            return False

        if not os.path.exists(file_path):
            logger.error(f"音频文件不存在: {file_path}")
            return False

        try:
            cmd = ['mpv', '--no-terminal', f'--audio-device={self.audio_device}']

            if volume is not None:
                cmd.extend(['--volume', str(volume)])

            cmd.append(file_path)

            logger.info(f"播放音频文件: {file_path}")

            if wait:

                result = subprocess.run(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=None
                )
                success = result.returncode == 0
                if success:
                    logger.info("播放完成")

                    if delete_after_play:
                        try:
                            if os.path.exists(file_path):
                                os.remove(file_path)
                                logger.info(f"已删除音频文件: {file_path}")
                            else:
                                logger.warning(f"文件不存在，无法删除: {file_path}")
                        except Exception as e:
                            logger.warning(f"删除文件失败: {file_path}, 错误: {e}")

                else:
                    logger.warning(f"播放可能异常结束，返回码: {result.returncode}")
                return success
            else:

                self.mpv_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                logger.info(f"后台播放已启动，PID: {self.mpv_process.pid}")

                if delete_after_play:
                    logger.warning("后台播放模式下，delete_after_play参数无效（无法确定播放完成时间）")

                return True

        except Exception as e:
            logger.exception(f"播放文件异常: {e}")
            return False

    def start_stream(self) -> bool:

        if not self.check_mpv_installed():
            logger.error("MPV播放器未安装！请运行: sudo apt update && sudo apt install -y mpv")
            return False

        if self.mpv_process is not None:
            logger.warning("流式播放已启动，先停止现有播放")
            self.stop_stream()

        try:
            cmd = [
                'mpv',
                '--no-cache',
                '--no-terminal',
                f'--audio-device={self.audio_device}',
                '--',
                'fd://0'
            ]

            self.mpv_process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False
            )

            logger.info("流式播放已启动")
            return True

        except Exception as e:
            logger.exception(f"启动流式播放异常: {e}")
            return False

    def play_stream_chunk(self, audio_data: bytes) -> bool:

        if self.mpv_process is None or self.mpv_process.stdin is None:
            logger.error("流式播放未启动，请先调用start_stream()")
            return False

        try:

            if isinstance(audio_data, str):
                audio_bytes = bytes.fromhex(audio_data)
            else:
                audio_bytes = audio_data

            if not audio_bytes:
                logger.warning("音频数据为空")
                return False

            self.mpv_process.stdin.write(audio_bytes)
            self.mpv_process.stdin.flush()

            logger.debug(f"已发送 {len(audio_bytes)} 字节音频数据")
            return True

        except BrokenPipeError:
            logger.error("MPV进程管道已断开")
            self.mpv_process = None
            return False
        except Exception as e:
            logger.exception(f"播放音频块异常: {e}")
            return False

    def stop_stream(self, timeout: float = 10.0) -> bool:

        if self.mpv_process is None:
            return True

        try:

            if self.mpv_process.stdin and not self.mpv_process.stdin.closed:
                try:
                    self.mpv_process.stdin.close()
                except Exception as e:
                    logger.warning(f"关闭stdin异常: {e}")

            try:
                self.mpv_process.wait(timeout=timeout)
                logger.info("流式播放已停止")
            except subprocess.TimeoutExpired:
                logger.warning("等待超时，强制终止进程")
                self.mpv_process.terminate()
                try:
                    self.mpv_process.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    logger.error("强制终止失败，使用kill")
                    self.mpv_process.kill()
                    self.mpv_process.wait()

            self.mpv_process = None
            return True

        except Exception as e:
            logger.exception(f"停止流式播放异常: {e}")
            self.mpv_process = None
            return False

    def is_playing(self) -> bool:

        if self.mpv_process is None:
            return False

        poll_result = self.mpv_process.poll()
        if poll_result is not None:

            self.mpv_process = None
            return False

        return True

    def get_available_audio_devices(self) -> List[str]:

        devices = []
        try:
            result = subprocess.run(
                ['pactl', 'list', 'short', 'sinks'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            sink_name = parts[1]
                            devices.append(f"pulse/{sink_name}")
        except Exception as e:
            logger.warning(f"获取音频设备列表时出错: {e}")

        return devices

    def cleanup(self):

        if self.mpv_process is not None:
            self.stop_stream()
        logger.debug("资源已清理")

def play_audio_file(file_path: str, delete_after_play: bool = True, **kwargs) -> bool:

    player = AudioPlayer()
    try:
        return player.play_file(file_path, delete_after_play=delete_after_play, **kwargs)
    finally:
        player.cleanup()
