#!/usr/bin/env python3

import spidev
import RPi.GPIO as GPIO
import time
import os
import sys
import logging
import math
from typing import Optional, Union
from PIL import Image, ImageDraw

from config import (
    SCREEN_RST_PIN,
    SCREEN_DC_PIN,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    SCREEN_SPI_SPEED,
    DEBUG_LOG,
    PROGRESS_RING_WIDTH,
    PROGRESS_RING_COLOR_COMPLETED,
    PROGRESS_RING_COLOR_INCOMPLETE,
    PROGRESS_RING_COLOR_LOCKED
)

logging.basicConfig(
    level=logging.DEBUG if DEBUG_LOG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EP1831TDriver:

    def __init__(self,
                 rst_pin: Optional[int] = None,
                 dc_pin: Optional[int] = None,
                 width: Optional[int] = None,
                 height: Optional[int] = None,
                 spi_speed: Optional[int] = None,
                 spi_bus: int = 0,
                 spi_device: int = 0):

        self.rst_pin = rst_pin or SCREEN_RST_PIN
        self.dc_pin = dc_pin or SCREEN_DC_PIN
        self.width = width or SCREEN_WIDTH
        self.height = height or SCREEN_HEIGHT
        self.spi_speed = spi_speed or SCREEN_SPI_SPEED

        self.spi = None
        self._initialized = False

        try:
            self._init_gpio()
            self._init_spi(spi_bus, spi_device)
            logger.info("EP1831T 初始化中...")
            self.reset()
            self.init_display()
            self._initialized = True
            logger.info("EP1831T 初始化完成")
        except Exception as e:
            logger.exception(f"EP1831T 初始化失败: {e}")
            self.cleanup()
            raise

    def _init_gpio(self):

        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(self.rst_pin, GPIO.OUT)
            GPIO.setup(self.dc_pin, GPIO.OUT)
            logger.debug(f"GPIO初始化完成: RST={self.rst_pin}, DC={self.dc_pin}")
        except Exception as e:
            logger.exception(f"GPIO初始化失败: {e}")
            raise

    def _init_spi(self, bus: int, device: int):

        try:
            self.spi = spidev.SpiDev()
            self.spi.open(bus, device)
            self.spi.max_speed_hz = self.spi_speed
            self.spi.mode = 0
            logger.debug(f"SPI初始化完成: bus={bus}, device={device}, speed={self.spi_speed}Hz")
        except Exception as e:
            logger.exception(f"SPI初始化失败: {e}")
            raise

    def reset(self):

        try:
            GPIO.output(self.rst_pin, GPIO.HIGH)
            time.sleep(0.01)
            GPIO.output(self.rst_pin, GPIO.LOW)
            time.sleep(0.01)
            GPIO.output(self.rst_pin, GPIO.HIGH)
            time.sleep(0.12)
            logger.debug("显示屏复位完成")
        except Exception as e:
            logger.exception(f"复位失败: {e}")
            raise

    def write_cmd(self, cmd: int):

        try:
            GPIO.output(self.dc_pin, GPIO.LOW)
            self.spi.writebytes([cmd])
        except Exception as e:
            logger.exception(f"写入命令失败: {e}")
            raise

    def write_data(self, data: Union[int, list]):

        try:
            GPIO.output(self.dc_pin, GPIO.HIGH)
            if isinstance(data, int):
                self.spi.writebytes([data])
            else:
                self.spi.writebytes(data)
        except Exception as e:
            logger.exception(f"写入数据失败: {e}")
            raise

    def write_data_array(self, data: list):

        try:
            GPIO.output(self.dc_pin, GPIO.HIGH)
            chunk_size = 4096
            for i in range(0, len(data), chunk_size):
                self.spi.writebytes(data[i:i+chunk_size])
        except Exception as e:
            logger.exception(f"写入数据数组失败: {e}")
            raise

    def init_display(self):

        try:

            init_commands = [
                (0xF0, 0x28), (0xF2, 0x28),
                (0x73, 0xF0), (0x7C, 0xD1), (0x83, 0xE0), (0x84, 0x61), (0xF2, 0x82),
                (0xF0, 0x00), (0xF0, 0x01), (0xF1, 0x01),
                (0xB0, 0x56), (0xB1, 0x4D), (0xB2, 0x24), (0xB4, 0x87),
                (0xB5, 0x44), (0xB6, 0x8B), (0xB7, 0x40), (0xB8, 0x86),
                (0xBA, 0x00), (0xBB, 0x08), (0xBC, 0x08), (0xBD, 0x00),
                (0xC0, 0x80), (0xC1, 0x10), (0xC2, 0x37), (0xC3, 0x80),
                (0xC4, 0x10), (0xC5, 0x37), (0xC6, 0xA9), (0xC7, 0x41),
                (0xC8, 0x01), (0xC9, 0xA9), (0xCA, 0x41), (0xCB, 0x01),
                (0xD0, 0x91), (0xD1, 0x68), (0xD2, 0x68),
                (0xF5, [0x00, 0xA5]),
                (0xDD, 0x4F), (0xDE, 0x4F),
                (0xF1, 0x10), (0xF0, 0x00), (0xF0, 0x02),
                (0xE0, [0xF0, 0x0A, 0x10, 0x09, 0x09, 0x36, 0x35, 0x33, 0x4A, 0x29, 0x15, 0x15, 0x2E, 0x34]),
                (0xE1, [0xF0, 0x0A, 0x0F, 0x08, 0x08, 0x05, 0x34, 0x33, 0x4A, 0x39, 0x15, 0x15, 0x2D, 0x33]),
                (0xF0, 0x10), (0xF3, 0x10),
                (0xE0, 0x07), (0xE1, 0x00), (0xE2, 0x00), (0xE3, 0x00),
                (0xE4, 0xE0), (0xE5, 0x06), (0xE6, 0x21), (0xE7, 0x01),
                (0xE8, 0x05), (0xE9, 0x02), (0xEA, 0xDA), (0xEB, 0x00),
                (0xEC, 0x00), (0xED, 0x0F), (0xEE, 0x00), (0xEF, 0x00),
                (0xF8, 0x00), (0xF9, 0x00), (0xFA, 0x00), (0xFB, 0x00),
                (0xFC, 0x00), (0xFD, 0x00), (0xFE, 0x00), (0xFF, 0x00),
                (0x60, 0x40), (0x61, 0x04), (0x62, 0x00), (0x63, 0x42),
                (0x64, 0xD9), (0x65, 0x00), (0x66, 0x00), (0x67, 0x00),
                (0x68, 0x00), (0x69, 0x00), (0x6A, 0x00), (0x6B, 0x00),
                (0x70, 0x40), (0x71, 0x03), (0x72, 0x00), (0x73, 0x42),
                (0x74, 0xD8), (0x75, 0x00), (0x76, 0x00), (0x77, 0x00),
                (0x78, 0x00), (0x79, 0x00), (0x7A, 0x00), (0x7B, 0x00),
            ]

            for cmd, data in init_commands:
                self.write_cmd(cmd)
                if isinstance(data, list):
                    self.write_data(data)
                else:
                    self.write_data(data)

            timing_configs = [
                (0x80, [0x48, 0x00, 0x06, 0x02, 0xD6, 0x04, 0x00, 0x00]),
                (0x88, [0x48, 0x00, 0x08, 0x02, 0xD8, 0x04, 0x00, 0x00]),
                (0x90, [0x48, 0x00, 0x0A, 0x02, 0xDA, 0x04, 0x00, 0x00]),
                (0x98, [0x48, 0x00, 0x0C, 0x02, 0xDC, 0x04, 0x00, 0x00]),
                (0xA0, [0x48, 0x00, 0x05, 0x02, 0xD5, 0x04, 0x00, 0x00]),
                (0xA8, [0x48, 0x00, 0x07, 0x02, 0xD7, 0x04, 0x00, 0x00]),
                (0xB0, [0x48, 0x00, 0x09, 0x02, 0xD9, 0x04, 0x00, 0x00]),
                (0xB8, [0x48, 0x00, 0x0B, 0x02, 0xDB, 0x04, 0x00, 0x00]),
            ]

            for base_addr, values in timing_configs:
                for i, val in enumerate(values):
                    self.write_cmd(base_addr + i)
                    self.write_data(val)

            source_configs = [
                (0xC0, [0x10, 0x47, 0x56, 0x65, 0x74, 0x88, 0x99, 0x01, 0xBB, 0xAA]),
                (0xD0, [0x10, 0x47, 0x56, 0x65, 0x74, 0x88, 0x99, 0x01, 0xBB, 0xAA]),
            ]

            for base_addr, values in source_configs:
                for i, val in enumerate(values):
                    self.write_cmd(base_addr + i)
                    self.write_data(val)

            self.write_cmd(0xF3)
            self.write_data(0x01)
            self.write_cmd(0xF0)
            self.write_data(0x00)

            self.write_cmd(0x3A)
            self.write_data(0x66)

            self.write_cmd(0x21)
            self.write_cmd(0x11)
            time.sleep(0.12)
            self.write_cmd(0x29)

            logger.info("显示屏初始化完成")

        except Exception as e:
            logger.exception(f"初始化显示屏失败: {e}")
            raise

    def set_window(self, x0: int, y0: int, x1: int, y1: int):

        try:
            self.write_cmd(0x2A)
            self.write_data([
                (x0 >> 8) & 0xFF, x0 & 0xFF,
                (x1 >> 8) & 0xFF, x1 & 0xFF
            ])

            self.write_cmd(0x2B)
            self.write_data([
                (y0 >> 8) & 0xFF, y0 & 0xFF,
                (y1 >> 8) & 0xFF, y1 & 0xFF
            ])

            self.write_cmd(0x2C)
        except Exception as e:
            logger.exception(f"设置窗口失败: {e}")
            raise

    def display_image(self, image: Union[str, Image.Image], islands_progress: Optional[list] = None):

        if not self._initialized:
            raise RuntimeError("显示屏未初始化，请先调用初始化方法")

        try:

            if isinstance(image, str):
                if not os.path.exists(image):
                    raise FileNotFoundError(f"图片文件不存在: {image}")
                img = Image.open(image)
                logger.debug(f"加载图片: {image}")
            else:
                img = image

            if img.size != (self.width, self.height):
                logger.warning(f"图片尺寸不匹配: {img.size}, 期望: ({self.width}, {self.height})")
                img = img.resize((self.width, self.height), Image.Resampling.LANCZOS)
                logger.info(f"图片已缩放至: ({self.width}, {self.height})")

            if img.mode != 'RGB':
                if img.mode == 'RGBA':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])
                    img = background
                else:
                    img = img.convert('RGB')

            if islands_progress:
                img = self._add_progress_ring_on_top(img, islands_progress)

            logger.debug("转换图片数据为RGB888格式...")
            pixels = img.load()
            image_data = []

            for y in range(self.height):
                for x in range(self.width):
                    r, g, b = pixels[x, y]
                    image_data.extend([r, g, b])

            logger.debug(f"图片数据大小: {len(image_data)} 字节")

            self.set_window(0, 0, self.width - 1, self.height - 1)
            self.write_data_array(image_data)

            logger.info("图片显示完成")

        except Exception as e:
            logger.exception(f"显示图片失败: {e}")
            raise

    def _add_progress_ring_on_top(self, img: Image.Image, islands_progress: list) -> Image.Image:

        try:

            progress_info = None
            for island in islands_progress:
                if isinstance(island, dict) and island.get("island_inner_id") == 1:
                    progress_info = island
                    break

            if not progress_info:
                logger.debug("未找到 island_inner_id = 1 的进度信息，跳过进度环绘制")
                return img

            learned_percentage = progress_info.get("learned_percentage", "0.00")
            is_locked = progress_info.get("is_locked", False)

            try:
                if isinstance(learned_percentage, str):
                    progress = float(learned_percentage)
                else:
                    progress = float(learned_percentage)
            except (ValueError, TypeError):
                logger.warning(f"无效的进度值: {learned_percentage}，使用默认值0")
                progress = 0.0

            progress = max(0.0, min(100.0, progress))

            result_img = img.copy()

            ring_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
            ring_draw = ImageDraw.Draw(ring_layer)

            self._draw_progress_ring(ring_draw, img.size, progress, is_locked)

            result_img = Image.alpha_composite(
                result_img.convert('RGBA'),
                ring_layer
            ).convert('RGB')

            logger.debug(f"进度环图层已添加: 进度={progress}%, 锁定={is_locked}")
            return result_img

        except Exception as e:
            logger.warning(f"绘制进度环时出错: {e}，返回原图片")
            return img

    def _draw_progress_ring(self, draw: ImageDraw.Draw, size: tuple, progress: float, is_locked: bool):

        width, height = size
        center_x = width // 2
        center_y = height // 2

        outer_radius = min(width, height) // 2
        inner_radius = outer_radius - PROGRESS_RING_WIDTH

        if is_locked:
            ring_color = PROGRESS_RING_COLOR_LOCKED + (255,)
        else:
            ring_color = PROGRESS_RING_COLOR_COMPLETED + (255,)

        incomplete_color = PROGRESS_RING_COLOR_INCOMPLETE + (255,)

        outer_bbox = (
            center_x - outer_radius,
            center_y - outer_radius,
            center_x + outer_radius,
            center_y + outer_radius
        )

        inner_bbox = (
            center_x - inner_radius,
            center_y - inner_radius,
            center_x + inner_radius,
            center_y + inner_radius
        )

        draw.ellipse(outer_bbox, fill=incomplete_color, outline=incomplete_color)

        draw.ellipse(inner_bbox, fill=(0, 0, 0, 0), outline=(0, 0, 0, 0))

        if progress > 0 and not is_locked:

            start_angle = -90
            end_angle = start_angle + (progress / 100.0) * 360

            draw.pieslice(
                outer_bbox,
                start=start_angle,
                end=end_angle,
                fill=ring_color,
                outline=ring_color
            )

            draw.ellipse(inner_bbox, fill=(0, 0, 0, 0), outline=(0, 0, 0, 0))

        elif is_locked:

            draw.ellipse(outer_bbox, fill=ring_color, outline=ring_color)

            draw.ellipse(inner_bbox, fill=(0, 0, 0, 0), outline=(0, 0, 0, 0))

    def fill_color(self, r: int, g: int, b: int):

        try:
            self.set_window(0, 0, self.width - 1, self.height - 1)

            row_data = [r, g, b] * self.width

            for y in range(self.height):
                self.write_data_array(row_data)

            logger.info(f"填充颜色完成: RGB({r}, {g}, {b})")

        except Exception as e:
            logger.exception(f"填充颜色失败: {e}")
            raise

    def cleanup(self):

        try:
            if self.spi:
                self.spi.close()
                self.spi = None
            GPIO.cleanup()
            self._initialized = False
            logger.info("资源已清理")
        except Exception as e:
            logger.warning(f"清理资源时出错: {e}")
