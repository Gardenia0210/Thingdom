#!/usr/bin/env python3

import os
import sys
import json
import cv2
import numpy as np
import logging
from typing import Optional
from datetime import datetime

from config import (
    PROJECT_ROOT,
    FILE_OBJECT_NAME,
    DEBUG_LOG,
    TEMP_DATA_DIR
)

logging.basicConfig(
    level=logging.DEBUG if DEBUG_LOG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DEFAULT_HEARER_MODEL_PATH = os.path.join(PROJECT_ROOT, "yolo", "models", "best.pt")
DEFAULT_GENERAL_MODEL_PATH = os.path.join(PROJECT_ROOT, "yolo", "models", "yolo11n.pt")

class ObjectDetection:

    def __init__(self,
                 hearer_model_path: Optional[str] = None,
                 general_model_path: Optional[str] = None):

        try:
            from ultralytics import YOLO
            self.YOLO = YOLO
        except ImportError:
            raise ImportError("ultralytics 未安装，请运行: pip install ultralytics")

        self.hearer_model_path = hearer_model_path or DEFAULT_HEARER_MODEL_PATH
        self.general_model_path = general_model_path or DEFAULT_GENERAL_MODEL_PATH

        self._hearer_model = None
        self._general_model = None

        if not os.path.exists(self.hearer_model_path):
            logger.warning(f"hearer模型文件不存在: {self.hearer_model_path}")
        if not os.path.exists(self.general_model_path):
            logger.warning(f"通用模型文件不存在: {self.general_model_path}")

    def _load_local(self, path):
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        return self.YOLO(path)

    def _load_models(self):

        if self._hearer_model is None:
            try:
                logger.debug(f"加载hearer模型: {self.hearer_model_path}")
                self._hearer_model = self._load_local(self.hearer_model_path)
                logger.info("hearer模型加载成功")
            except Exception as e:
                logger.exception(f"加载hearer模型失败: {e}")
                raise

        if self._general_model is None:
            try:
                logger.debug(f"加载通用模型: {self.general_model_path}")
                self._general_model = self._load_local(self.general_model_path)
                logger.info("通用模型加载成功")
            except Exception as e:
                logger.exception(f"加载通用模型失败: {e}")
                raise

    def detect_closest_object(self, image_path: str) -> Optional[str]:

        if not os.path.exists(image_path):
            logger.error(f"图片文件不存在: {image_path}")
            return None

        try:

            self._load_models()

            img = cv2.imread(image_path)
            if img is None:
                logger.error(f"无法读取图片: {image_path}")
                return None

            logger.debug(f"开始检测图片: {image_path}")

            hearer_results = self._hearer_model(img, verbose=False)[0]
            hearer_boxes = hearer_results.boxes.xyxy.cpu().numpy()
            hearer_scores = hearer_results.boxes.conf.cpu().numpy()

            general_results = self._general_model(img, verbose=False)[0]
            other_boxes = general_results.boxes.xyxy.cpu().numpy()
            other_scores = general_results.boxes.conf.cpu().numpy()
            other_classes = general_results.boxes.cls.cpu().numpy()
            class_names = general_results.names

            closest_name = "null"

            if len(hearer_boxes) == 0:
                logger.debug("未检测到hearer")

                self._save_annotated_image(img, hearer_results, general_results, closest_name, image_path)
                return None

            best_idx = np.argmax(hearer_scores)
            best_hearer_score = hearer_scores[best_idx]
            logger.debug(f"检测到hearer，置信度: {best_hearer_score:.2f}")

            if best_hearer_score < 0.7:
                logger.debug(f"hearer置信度 {best_hearer_score:.2f} 低于阈值 0.7，视为无效识别")

                self._save_annotated_image(img, hearer_results, general_results, closest_name, image_path)
                return None

            best_hearer_box = hearer_boxes[best_idx]

            valid_objects = []
            ignore_classes = ["person", "frisbee"]

            for o_box, cls_idx, o_score in zip(other_boxes, other_classes, other_scores):
                obj_name = class_names[int(cls_idx)]
                if o_score < 0.25:
                    continue
                if obj_name in ignore_classes:
                    continue
                valid_objects.append((o_box, obj_name))

            logger.debug(f"检测到 {len(valid_objects)} 个有效物体")

            if len(valid_objects) == 0:
                logger.debug("未检测到其他有效物体")

                self._save_annotated_image(img, hearer_results, general_results, closest_name, image_path)
                return None

            hx1, hy1, hx2, hy2 = best_hearer_box
            hcx = (hx1 + hx2) / 2
            hcy = (hy1 + hy2) / 2

            min_dist = float("inf")
            for o_box, obj_name in valid_objects:
                ox1, oy1, ox2, oy2 = o_box
                ocx = (ox1 + ox2) / 2
                ocy = (oy1 + oy2) / 2
                dist = np.sqrt((hcx - ocx) ** 2 + (hcy - ocy) ** 2)
                if dist < min_dist:
                    min_dist = dist
                    closest_name = obj_name

            logger.info(f"检测到最接近的物体: {closest_name} (距离: {min_dist:.2f})")

            self._save_annotated_image(img, hearer_results, general_results, closest_name, image_path)

            return None if closest_name == "null" else closest_name

        except Exception as e:
            logger.exception(f"物体检测异常: {e}")

            try:
                if 'img' in locals() and 'hearer_results' in locals() and 'general_results' in locals():
                    self._save_annotated_image(img, hearer_results, general_results, "null", image_path)
            except:
                pass
            return None

    def _save_annotated_image(self, img, hearer_results, general_results, closest_name, original_image_path):

        return
        try:

            annotated_img = img.copy()

            if len(hearer_results.boxes) > 0:
                hearer_boxes = hearer_results.boxes.xyxy.cpu().numpy()
                hearer_scores = hearer_results.boxes.conf.cpu().numpy()
                best_idx = np.argmax(hearer_scores)
                best_box = hearer_boxes[best_idx].astype(int)
                score = hearer_scores[best_idx]

                x1, y1, x2, y2 = best_box
                cv2.rectangle(annotated_img, (x1, y1), (x2, y2), (0, 0, 255), 3)

                label = f"Hearer: {score:.2f}"
                label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                cv2.rectangle(annotated_img, (x1, y1 - label_size[1] - 10),
                             (x1 + label_size[0], y1), (0, 0, 255), -1)
                cv2.putText(annotated_img, label, (x1, y1 - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            if len(general_results.boxes) > 0:
                other_boxes = general_results.boxes.xyxy.cpu().numpy()
                other_scores = general_results.boxes.conf.cpu().numpy()
                other_classes = general_results.boxes.cls.cpu().numpy()
                class_names = general_results.names

                ignore_classes = ["person", "frisbee"]

                for o_box, cls_idx, o_score in zip(other_boxes, other_classes, other_scores):
                    obj_name = class_names[int(cls_idx)]

                    if o_score < 0.25:
                        continue
                    if obj_name in ignore_classes:
                        continue

                    is_closest = (obj_name == closest_name)
                    color = (0, 255, 0) if is_closest else (255, 255, 0)
                    thickness = 3 if is_closest else 2

                    x1, y1, x2, y2 = o_box.astype(int)
                    cv2.rectangle(annotated_img, (x1, y1), (x2, y2), color, thickness)

                    label = f"{obj_name}: {o_score:.2f}"
                    if is_closest:
                        label = f"★ {label}"

                    label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    cv2.rectangle(annotated_img, (x1, y1 - label_size[1] - 10),
                                 (x1 + label_size[0], y1), color, -1)
                    cv2.putText(annotated_img, label, (x1, y1 - 5),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = os.path.splitext(os.path.basename(original_image_path))[0]
            output_filename = f"{base_name}_annotated_{timestamp}.jpg"
            output_path = os.path.join(TEMP_DATA_DIR, output_filename)

            os.makedirs(TEMP_DATA_DIR, exist_ok=True)

            success = cv2.imwrite(output_path, annotated_img)
            if success:
                logger.info(f"带标签的图片已保存: {output_path}")
                print(f"[ObjectDetection] 带标签的图片已保存: {output_path}")
            else:
                logger.error(f"保存带标签图片失败: {output_path}")
                print(f"[ObjectDetection] 错误: 保存带标签图片失败: {output_path}")

        except Exception as e:
            logger.exception(f"保存带标签图片异常: {e}")
            print(f"[ObjectDetection] 错误: 保存带标签图片异常: {e}")
            import traceback
            traceback.print_exc()

    def detect_and_save(self,
                       image_path: str,
                       output_file: Optional[str] = None) -> bool:

        output_file = output_file or FILE_OBJECT_NAME

        try:

            object_name = self.detect_closest_object(image_path)

            result = {
                "object_name": object_name
            }

            output_dir = os.path.dirname(output_file)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=4)

            logger.info(f"检测结果已保存到: {output_file}")
            logger.debug(f"检测结果: {result}")
            return True

        except Exception as e:
            logger.exception(f"保存检测结果异常: {e}")
            return False

def detect_object(image_path: str,
                 output_file: Optional[str] = None,
                 **kwargs) -> bool:

    detector = ObjectDetection(**kwargs)
    return detector.detect_and_save(image_path, output_file)
