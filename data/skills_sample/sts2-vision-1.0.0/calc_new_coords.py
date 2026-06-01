#!/usr/bin/env python3
# 计算新的相对坐标

window_x = 304
window_y = 176

# 門先生提供的新坐标
# 格式: (x1,y1), (x2,y2), (x3,y3), (x4,y4)
regions = {
    "discard_pile_new": [(2354, 1126), (2400, 1126), (2354, 1168), (2400, 1168)],
    "player1_hp_bottom": [(685, 1043), (976, 1043), (685, 1095), (976, 1095)],
    "enemy2_hp": [(1800, 1040), (2040, 1040), (1800, 1187), (2040, 1187)],
    "enemy3_hp": [(2090, 1040), (2318, 1040), (2090, 1187), (2318, 1187)],
}

print("更新后的相对坐标:")
print()

for name, coords in regions.items():
    # 计算边界
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    
    x = min(xs) - window_x
    y = min(ys) - window_y
    w = max(xs) - min(xs)
    h = max(ys) - min(ys)
    
    print(f'"{name}": {{"x": {x}, "y": {y}, "w": {w}, "h": {h}}},')
