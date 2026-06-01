#!/usr/bin/env python3
from smart_capture import STS2Capture

s = STS2Capture()
w = s.find_window()
if w:
    print(f"窗口: {w['title']}")
    print(f"位置: {w['x']}, {w['y']}")
    print(f"大小: {w['width']} x {w['height']}")
    
    # 捕获
    img = s.capture()
    if img is not None:
        print(f"捕获成功: {img.shape}")
else:
    print("未找到窗口")

s.release()
