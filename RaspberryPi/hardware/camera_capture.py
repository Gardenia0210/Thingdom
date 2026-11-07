#!/usr/bin/env python3

import os
import sys
import cv2
import numpy as np
import logging
from datetime import datetime
from typing import Optional

from config import (
    TEMP_DATA_DIR,
    DEBUG_LOG
)

logging.basicConfig(
    level=logging.DEBUG if DEBUG_LOG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CAMERA_WIDTH = 1920
CAMERA_HEIGHT = 1080

class CameraCapture:

    def __init__(self,
                 width: Optional[int] = None,
                 height: Optional[int] = None,
                 save_dir: Optional[str] = None):

        self.width = width or CAMERA_WIDTH
        self.height = height or CAMERA_HEIGHT
        self.save_dir = save_dir or TEMP_DATA_DIR

        if self.save_dir:
            os.makedirs(self.save_dir, exist_ok=True)
            logger.debug(f"保存目录已确保存在: {self.save_dir}")

    def capture_photo_usb_camera(self) -> Optional[np.ndarray]:

        logger.debug("尝试使用USB摄像头...")
        cap = cv2.VideoCapture(int(os.getenv("CAMERA_INDEX", "0")))

        if not cap.isOpened():
            logger.warning("USB摄像头无法打开")
            cap.release()
            return None

        try:

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

            logger.debug("让摄像头调整...")
            for _ in range(5):
                ret, frame = cap.read()
                if not ret:
                    logger.warning("无法从USB摄像头读取帧")
                    return None

            logger.debug("正在拍摄照片...")
            ret, frame = cap.read()

            if not ret or frame is None:
                logger.warning("拍摄失败")
                return None

            actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            logger.debug(f"实际分辨率: {actual_width}x{actual_height}")

            if actual_width != self.width or actual_height != self.height:
                logger.debug(f"调整图像分辨率到 {self.width}x{self.height}")
                frame = cv2.resize(frame, (self.width, self.height))

            return frame

        except Exception as e:
            logger.exception(f"USB摄像头拍摄异常: {e}")
            return None
        finally:
            cap.release()

    def capture(self) -> Optional[np.ndarray]:

        return self.capture_photo_usb_camera()

    def save_photo(self,
                   frame: np.ndarray,
                   filename: Optional[str] = None) -> Optional[str]:

        if frame is None:
            logger.error("照片数据为空")
            return None

        try:

            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"photo_{timestamp}.jpg"

            if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                filename += '.jpg'

            filepath = os.path.join(self.save_dir, filename)

            success = cv2.imwrite(filepath, frame)

            if success:
                file_size = os.path.getsize(filepath)
                logger.info(f"照片保存成功: {filepath} ({file_size / 1024:.2f} KB)")
                return filepath
            else:
                logger.error(f"照片保存失败: {filepath}")
                return None

        except Exception as e:
            logger.exception(f"保存照片异常: {e}")
            return None

    def capture_and_save(self, filename: Optional[str] = None) -> Optional[str]:

        frame = self.capture()
        if frame is None:
            logger.error("拍摄失败")
            return None

        return self.save_photo(frame, filename)

    def cleanup(self):

        logger.debug("摄像头工具清理完成")

def capture_photo(filename: Optional[str] = None,
                 save_dir: Optional[str] = None,
                 **kwargs) -> Optional[str]:

    camera = CameraCapture(save_dir=save_dir, **kwargs)
    return camera.capture_and_save(filename)
