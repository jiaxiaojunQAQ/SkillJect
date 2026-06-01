#!/usr/bin/env python3
# 单个敌人坐标计算

# 绝对坐标
enemy_x1, enemy_y1 = 1730, 1043
enemy_x2, enemy_y2 = 2082, 1187

# 窗口偏移
window_x = 304
window_y = 176

# 计算相对坐标
rel_x = enemy_x1 - window_x
rel_y = enemy_y1 - window_y
rel_w = enemy_x2 - enemy_x1
rel_h = enemy_y2 - enemy_y1

print(f'单个敌人血量区域:')
print(f'enemy_hp: x={rel_x}, y={rel_y}, w={rel_w}, h={rel_h}')
print()

# 方案建议
print('=== 节省Token方案 ===')
print('1. 完全本地运行 - 不调用任何AI API')
print('   - 纯Python + OpenCV处理')
print('   - 血量变化在本地计算')
print('   - 只在需要分析时调用DeepSeek')
print()
print('2. 定期批量处理 - 减少API调用频率')
print('   - 每分钟采集数据存入本地JSON')
print('   - 战斗结束后一次性分析')
print()
print('3. 阈值触发 - 仅异常时通知')
print('   - 正常掉血不调用API')
print('   - 出现未知状态/异常时再调用')
