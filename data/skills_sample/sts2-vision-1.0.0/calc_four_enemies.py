# 四位敌人坐标计算

x1, y1 = 1420, 987
x2, y2 = 2405, 1073

window_x = 304
window_y = 176

# 相对坐标
rel_x = x1 - window_x
rel_y = y1 - window_y
rel_w = x2 - x1
rel_h = y2 - y1

print(f'四位敌人血条区域:')
print(f'enemies_hp: x={rel_x}, y={rel_y}, w={rel_w}, h={rel_h}')
