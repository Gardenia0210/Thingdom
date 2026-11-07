#!/usr/bin/env python3

import os
import sys
import logging
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

from config import (
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    CARD_BG_COLOR,
    CARD_CIRCLE_COLOR,
    CARD_TEXT_COLOR,
    CARD_IMAGE_SIZE,
    CARD_IMAGE_Y_OFFSET,
    FONT_EN_PATH,
    FONT_CN_PATH,
    FONT_EN_SIZE,
    FONT_CN_SIZE,
    DEBUG_LOG
)

logging.basicConfig(
    level=logging.DEBUG if DEBUG_LOG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FlashCardMaker:

    def __init__(self,
                 screen_width: Optional[int] = None,
                 screen_height: Optional[int] = None,
                 bg_color: Optional[Tuple[int, int, int]] = None,
                 circle_color: Optional[Tuple[int, int, int]] = None,
                 text_color: Optional[Tuple[int, int, int]] = None,
                 font_en_path: Optional[str] = None,
                 font_cn_path: Optional[str] = None,
                 font_en_size: Optional[int] = None,
                 font_cn_size: Optional[int] = None):

        self.screen_width = screen_width or SCREEN_WIDTH
        self.screen_height = screen_height or SCREEN_HEIGHT
        self.bg_color = bg_color or CARD_BG_COLOR
        self.circle_color = circle_color or CARD_CIRCLE_COLOR
        self.text_color = text_color or CARD_TEXT_COLOR

        self.font_en_path = font_en_path or FONT_EN_PATH
        self.font_cn_path = font_cn_path or FONT_CN_PATH
        self.font_en_size = font_en_size or FONT_EN_SIZE
        self.font_cn_size = font_cn_size or FONT_CN_SIZE

        self.center = self.screen_width // 2
        self.circle_radius = self.center - 20

        self.font_en = None
        self.font_cn = None
        self._load_fonts()

        logger.info("单词卡片制作工具初始化完成")

    def _load_fonts(self):

        try:

            if os.path.exists(self.font_en_path):
                self.font_en = ImageFont.truetype(self.font_en_path, self.font_en_size)
                logger.debug(f"英文字体加载成功: {self.font_en_path}")
            else:
                logger.warning(f"英文字体文件不存在: {self.font_en_path}，使用默认字体")
                self.font_en = ImageFont.load_default()
        except Exception as e:
            logger.warning(f"加载英文字体失败: {e}，使用默认字体")
            self.font_en = ImageFont.load_default()

        try:

            if os.path.exists(self.font_cn_path):
                self.font_cn = ImageFont.truetype(self.font_cn_path, self.font_cn_size)
                logger.debug(f"中文字体加载成功: {self.font_cn_path}")
            else:
                logger.warning(f"中文字体文件不存在: {self.font_cn_path}，使用默认字体")
                self.font_cn = ImageFont.load_default()
        except Exception as e:
            logger.warning(f"加载中文字体失败: {e}，使用默认字体")
            self.font_cn = ImageFont.load_default()

    def create_card(self,
                   image_path: str,
                   english_word: str,
                   chinese_word: str,
                   image_size: Optional[int] = None,
                   image_y_offset: Optional[int] = None) -> Image.Image:

        if image_path is not None and not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件不存在: {image_path}")

        image_size = image_size if image_size is not None else CARD_IMAGE_SIZE
        image_y_offset = image_y_offset if image_y_offset is not None else CARD_IMAGE_Y_OFFSET

        logger.info(f"创建单词卡片: {english_word} - {chinese_word}")

        try:

            canvas = Image.new('RGB', (self.screen_width, self.screen_height), self.bg_color)
            draw = ImageDraw.Draw(canvas)

            self._draw_circle_background(draw)

            if image_path is not None:
                with Image.open(image_path) as original:
                    img = original.convert("RGBA")
                img.thumbnail((image_size, image_size), Image.Resampling.LANCZOS)
                canvas.paste(img, (self.center - img.width // 2,
                                  self.center - img.height // 2 + image_y_offset), img)
                text_top = self.center + img.height // 2
            else:
                text_top = self.center
            self._draw_text(draw, english_word, chinese_word, text_top)

            logger.info("单词卡片创建完成")
            return canvas

        except Exception as e:
            logger.exception(f"创建单词卡片失败: {e}")
            raise

    def _draw_circle_background(self, draw: ImageDraw.Draw):

        try:
            margin = self.center - self.circle_radius
            x0 = margin
            y0 = margin
            x1 = self.screen_width - margin
            y1 = self.screen_height - margin

            draw.ellipse([x0, y0, x1, y1],
                        fill=self.circle_color, outline=self.circle_color)
            logger.debug("圆形背景绘制完成")
        except Exception as e:
            logger.exception(f"绘制圆形背景失败: {e}")
            raise

    def _draw_text(self, draw: ImageDraw.Draw, english: str, chinese: str, start_y: int):

        try:
            spacing = 20

            bbox_en = draw.textbbox((0, 0), english, font=self.font_en)
            text_width_en = bbox_en[2] - bbox_en[0]
            text_height_en = bbox_en[3] - bbox_en[1]

            x_en = self.center - text_width_en // 2
            y_en = start_y + spacing

            bbox_cn = draw.textbbox((0, 0), chinese, font=self.font_cn)
            text_width_cn = bbox_cn[2] - bbox_cn[0]
            text_height_cn = bbox_cn[3] - bbox_cn[1]

            x_cn = self.center - text_width_cn // 2
            y_cn = y_en + text_height_en + spacing

            draw.text((x_en, y_en), english, fill=self.text_color, font=self.font_en)
            draw.text((x_cn, y_cn), chinese, fill=self.text_color, font=self.font_cn)

            logger.debug("文字绘制完成")
        except Exception as e:
            logger.exception(f"绘制文字失败: {e}")
            raise

    def create_and_save(self,
                       image_path: str,
                       english_word: str,
                       chinese_word: str,
                       output_path: str,
                       image_size: Optional[int] = None,
                       image_y_offset: Optional[int] = None) -> str:

        try:
            card = self.create_card(image_path, english_word, chinese_word,
                                  image_size, image_y_offset)

            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            card.save(output_path)
            logger.info(f"单词卡片已保存: {output_path}")
            return output_path
        except Exception as e:
            logger.exception(f"保存单词卡片失败: {e}")
            raise

    def create_and_display(self,
                          image_path: str,
                          english_word: str,
                          chinese_word: str,
                          display_driver,
                          image_size: Optional[int] = None,
                          image_y_offset: Optional[int] = None,
                          islands_progress: Optional[list] = None):

        try:
            card = self.create_card(image_path, english_word, chinese_word,
                                  image_size, image_y_offset)

            logger.info("显示单词卡片到显示屏...")
            display_driver.display_image(card, islands_progress=islands_progress)
            logger.info("单词卡片显示完成")
        except Exception as e:
            logger.exception(f"显示单词卡片失败: {e}")
            raise

def create_flashcard(image_path: str,
                    english_word: str,
                    chinese_word: str,
                    output_path: Optional[str] = None,
                    **kwargs) -> Image.Image:

    maker = FlashCardMaker()
    card = maker.create_card(image_path, english_word, chinese_word, **kwargs)

    if output_path:
        maker.create_and_save(image_path, english_word, chinese_word, output_path, **kwargs)

    return card
