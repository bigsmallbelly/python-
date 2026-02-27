"""
麻將牌影像辨識模組
Mahjong Tile Image Recognition Module

辨識流程：
1. 讀取圖片 → 灰階化 → 自適應二值化
2. 輪廓偵測 → 找出牌面區域（接近正方形的矩形）
3. 每張牌 ROI → 特徵提取 → 分類器預測牌名

支援兩種辨識後端：
 a) Template Matching（無需訓練，準確率中等）
 b) CNN 分類器（需先執行 train_classifier.py，準確率高）

依賴套件：pip install opencv-python-headless numpy pillow
"""
from __future__ import annotations

import os
import re
import json
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Dict

import cv2
import numpy as np

log = logging.getLogger(__name__)

# ─── 牌名對照 ─────────────────────────────────────────────────────────────────
#   key: 顯示名稱（與 tiles.py 一致）
#   value: 分類索引（用於CNN）

TILE_NAMES: List[str] = (
    [f"{i}萬" for i in range(1, 10)] +
    [f"{i}條" for i in range(1, 10)] +
    [f"{i}餅" for i in range(1, 10)] +
    ["東", "南", "西", "北"] +
    ["中", "發", "白"] +
    ["梅", "蘭", "菊", "竹", "春", "夏", "秋", "冬"]
)
TILE_INDEX: Dict[str, int] = {name: i for i, name in enumerate(TILE_NAMES)}
NUM_CLASSES = len(TILE_NAMES)   # 43


# ─── 影像前處理工具 ───────────────────────────────────────────────────────────

class ImagePreprocessor:
    """共用前處理管線"""

    @staticmethod
    def to_gray(img: np.ndarray) -> np.ndarray:
        if len(img.shape) == 3:
            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return img

    @staticmethod
    def denoise(gray: np.ndarray) -> np.ndarray:
        return cv2.GaussianBlur(gray, (5, 5), 0)

    @staticmethod
    def binarize(gray: np.ndarray) -> np.ndarray:
        return cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 2
        )

    @staticmethod
    def normalize(roi: np.ndarray, size: int = 64) -> np.ndarray:
        resized = cv2.resize(roi, (size, size), interpolation=cv2.INTER_AREA)
        return resized.astype(np.float32) / 255.0


# ─── 牌面偵測 ────────────────────────────────────────────────────────────────

class TileDetector:
    """
    從整張桌面圖片中偵測並裁切出每張麻將牌的 ROI
    """

    MIN_AREA = 1_500      # 最小面積（過濾雜訊）
    MAX_AREA = 200_000    # 最大面積
    ASPECT_RATIO_RANGE = (0.6, 1.7)   # 寬高比範圍（麻將牌約 0.8~1.2）

    def detect(self, img: np.ndarray) -> List[Tuple[np.ndarray, Tuple[int, int, int, int]]]:
        """
        回傳 [(roi_bgr, (x,y,w,h)), ...]，已由左而右、由上而下排序
        """
        prep = ImagePreprocessor()
        gray = prep.to_gray(img)
        blurred = prep.denoise(gray)
        binary = prep.binarize(blurred)

        # 形態學閉運算以連接破碎邊緣
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)

        rois = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if not (self.MIN_AREA <= area <= self.MAX_AREA):
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            ratio = w / h if h > 0 else 0
            if not (self.ASPECT_RATIO_RANGE[0] <= ratio <= self.ASPECT_RATIO_RANGE[1]):
                continue

            roi = img[y:y + h, x:x + w]
            rois.append((roi, (x, y, w, h)))

        # 由左而右、由上而下排序
        rois.sort(key=lambda r: (r[1][1] // 60, r[1][0]))
        return rois

    def visualize(self, img: np.ndarray,
                  detections: List[Tuple[np.ndarray, Tuple[int, int, int, int]]],
                  labels: Optional[List[str]] = None) -> np.ndarray:
        """在原圖上繪製偵測框與標籤"""
        vis = img.copy()
        for i, (_, (x, y, w, h)) in enumerate(detections):
            cv2.rectangle(vis, (x, y), (x + w, y + h), (0, 255, 0), 2)
            if labels and i < len(labels):
                cv2.putText(vis, labels[i], (x, y - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 0), 2)
        return vis


# ─── Template Matching 後端 ───────────────────────────────────────────────────

class TemplateMatcher:
    """
    使用範本比對辨識麻將牌。
    templates_dir 需包含 {tile_name}.png / .jpg 的範本圖（64x64 灰階）。
    """

    def __init__(self, templates_dir: str | Path):
        self.templates_dir = Path(templates_dir)
        self.templates: Dict[str, np.ndarray] = {}
        self._load_templates()

    def _load_templates(self):
        exts = (".png", ".jpg", ".jpeg", ".bmp")
        for fp in self.templates_dir.iterdir():
            if fp.suffix.lower() in exts:
                gray = cv2.imread(str(fp), cv2.IMREAD_GRAYSCALE)
                if gray is None:
                    continue
                resized = cv2.resize(gray, (64, 64))
                stem = fp.stem  # filename without extension = tile name
                self.templates[stem] = resized
        log.info("載入 %d 個麻將範本", len(self.templates))

    def predict(self, roi: np.ndarray) -> Tuple[str, float]:
        """
        回傳 (tile_name, confidence 0~1)
        confidence = 1 - min_distance_ratio
        """
        if not self.templates:
            return "未知", 0.0

        prep = ImagePreprocessor()
        gray = prep.to_gray(roi)
        gray = cv2.resize(gray, (64, 64))

        best_name = "未知"
        best_score = -1.0
        for name, tmpl in self.templates.items():
            res = cv2.matchTemplate(gray, tmpl, cv2.TM_CCOEFF_NORMED)
            score = float(res[0][0])
            if score > best_score:
                best_score = score
                best_name = name

        return best_name, max(0.0, best_score)

    def predict_batch(self, rois: List[np.ndarray]) -> List[Tuple[str, float]]:
        return [self.predict(roi) for roi in rois]


# ─── CNN 後端 (PyTorch) ───────────────────────────────────────────────────────

class CNNRecognizer:
    """
    使用 CNN 模型辨識麻將牌。
    model_path：事先訓練好的 .pt 檔（使用 train_classifier.py）。
    """

    INPUT_SIZE = 64

    def __init__(self, model_path: str | Path):
        try:
            import torch
            import torch.nn as nn
            self._torch = torch
            self._nn = nn
        except ImportError:
            raise ImportError("請安裝 PyTorch：pip install torch torchvision")

        self.model = self._build_model()
        self.model.load_state_dict(
            self._torch.load(str(model_path), map_location="cpu")
        )
        self.model.eval()

    def _build_model(self):
        import torch.nn as nn

        class TileCNN(nn.Module):
            def __init__(self):
                super().__init__()
                self.features = nn.Sequential(
                    nn.Conv2d(1, 32, 3, padding=1), nn.ReLU(),
                    nn.MaxPool2d(2),
                    nn.Conv2d(32, 64, 3, padding=1), nn.ReLU(),
                    nn.MaxPool2d(2),
                    nn.Conv2d(64, 128, 3, padding=1), nn.ReLU(),
                    nn.MaxPool2d(2),
                )
                self.classifier = nn.Sequential(
                    nn.Flatten(),
                    nn.Linear(128 * 8 * 8, 256), nn.ReLU(), nn.Dropout(0.4),
                    nn.Linear(256, NUM_CLASSES),
                )

            def forward(self, x):
                return self.classifier(self.features(x))

        return TileCNN()

    def predict(self, roi: np.ndarray) -> Tuple[str, float]:
        import torch

        prep = ImagePreprocessor()
        gray = prep.to_gray(roi)
        norm = prep.normalize(gray, self.INPUT_SIZE)          # (64,64) float32 0~1
        tensor = torch.tensor(norm).unsqueeze(0).unsqueeze(0)  # (1,1,64,64)

        with torch.no_grad():
            logits = self.model(tensor)
            probs = torch.softmax(logits, dim=1)[0]
            idx = int(probs.argmax())
            conf = float(probs[idx])

        return TILE_NAMES[idx], conf

    def predict_batch(self, rois: List[np.ndarray]) -> List[Tuple[str, float]]:
        return [self.predict(roi) for roi in rois]


# ─── 高階辨識器 ───────────────────────────────────────────────────────────────

class MahjongRecognizer:
    """
    端對端麻將影像辨識器：
      圖片 → 偵測牌面 → 辨識每張牌 → 回傳牌名列表
    """

    CONFIDENCE_THRESHOLD = 0.50

    def __init__(self, backend: str = "template",
                 templates_dir: Optional[str] = None,
                 model_path: Optional[str] = None):
        """
        backend: "template" | "cnn"
        templates_dir: 範本圖資料夾（template 模式需要）
        model_path: CNN 模型路徑（cnn 模式需要）
        """
        self.detector = TileDetector()

        if backend == "cnn":
            if model_path is None:
                raise ValueError("cnn 模式需要 model_path")
            self.classifier = CNNRecognizer(model_path)
        else:
            if templates_dir is None:
                raise ValueError("template 模式需要 templates_dir")
            self.classifier = TemplateMatcher(templates_dir)  # type: ignore[assignment]

    def recognize_file(self, image_path: str) -> List[str]:
        """從檔案路徑辨識，回傳牌名列表"""
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"無法讀取圖片：{image_path}")
        return self.recognize(img)

    def recognize(self, img: np.ndarray,
                  save_debug: Optional[str] = None) -> List[str]:
        """
        從 numpy 圖像辨識，回傳牌名列表。
        save_debug: 若提供路徑，將標注後圖片存檔供除錯。
        """
        detections = self.detector.detect(img)
        if not detections:
            log.warning("未偵測到任何麻將牌")
            return []

        rois = [det[0] for det in detections]
        predictions = self.classifier.predict_batch(rois)

        tile_names = []
        labels_for_vis = []
        for (name, conf) in predictions:
            if conf >= self.CONFIDENCE_THRESHOLD:
                tile_names.append(name)
                labels_for_vis.append(f"{name}({conf:.2f})")
            else:
                tile_names.append("?")
                labels_for_vis.append(f"?({conf:.2f})")
            log.debug("預測: %s  信心: %.3f", name, conf)

        if save_debug:
            vis = self.detector.visualize(img, detections, labels_for_vis)
            cv2.imwrite(save_debug, vis)
            log.info("除錯圖已存至 %s", save_debug)

        return tile_names


# ─── 快速辨識入口 ─────────────────────────────────────────────────────────────

def recognize_from_image(image_path: str,
                         templates_dir: Optional[str] = None,
                         model_path: Optional[str] = None,
                         save_debug: Optional[str] = None) -> List[str]:
    """
    便利函式：傳入圖片路徑，回傳辨識出的牌名列表。

    若提供 model_path 優先使用 CNN 模式，否則使用 template 模式。
    """
    if model_path and os.path.exists(model_path):
        rec = MahjongRecognizer("cnn", model_path=model_path)
    elif templates_dir and os.path.isdir(templates_dir):
        rec = MahjongRecognizer("template", templates_dir=templates_dir)
    else:
        raise FileNotFoundError(
            "請提供 templates_dir（範本資料夾）或 model_path（CNN 模型）其中之一"
        )

    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"無法讀取圖片：{image_path}")

    return rec.recognize(img, save_debug=save_debug)
