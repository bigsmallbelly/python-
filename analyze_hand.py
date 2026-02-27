#!/usr/bin/env python3
"""
快速手牌辨識工具
用法: python analyze_hand.py <圖片路徑>
"""
import sys
import cv2
import numpy as np

def analyze_hand_image(image_path: str):
    img = cv2.imread(image_path)
    if img is None:
        print(f"無法讀取圖片：{image_path}")
        return

    h, w = img.shape[:2]
    print(f"圖片尺寸: {w}x{h}")

    # 轉灰階
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 自適應二值化
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 11, 2
    )

    # 尋找輪廓
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 篩選可能是牌的矩形
    tiles = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 1000 or area > 300000:
            continue
        x, y, tw, th = cv2.boundingRect(cnt)
        ratio = tw / th if th > 0 else 0
        if 0.5 <= ratio <= 1.8:
            tiles.append((x, y, tw, th))

    # 按位置排序（左→右）
    tiles.sort(key=lambda t: (t[1] // 80, t[0]))

    print(f"\n偵測到 {len(tiles)} 個牌面區域：")
    for i, (x, y, tw, th) in enumerate(tiles):
        print(f"  牌 {i+1:2d}: 位置=({x},{y}) 大小={tw}x{th}")

    # 畫出偵測框並儲存
    vis = img.copy()
    for i, (x, y, tw, th) in enumerate(tiles):
        cv2.rectangle(vis, (x, y), (x+tw, y+th), (0, 255, 0), 2)
        cv2.putText(vis, str(i+1), (x+2, y+20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    out_path = image_path.rsplit('.', 1)[0] + '_detected.jpg'
    cv2.imwrite(out_path, vis)
    print(f"\n偵測結果圖已存至: {out_path}")
    print("\n請根據偵測結果，使用以下指令計算台數：")
    print('python mahjong_score.py --hand "牌1 牌2 ..." --win-tile 胡牌張 [--self-draw]')

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python analyze_hand.py <圖片路徑>")
    else:
        analyze_hand_image(sys.argv[1])
