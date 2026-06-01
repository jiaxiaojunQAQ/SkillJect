#!/usr/bin/env python3
"""
杀戮尖塔2 相对坐标配置
基于窗口大小 2138x1266，使用时自动适配
"""

# 基础窗口大小（用于计算比例）
BASE_WINDOW_WIDTH = 2138
BASE_WINDOW_HEIGHT = 1266

# 相对坐标配置（基于提供的绝对坐标计算）
RELATIVE_ROI = {
    # ===== 顶部状态栏 =====
    "player_icon": {"x": 36, "y": 71, "w": 77, "h": 67,
                    "description": "玩家头像与难度"},
    
    "player_hp_top": {"x": 144, "y": 71, "w": 159, "h": 67,
                     "description": "顶部玩家血量"},
    
    "gold": {"x": 367, "y": 71, "w": 106, "h": 67,
             "description": "金币数量"},
    
    "floor": {"x": 880, "y": 71, "w": 75, "h": 67,
              "description": "爬塔层数"},
    
    "total_cards": {"x": 1936, "y": 71, "w": 91, "h": 67,
                    "description": "玩家总牌数"},
    
    # ===== 战斗区域 =====
    "energy": {"x": 145, "y": 1000, "w": 86, "h": 82,
              "description": "能量 3/3"},
    
    "player1_hp_bottom": {"x": 381, "y": 867, "w": 291, "h": 52,
                         "description": "玩家1血量(下) + 格挡"},
    
    # ===== 敌人血量（四个敌人模式-待校准）=====
    # "enemies_hp": {"x": 1414, "y": 821, "w": 588, "h": 122,
    #                "description": "四个敌人血量区域-待校准"},
    
    # ===== 敌人血量（三个敌人模式-常用）=====
    "enemy1_hp": {"x": 1243, "y": 864, "w": 161, "h": 147,
                  "description": "怪物1血量 44/44"},
    "enemy2_hp": {"x": 1496, "y": 864, "w": 240, "h": 147,
                  "description": "怪物2血量 65/65"},
    "enemy3_hp": {"x": 1786, "y": 864, "w": 228, "h": 147,
                  "description": "怪物3血量 65/65"},
    
    # ===== 牌堆区域 =====
    "draw_pile": {"x": 69, "y": 1170, "w": 78, "h": 66,
                  "description": "抽牌堆数量"},
    
    "discard_pile": {"x": 2050, "y": 950, "w": 46, "h": 42,
                    "description": "弃牌堆数量"},
    
    # ===== 手牌区域 =====
    "hand_cards": {"x": 288, "y": 979, "w": 1512, "h": 261,
                   "description": "手牌区域"},
    
    # ===== 伤害数字区域 =====
    "damage_numbers": {"x": 1200, "y": 300, "w": 400, "h": 300,
                      "description": "伤害数字弹出区域"},
    
    # ===== 状态图标区域 =====
    "player_buffs": {"x": 50, "y": 350, "w": 100, "h": 150,
                     "description": "玩家增益状态"},
    
    "player_debuffs": {"x": 50, "y": 500, "w": 100, "h": 150,
                      "description": "玩家减益状态"},
    
    "enemy_buffs": {"x": 1950, "y": 350, "w": 100, "h": 150,
                   "description": "敌人增益状态"},
    
    "enemy_debuffs": {"x": 1950, "y": 500, "w": 100, "h": 150,
                     "description": "敌人减益状态"},
}


def get_adaptive_roi(window_width: int, window_height: int) -> dict:
    """
    根据当前窗口大小计算适配的ROI
    按比例自动调整
    """
    scale_x = window_width / BASE_WINDOW_WIDTH
    scale_y = window_height / BASE_WINDOW_HEIGHT
    
    adaptive_roi = {}
    
    for name, roi in RELATIVE_ROI.items():
        adaptive_roi[name] = {
            "x": int(roi["x"] * scale_x),
            "y": int(roi["y"] * scale_y),
            "w": int(roi["w"] * scale_x),
            "h": int(roi["h"] * scale_y),
            "description": roi.get("description", "")
        }
    
    return adaptive_roi


def print_config():
    """打印配置"""
    print("=" * 60)
    print("杀戮尖塔2 ROI相对坐标配置")
    print("=" * 60)
    print(f"基础窗口: {BASE_WINDOW_WIDTH} x {BASE_WINDOW_HEIGHT}")
    print()
    
    for name, roi in RELATIVE_ROI.items():
        print(f'{name}: x={roi["x"]}, y={roi["y"]}, w={roi["w"]}, h={roi["h"]}')


if __name__ == "__main__":
    print_config()
    
    # 测试适配
    print("\n" + "=" * 60)
    print("窗口适配测试 (2138 x 1266)")
    print("=" * 60)
    
    adaptive = get_adaptive_roi(2138, 1266)
    for name, roi in adaptive.items():
        print(f'{name}: x={roi["x"]}, y={roi["y"]}, w={roi["w"]}, h={roi["h"]}')
