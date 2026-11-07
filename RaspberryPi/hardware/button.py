#!/usr/bin/env python3

import os
import sys
import time
import logging
from typing import Optional, Callable

from config import (
    GPIO_CHIP,
    USE_GPIO,
    BUTTON_PIN,
    DEBOUNCE_TIME,
    BUTTON_LONG_PRESS_TIME,
    DEBUG_LOG
)

logging.basicConfig(
    level=logging.DEBUG if DEBUG_LOG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Button:

    def __init__(self,
                 pin: Optional[int] = None,
                 debounce_time: Optional[float] = None,
                 use_gpio: Optional[bool] = None):

        self.pin = pin if pin is not None else BUTTON_PIN
        self.debounce_time = debounce_time if debounce_time is not None else DEBOUNCE_TIME
        self.use_gpio = use_gpio if use_gpio is not None else USE_GPIO

        self.gpio_chip = None
        self._initialized = False

        if self.use_gpio:
            self._init_gpio()
        else:
            logger.warning("GPIO未启用，按钮检测功能不可用")

    def _init_gpio(self):

        try:
            import lgpio
            self.gpio_chip = lgpio.gpiochip_open(GPIO_CHIP)

            lgpio.gpio_claim_input(self.gpio_chip, self.pin, lgpio.SET_PULL_UP)
            self._initialized = True
            logger.info(f"按钮初始化成功，引脚 BCM {self.pin}（低电平触发）")
        except ImportError:
            logger.error("lgpio 未安装，请运行: pip3 install lgpio")
            self._initialized = False
        except Exception as e:
            logger.exception(f"GPIO初始化失败: {e}")
            self._initialized = False

    def is_pressed(self) -> bool:

        if not self._initialized:
            logger.warning("GPIO未初始化，无法检测")
            return False

        try:
            import lgpio

            state = lgpio.gpio_read(self.gpio_chip, self.pin)
            return state == 0
        except Exception as e:
            logger.exception(f"读取GPIO状态失败: {e}")
            return False

    def wait_for_press(self, timeout: Optional[float] = None) -> bool:

        if not self._initialized:
            logger.warning("GPIO未初始化，无法检测")
            return False

        start_time = time.time()
        last_press_time = 0

        while True:
            if timeout and (time.time() - start_time) > timeout:
                logger.debug("等待按下超时")
                return False

            if self.is_pressed():
                now = time.time()

                if now - last_press_time >= self.debounce_time:
                    logger.debug("检测到按下")
                    return True
                time.sleep(0.01)
            else:
                last_press_time = 0
                time.sleep(0.01)

    def wait_for_release(self, timeout: Optional[float] = None) -> bool:

        if not self._initialized:
            logger.warning("GPIO未初始化，无法检测")
            return False

        start_time = time.time()
        last_release_time = 0

        while True:
            if timeout and (time.time() - start_time) > timeout:
                logger.debug("等待释放超时")
                return False

            if not self.is_pressed():
                now = time.time()

                if now - last_release_time >= self.debounce_time:
                    logger.debug("检测到释放")
                    return True
                time.sleep(0.01)
            else:
                last_release_time = 0
                time.sleep(0.01)

    def wait_for_long_press(self, long_press_time: Optional[float] = None, timeout: Optional[float] = None) -> bool:

        if not self._initialized:
            logger.warning("GPIO未初始化，无法检测")
            return False

        long_press_duration = long_press_time if long_press_time is not None else BUTTON_LONG_PRESS_TIME
        start_time = time.time()

        if not self.wait_for_press(timeout=timeout):
            return False

        press_start_time = time.time()
        logger.debug(f"检测到按下，开始计时长按（需要 {long_press_duration} 秒）...")

        while self.is_pressed():
            elapsed = time.time() - press_start_time

            if elapsed >= long_press_duration:
                logger.debug(f"检测到长按（持续 {elapsed:.2f} 秒）")
                return True

            if timeout and (time.time() - start_time) > timeout:
                logger.debug("等待长按超时")
                return False

            time.sleep(0.01)

        logger.debug("按钮提前释放，未达到长按时间")
        return False

    def monitor(self, press_callback: Optional[Callable[[], None]] = None,
                release_callback: Optional[Callable[[], None]] = None,
                poll_interval: float = 0.01):

        if not self._initialized:
            logger.warning("GPIO未初始化，无法监控")
            return

        last_state = False
        last_change_time = 0

        logger.info("开始监控按钮...")

        try:
            while True:
                current_state = self.is_pressed()

                if current_state != last_state:
                    now = time.time()
                    if now - last_change_time >= self.debounce_time:
                        last_state = current_state
                        last_change_time = now

                        if current_state:
                            logger.debug("检测到按下")
                            if press_callback:
                                try:
                                    press_callback()
                                except Exception as e:
                                    logger.exception(f"按下回调异常: {e}")
                        else:
                            logger.debug("检测到释放")
                            if release_callback:
                                try:
                                    release_callback()
                                except Exception as e:
                                    logger.exception(f"释放回调异常: {e}")

                time.sleep(poll_interval)

        except KeyboardInterrupt:
            logger.info("监控被用户中断")
        except Exception as e:
            logger.exception(f"监控过程异常: {e}")

    def cleanup(self):

        if self.gpio_chip:
            try:
                import lgpio

                try:
                    lgpio.gpio_free(self.gpio_chip, self.pin)
                except Exception as free_error:

                    if "not allocated" not in str(free_error).lower():
                        logger.debug(f"释放GPIO时出错（可忽略）: {free_error}")

                try:
                    lgpio.gpiochip_close(self.gpio_chip)
                except Exception as close_error:
                    logger.debug(f"关闭GPIO芯片时出错（可忽略）: {close_error}")

                self.gpio_chip = None
                self._initialized = False
                logger.info("资源已清理")
            except Exception as e:

                if "not allocated" not in str(e).lower():
                    logger.warning(f"清理资源时出错: {e}")
                else:
                    logger.debug(f"清理资源时GPIO未分配（可忽略）: {e}")
