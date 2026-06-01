#!/usr/bin/env python3
"""提取战斗区域的ROI"""
import cv2

img = cv2.imread('game_capture.png')

# 根据新的布局提取关键区域
regions = {
    # 顶部
    'player_hp': (120, 35, 100, 25),
    'player_hp2': (100, 275, 100, 25),
    
    # 怪物血量
    'enemy1_hp': (1600, 250, 80, 20),
    'enemy2_hp': (1750, 250, 80, 20),
    'enemy3_hp': (1900, 250, 80, 20),
    
    # 能量
    'energy': (1900, 850, 80, 40),
    
    # 抽牌堆
    'draw_pile': (50, 900, 100, 80),
    
    # 弃牌堆
    'discard_pile': (1950, 1150, 100, 80),
    
    # 伤害数字区域
    'damage': (1500, 150, 300, 150),
}

for name, (x, y, w, h) in regions.items():
    roi = img[y:y+h, x:x+w]
    cv2.imwrite(f'fight_{name}.png', roi)
    print(f"已保存: fight_{name}.png")
