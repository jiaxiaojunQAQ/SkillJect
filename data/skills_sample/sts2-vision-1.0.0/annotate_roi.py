#!/usr/bin/env python3
"""
在截图上标注ROI区域
"""

import cv2
import numpy as np
from screen_capture import ScreenCapture
from roi_config import ROI_CONFIG

def draw_rois(image, rois, color=(0, 255, 0), thickness=2):
    """在图像上绘制ROI区域"""
    for name, roi in rois.items():
        x, y = roi["x"], roi["y"]
        w, h = roi["w"], roi["h"]
        
        # 绘制矩形
        cv2.rectangle(image, (x, y), (x + w, y + h), color, thickness)
        
        # 添加标签
        label = name.replace("_", " ").title()
        cv2.putText(image, label, (x, y - 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    
    return image

def annotate_screenshot():
    """标注截图"""
    # 加载截图
    img = cv2.imread("game_capture.png")
    
    if img is None:
        print("未找到截图，请先运行: python test_window.py")
        return
    
    print(f"原始图像: {img.shape}")
    
    # 绘制ROI
    img_annotated = draw_rois(img.copy(), ROI_CONFIG, (0, 255, 0), 2)
    
    # 保存
    cv2.imwrite("game_with_roi.png", img_annotated)
    print("已保存标注图: game_with_roi.png")

if __name__ == "__main__":
    annotate_screenshot()
