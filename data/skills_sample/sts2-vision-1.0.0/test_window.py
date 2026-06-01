#!/usr/bin/env python3
from screen_capture import ScreenCapture

s = ScreenCapture()
w = s.get_game_window("Slay the Spire 2")
if w:
    print(f"找到窗口: {w['title']}")
    print(f"位置: {w['x']}, {w['y']}")
    print(f"大小: {w['width']} x {w['height']}")
    
    # 捕获一帧
    img = s.capture_window(w)
    if img is not None:
        print(f"捕获成功: {img.shape}")
        s.save_screenshot(img, "game_capture.png")
else:
    print("未找到窗口")

s.release()
