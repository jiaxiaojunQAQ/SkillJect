from smart_capture import STS2Capture
import cv2
import numpy as np

s = STS2Capture()
s.find_window()

# 捕获整个区域
img = s.capture()

if img is not None:
    # 保存大图
    cv2.imwrite("four_enemies_full.png", img)
    print(f"已保存大图: {img.shape}")
    
    # 显示敌人区域 (y=800-1000)
    enemy_area = img[800:1000, 1000:2200]
    cv2.imwrite("four_enemies_area.png", enemy_area)
    print(f"敌人区域: {enemy_area.shape}")

s.release()
