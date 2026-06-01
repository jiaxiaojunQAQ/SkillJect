#!/usr/bin/env python3
"""
杀戮尖塔2 联机监控系统
区分門先生和队友的伤害
"""

import os
import sys
import time
import json
import cv2
import numpy as np
from collections import deque
from datetime import datetime
from smart_capture import STS2Capture

# 鼠标监听
from pynput import mouse


class OnlineMonitor:
    """联机监控系统 - 带鼠标事件"""
    
    def __init__(self):
        self.capture = STS2Capture()
        
        # 鼠标事件
        self.clicks = deque(maxlen=200)
        self.my_clicks = deque(maxlen=100)  # 門先生的点击
        self.partner_clicks = deque(maxlen=100)  # 队友点击
        
        # 血量历史
        self.history = deque(maxlen=2000)
        
        # 伤害记录
        self.my_damage = 0  # 門先生伤害
        self.partner_damage = 0  # 队友伤害
        self.damage_events = []
        
        # 敌人最大HP
        self.enemy_max_hp = {}
        
        # 窗口区域
        self.window_rect = None
        
        self.running = False
        
    def start(self) -> bool:
        """启动"""
        print("=" * 50)
        print("杀戮尖塔2 联机监控系统")
        print("=" * 50)
        
        window = self.capture.find_window()
        if not window:
            print("未找到游戏窗口")
            return False
        
        self.window_rect = {
            "x": window["x"],
            "y": window["y"],
            "w": window["width"],
            "h": window["height"]
        }
        
        print(f"窗口: {window['title']}")
        print(f"区域: ({window['x']}, {window['y']}) - {window['width']}x{window['height']}")
        
        # 启动鼠标监听
        self._start_mouse_listener()
        
        self.running = True
        return True
    
    def _start_mouse_listener(self):
        """启动鼠标监听"""
        def on_click(x, y, button, pressed):
            if not pressed:
                return
            
            click_time = time.time()
            
            # 判断点击是否在游戏窗口内
            if self.window_rect:
                wx, wy = self.window_rect["x"], self.window_rect["y"]
                ww, wh = self.window_rect["w"], self.window_rect["h"]
                
                # 在窗口内
                if wx <= x <= wx + ww and wy <= y <= wy + wh:
                    # 判断是門先生还是队友
                    # 門先生在左侧区域，队友在右侧
                    # 左侧1/3为門先生区域
                    rel_x = x - wx
                    
                    if rel_x < ww / 3:
                        # 左侧 - 門先生
                        self.my_clicks.append({
                            "time": click_time,
                            "x": x,
                            "y": y,
                            "rel_x": rel_x
                        })
                    else:
                        # 右侧 - 队友
                        self.partner_clicks.append({
                            "time": click_time,
                            "x": x,
                            "y": y,
                            "rel_x": rel_x
                        })
                    
                    # 记录所有点击
                    self.clicks.append({
                        "time": click_time,
                        "x": x,
                        "y": y,
                        "is_mine": rel_x < ww / 3
                    })
        
        self.mouse_listener = mouse.Listener(on_click=on_click)
        self.mouse_listener.daemon = True
        self.mouse_listener.start()
        print("鼠标监听已启动")
        print("  - 左侧1/3区域 = 門先生")
        print("  - 右侧2/3区域 = 队友")
    
    def extract_hp(self, roi_img):
        """提取HP（简化版）"""
        if roi_img is None or roi_img.size < 50:
            return None
        
        try:
            if len(roi_img.shape) == 3:
                gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
            else:
                gray = roi_img
            
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            thresh = cv2.adaptiveThreshold(blurred, 255, 
                                          cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                          cv2.THRESH_BINARY_INV, 15, 2)
            
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # 估算HP
            return len([c for c in contours if cv2.boundingRect(c)[2] > 3])
            
        except:
            return None
    
    def process_frame(self):
        """处理帧"""
        rois = self.capture.get_all_roi()
        if not rois:
            return None
        
        timestamp = time.time()
        
        # 提取敌人血量
        enemy1_hp = self.extract_hp(rois.get("enemy1_hp"))
        enemy2_hp = self.extract_hp(rois.get("enemy2_hp"))
        enemy3_hp = self.extract_hp(rois.get("enemy3_hp"))
        
        # 记录历史
        self.history.append({
            "time": timestamp,
            "enemy1_hp": enemy1_hp,
            "enemy2_hp": enemy2_hp,
            "enemy3_hp": enemy3_hp,
            "my_clicks_recent": len([c for c in self.my_clicks if timestamp - c["time"] < 3]),
            "partner_clicks_recent": len([c for c in self.partner_clicks if timestamp - c["time"] < 3])
        })
        
        # 计算伤害
        if len(self.history) >= 2:
            prev = self.history[-2]
            curr = self.history[-1]
            
            # 检查每个敌人的血量变化
            for i, hp_key in enumerate(["enemy1_hp", "enemy2_hp", "enemy3_hp"], 1):
                prev_hp = prev.get(hp_key)
                curr_hp = curr.get(hp_key)
                
                if prev_hp and curr_hp and prev_hp > curr_hp:
                    damage = prev_hp - curr_hp
                    
                    # 判断是谁造成的伤害
                    # 检查最近3秒内的点击
                    recent_my = len([c for c in self.my_clicks if timestamp - c["time"] < 3])
                    recent_partner = len([c for c in self.partner_clicks if timestamp - c["time"] < 3])
                    
                    if recent_my > recent_partner:
                        self.my_damage += damage
                        attacker = "門先生"
                    elif recent_partner > recent_my:
                        self.partner_damage += damage
                        attacker = "队友"
                    else:
                        # 无法判断，归为未知
                        attacker = "未知"
                    
                    self.damage_events.append({
                        "time": timestamp,
                        "enemy": i,
                        "damage": damage,
                        "my_clicks": recent_my,
                        "partner_clicks": recent_partner,
                        "attacker": attacker
                    })
        
        return {
            "my_damage": self.my_damage,
            "partner_damage": self.partner_damage,
            "my_clicks": len(self.my_clicks),
            "partner_clicks": len(self.partner_clicks)
        }
    
    def get_stats(self) -> dict:
        """统计"""
        total = self.my_damage + self.partner_damage
        
        return {
            "my_damage": self.my_damage,
            "partner_damage": self.partner_damage,
            "total_damage": total,
            "my_clicks": len(self.my_clicks),
            "partner_clicks": len(self.partner_clicks),
            "damage_events": len(self.damage_events)
        }
    
    def run(self):
        """运行"""
        if not self.start():
            return
        
        print("\n开始监控...\n")
        
        last_report = time.time()
        
        try:
            while self.running:
                self.process_frame()
                
                if time.time() - last_report >= 5:
                    stats = self.get_stats()
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                          f"我的: {stats['my_damage']} | "
                          f"队友: {stats['partner_damage']} | "
                          f"点击: {stats['my_clicks']}/{stats['partner_clicks']}")
                    last_report = time.time()
                
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("\n停止")
            self.stop()
    
    def stop(self):
        """停止"""
        self.running = False
        
        if hasattr(self, 'mouse_listener'):
            self.mouse_listener.stop()
        
        stats = self.get_stats()
        
        print("\n" + "=" * 50)
        print("战斗统计")
        print("=" * 50)
        print(f"門先生伤害: {stats['my_damage']}")
        print(f"队友伤害: {stats['partner_damage']}")
        print(f"門先生点击: {stats['my_clicks']}")
        print(f"队友点击: {stats['partner_clicks']}")
        
        # 保存报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "my_damage": stats["my_damage"],
            "partner_damage": stats["partner_damage"],
            "my_clicks": stats["my_clicks"],
            "partner_clicks": stats["partner_clicks"],
            "events": self.damage_events[-30:]
        }
        
        filename = f"online_report_{int(time.time())}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n报告: {filename}")
        
        self.capture.release()


if __name__ == "__main__":
    monitor = OnlineMonitor()
    monitor.run()
