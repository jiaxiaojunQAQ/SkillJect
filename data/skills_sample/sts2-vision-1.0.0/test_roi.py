#!/usr/bin/env python3
import cv2
import numpy as np

def preprocess_for_ocr(image):
    """图像预处理"""
    if image is None:
        return None
    
    # 转为灰度
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # 高斯模糊降噪
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    
    # 自适应阈值
    thresh = cv2.adaptiveThreshold(blurred, 255, 
                                   cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV, 11, 2)
    
    return thresh

def simple_digit_read(image):
    """简单数字识别"""
    if image is None:
        return "N/A"
    
    # 预处理
    processed = preprocess_for_ocr(image)
    
    if processed is None:
        return "N/A"
    
    # 查找轮廓
    contours, _ = cv2.findContours(processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return "N/A"
    
    # 获取数字区域
    digits = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w > 3 and h > 5:  # 过滤噪声
            digits.append((x, w * h))
    
    # 按位置排序
    digits.sort()
    
    # 简单返回数字个数（实际需要更复杂的识别）
    return f"{len(digits)} objects"

# 测试各个ROI
rois = ['hp_text', 'gold', 'floor', 'deck_count', 'energy']

print("=" * 50)
print("ROI区域识别测试")
print("=" * 50)

for name in rois:
    img = cv2.imread(f'roi_{name}.png')
    result = simple_digit_read(img)
    print(f"{name}: {result}")
