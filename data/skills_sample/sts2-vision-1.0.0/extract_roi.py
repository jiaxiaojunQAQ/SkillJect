#!/usr/bin/env python3
import cv2

img = cv2.imread('game_capture.png')

# 提取关键区域
regions = {
    'hp_text': (120, 65, 100, 25),
    'gold': (280, 40, 80, 30),
    'floor': (550, 40, 60, 30),
    'deck_count': (720, 40, 80, 30),
    'energy': (220, 65, 40, 30)
}

for name, (x, y, w, h) in regions.items():
    roi = img[y:y+h, x:x+w]
    cv2.imwrite(f'roi_{name}.png', roi)
    print(f'已保存: roi_{name}.png')
