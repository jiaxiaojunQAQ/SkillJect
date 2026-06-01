#!/usr/bin/env python3
"""
杀戮尖塔2 血量监控 + 鼠标监听
阶段1：基础血量监控
阶段2：鼠标监听 + 伤害判断
"""

import os
import sys
import time
import json
import threading
import cv2
import numpy as np
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional

# 导入捕获模块
from smart_capture import STS2Capture

# 鼠标监听
from pynput import mouse


class MouseListener:
    """鼠标事件监听器"""
    
    def __init__(self):
        self.clicks = deque(maxlen=100)
        self.last_click_time = 0
        
    def on_click(self, x, y, button, pressed):
        """点击事件"""
        if pressed:  # 只记录按下
            click_info = {
                "time": time.time(),
                "x": x,
                "y": y,
                "button": str(button)
            }
            self.clicks.append(click_info)
            self.last_click_time = click_info["time"]
    
    def start(self):
        """启动监听"""
        self.listener = mouse.Listener(on_click=self.on_click)
        self.listener.daemon = True
        self.listener.start()
        print("鼠标监听已启动")
    
    def stop(self):
        """停止监听"""
        if hasattr(self, 'listener'):
            self.listener.stop()
    
    def get_recent_clicks(self, seconds: int = 5) -> List[Dict]:
        """获取最近的点击"""
        current_time = time.time()
        return [c for c in self.clicks if current_time - c["time"] <= seconds]


class HPTracker:
    """血量追踪器"""
    
    def __init__(self):
        self.history = deque(maxlen=1000)
        self.damage_events = deque(maxlen=500)
        self.player1_hp = 0
        self.player1_max_hp = 0
        self.enemy_hp = {}
        
    def update(self, player1_hp: int = None, player1_max_hp: int = None,
               enemy1_hp: int = None, enemy2_hp: int = None, enemy3_hp: int = None):
        """更新血量"""
        timestamp = time.time()
        
        # 玩家1血量
        if player1_hp is not None:
            old_hp = self.player1_hp
            self.player1_hp = player1_hp
            
            if old_hp > 0 and player1_hp < old_hp:
                damage = old_hp - player1_hp
                self.damage_events.append({
                    "time": timestamp,
                    "target": "player1",
                    "damage": damage,
                    "hp_after": player1_hp
                })
            
            if player1_max_hp:
                self.player1_max_hp = player1_max_hp
        
        # 敌人血量
        if enemy1_hp is not None:
            self._update_enemy_hp(1, enemy1_hp, timestamp)
        if enemy2_hp is not None:
            self._update_enemy_hp(2, enemy2_hp, timestamp)
        if enemy3_hp is not None:
            self._update_enemy_hp(3, enemy3_hp, timestamp)
        
        # 记录历史
        self.history.append({
            "time": timestamp,
            "player1_hp": self.player1_hp,
            "player1_max_hp": self.player1_max_hp,
            "enemy_hp": dict(self.enemy_hp)
        })
    
    def _update_enemy_hp(self, enemy_id: int, hp: int, timestamp: float):
        """更新敌人血量"""
        old_hp = self.enemy_hp.get(enemy_id, 0)
        self.enemy_hp[enemy_id] = hp
        
        if old_hp > 0 and hp < old_hp:
            damage = old_hp - hp
            self.damage_events.append({
                "time": timestamp,
                "target": f"enemy{enemy_id}",
                "damage": damage,
                "hp_after": hp
            })
    
    def get_total_damage_dealt(self) -> int:
        """对敌人造成的总伤害"""
        return sum(e["damage"] for e in self.damage_events if e["target"].startswith("enemy"))
    
    def get_total_damage_taken(self) -> int:
        """受到的总伤害"""
        return sum(e["damage"] for e in self.damage_events if e["target"] == "player1")
    
    def get_statistics(self) -> Dict:
        """统计信息"""
        duration = 0
        if self.history:
            duration = self.history[-1]["time"] - self.history[0]["time"]
        
        dps = 0
        if duration > 0:
            dps = self.get_total_damage_dealt() / duration
        
        return {
            "duration": duration,
            "damage_dealt": self.get_total_damage_dealt(),
            "damage_taken": self.get_total_damage_taken(),
            "dps": dps,
            "player1_hp": f"{self.player1_hp}/{self.player1_max_hp}" if self.player1_max_hp else "N/A",
            "enemy_count": len(self.enemy_hp)
        }


class STS2Monitor:
    """监控系统"""
    
    def __init__(self):
        self.capture = STS2Capture()
        self.mouse = MouseListener()
        self.tracker = HPTracker()
        self.running = False
        
    def start(self) -> bool:
        """启动"""
        print("=" * 50)
        print("杀戮尖塔2 监控系统")
        print("=" * 50)
        
        window = self.capture.find_window()
        if not window:
            print("未找到游戏窗口")
            return False
        
        print(f"窗口: {window['title']}")
        print(f"大小: {window['width']} x {window['height']}")
        
        # 启动鼠标监听
        try:
            self.mouse.start()
        except Exception as e:
            print(f"鼠标监听失败: {e}")
        
        self.running = True
        return True
    
    def process_frame(self):
        """处理帧"""
        rois = self.capture.get_all_roi()
        if not rois:
            return None
        
        # 提取血量（简化版）
        player1_hp = self._extract_hp(rois.get("player1_hp_bottom"))
        enemy1_hp = self._extract_hp(rois.get("enemy1_hp"))
        
        self.tracker.update(player1_hp=player1_hp, enemy1_hp=enemy1_hp)
        
        return {"player1_hp": player1_hp, "enemy1_hp": enemy1_hp}
    
    def _extract_hp(self, roi_img) -> Optional[int]:
        """提取HP数值"""
        if roi_img is None or roi_img.size == 0:
            return None
        
        try:
            gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY) if len(roi_img.shape) == 3 else roi_img
            _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            return len(contours)
        except:
            return None
    
    def run(self):
        """运行"""
        if not self.start():
            return
        
        print("\n开始监控... 按Ctrl+C停止\n")
        
        last_report = time.time()
        
        try:
            while self.running:
                self.process_frame()
                
                if time.time() - last_report >= 5:
                    stats = self.tracker.get_statistics()
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                          f"HP: {stats['player1_hp']} | "
                          f"伤害: {stats['damage_dealt']} | "
                          f"受伤: {stats['damage_taken']} | "
                          f"DPS: {stats['dps']:.1f}")
                    last_report = time.time()
                
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("\n停止监控")
            self.stop()
    
    def stop(self):
        """停止"""
        self.running = False
        self.mouse.stop()
        
        stats = self.tracker.get_statistics()
        
        print("\n" + "=" * 50)
        print("战斗统计")
        print("=" * 50)
        print(f"时长: {stats['duration']:.1f}秒")
        print(f"造成伤害: {stats['damage_dealt']}")
        print(f"受到伤害: {stats['damage_taken']}")
        print(f"DPS: {stats['dps']:.1f}")
        
        # 保存报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "statistics": stats,
            "damage_events": list(self.tracker.damage_events)
        }
        
        filename = f"sts2_report_{int(time.time())}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n报告已保存: {filename}")
        self.capture.release()


if __name__ == "__main__":
    monitor = STS2Monitor()
    monitor.run()
