x1, y1 = 1718, 997
x2, y2 = 2306, 1119
wx, wy = 304, 176

rel_x = x1 - wx
rel_y = y1 - wy
rel_w = x2 - x1
rel_h = y2 - y1

print(f'enemies_hp: x={rel_x}, y={rel_y}, w={rel_w}, h={rel_h}')
