#!/usr/bin/env python3
# 计算enemy1坐标

# 敌人1的绝对坐标（門先生之前给的）
enemy1_x1, enemy1_y1 = 1547, 1043
enemy1_x2, enemy1_y2 = 1708, 1095

# 窗口偏移
window_x = 304
window_y = 176

# 计算相对坐标
rel_x = enemy1_x1 - window_x
rel_y = enemy1_y1 - window_y
rel_w = enemy1_x2 - enemy1_x1
rel_h = enemy1_y2 - enemy1_y1

print(f'enemy1_hp: x={rel_x}, y={rel_y}, w={rel_w}, h={rel_h}')
print()
print(f'对比enemy2: x=1496, y=864, w=240, h=147')
print(f'对比enemy3: x=1786, y=864, w=228, h=147')
