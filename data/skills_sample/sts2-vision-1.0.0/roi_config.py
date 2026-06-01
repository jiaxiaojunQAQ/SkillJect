#!/usr/bin/env python3
"""
杀戮尖塔2 ROI区域配置
基于門先生提供的详细UI布局
"""

# 窗口大小: 2138 x 1266
# 横向分为3块: 左(0-712), 中(712-1424), 右(1424-2138)
# 纵向分为3块: 上(0-422), 中(422-844), 下(844-1266)

# ===== 顶部状态栏 =====
ROI_CONFIG = {
    # 顶部从左到右:
    "player_icon": {
        "x": 50, "y": 30, "w": 60, "h": 60,
        "description": "人物头像与难度"
    },
    "relics": {
        "x": 50, "y": 95, "w": 200, "h": 30,
        "description": "已获得的遗物"
    },
    "hp_text_top": {
        "x": 120, "y": 35, "w": 100, "h": 25,
        "description": "顶部血量 50/70"
    },
    "gold": {
        "x": 280, "y": 40, "w": 80, "h": 30,
        "description": "金币"
    },
    "potions": {
        "x": 370, "y": 35, "w": 120, "h": 35,
        "description": "药水栏"
    },
    "event": {
        "x": 500, "y": 40, "w": 40, "h": 40,
        "description": "事件问号"
    },
    "floor": {
        "x": 550, "y": 40, "w": 60, "h": 30,
        "description": "已爬楼层"
    },
    "boss_icon": {
        "x": 620, "y": 35, "w": 40, "h": 40,
        "description": "Boss图标"
    },
    "map": {
        "x": 670, "y": 40, "w": 40, "h": 40,
        "description": "地图"
    },
    "deck_count_top": {
        "x": 720, "y": 40, "w": 80, "h": 30,
        "description": "牌组数量"
    },
    "settings": {
        "x": 2050, "y": 35, "w": 50, "h": 50,
        "description": "设置按钮"
    },
    
    # ===== 战斗区域 (上1/3, 纵向范围约0-422) =====
    # 横向3等分: 0-712, 712-1424, 1424-2138
    
    # 左边玩家区域 (约 50-400)
    "player_hp_bar": {
        "x": 100, "y": 250, "w": 150, "h": 20,
        "description": "玩家血量条"
    },
    "player_hp_text": {
        "x": 100, "y": 275, "w": 100, "h": 25,
        "description": "玩家血量 50/70"
    },
    "player_block": {
        "x": 100, "y": 305, "w": 80, "h": 20,
        "description": "玩家护盾"
    },
    
    # 右边怪物区域 (约 1438-2000)
    "enemy1_hp_text": {
        "x": 1600, "y": 250, "w": 80, "h": 20,
        "description": "怪物1血量 9/9"
    },
    "enemy1_intent": {
        "x": 1600, "y": 200, "w": 60, "h": 40,
        "description": "怪物1意图 4"
    },
    "enemy2_hp_text": {
        "x": 1750, "y": 250, "w": 80, "h": 20,
        "description": "怪物2血量 26/26"
    },
    "enemy3_hp_text": {
        "x": 1900, "y": 250, "w": 80, "h": 20,
        "description": "怪物3血量 14/14"
    },
    
    # 伤害数字区域 (从怪物身体往上跳)
    "damage_numbers": {
        "x": 1500, "y": 150, "w": 300, "h": 150,
        "description": "伤害数字弹出区域"
    },
    
    # ===== 玩家区域 (下1/3, 纵向范围约844-1266) =====
    
    # 抽牌堆 (最左下)
    "draw_pile": {
        "x": 50, "y": 900, "w": 100, "h": 80,
        "description": "抽牌堆数量 6"
    },
    
    # 能量 (靠右上)
    "energy": {
        "x": 1900, "y": 850, "w": 80, "h": 40,
        "description": "能量 3/3"
    },
    
    # 手牌区域
    "hand_cards": {
        "x": 300, "y": 950, "w": 1500, "h": 200,
        "description": "7张手牌"
    },
    
    # 结束回合按钮
    "end_turn": {
        "x": 1950, "y": 1100, "w": 100, "h": 50,
        "description": "结束第一回合按钮"
    },
    
    # 弃牌堆 (最右下)
    "discard_pile": {
        "x": 1950, "y": 1150, "w": 100, "h": 80,
        "description": "弃牌堆数量 0"
    },
}

def print_roi_config():
    """打印ROI配置"""
    print("=" * 60)
    print("杀戮尖塔2 ROI配置")
    print("=" * 60)
    
    for name, roi in ROI_CONFIG.items():
        print(f"\n{name}:")
        print(f"  位置: ({roi['x']}, {roi['y']})")
        print(f"  大小: {roi['w']} x {roi['h']}")
        print(f"  说明: {roi['description']}")

if __name__ == "__main__":
    print_roi_config()
