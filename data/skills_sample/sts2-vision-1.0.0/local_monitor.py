#!/usr/bin/env python3
"""
杀戮尖塔2 本地监控系统
完全本地运行，不消耗任何Token
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


class LocalMonitor:
    """纯本地监控系统 - 零Token消耗"""
    
    def __init__(self):
        self.capture = STS2Capture()
        self.history = deque(maxlen=2000)  # 血量历史
        self.damage_events = []  # 伤害事件
        self.enemy_max_hp = {}  # 敌人最大HP
        self.running = False
        self.battle_start_time = None
        self.total_damage = 0
        
    def start(self) -> bool:
        """启动"""
        print("=" * 50)
        print("杀戮尖塔2 本地监控系统")
        print("=" * 50)
        
        window = self.capture.find_window()
        if not window:
            print("未找到游戏窗口")
            return False
        
        print(f"窗口: {window['title']}")
        print(f"大小: {window['width']} x {window['height']}")
        print("状态: 纯本地运行，零Token消耗")
        
        self.running = True
        self.battle_start_time = time.time()
        return True
    
    def detect_enemy_count(self, rois: dict) -> int:
        """检测敌人数量"""
        enemy_hp = rois.get("enemy_hp")
        enemy1_hp = rois.get("enemy1_hp")
        enemy2_hp = rois.get("enemy2_hp")
        enemy3_hp = rois.get("enemy3_hp")
        
        count = 0
        if enemy_hp is not None and enemy_hp.size > 100:
            count = 1
        elif enemy1_hp is not None and enemy1_hp.size > 100:
            count = 1
            # 检查多个敌人
            if enemy2_hp is not None and enemy2_hp.size > 100:
                count = 2
            if enemy3_hp is not None and enemy3_hp.size > 100:
                count = 3
        
        return count
    
    def extract_hp_value(self, roi_img) -> tuple:
        """提取HP数值 - 返回 (当前HP, 最大HP)"""
        if roi_img is None or roi_img.size < 50:
            return (None, None)
        
        try:
            # 转为灰度
            if len(roi_img.shape) == 3:
                gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
            else:
                gray = roi_img
            
            # 高斯模糊
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # 自适应阈值
            thresh = cv2.adaptiveThreshold(blurred, 255, 
                                          cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                          cv2.THRESH_BINARY_INV, 15, 2)
            
            # 查找轮廓
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # 按x坐标排序
            contours = sorted(contours, key=lambda c: cv2.boundingRect(c)[0])
            
            # 提取数字区域
            numbers = []
            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                if w > 3 and h > 5:  # 过滤噪声
                    numbers.append((x, y, w, h))
            
            return (len(numbers) * 10, None)  # 简化估算
            
        except:
            return (None, None)
    
    def process_frame(self):
        """处理帧"""
        rois = self.capture.get_all_roi()
        if not rois:
            return None
        
        timestamp = time.time()
        
        # 检测敌人数量
        enemy_count = self.detect_enemy_count(rois)
        
        # 提取玩家HP
        player_hp_roi = rois.get("player1_hp_bottom")
        player_hp, player_max = self.extract_hp_value(player_hp_roi)
        
        # 提取敌人HP
        enemy_hp = None
        enemy_roi = rois.get("enemy_hp")
        if enemy_roi is not None and enemy_roi.size > 100:
            enemy_hp, enemy_max = self.extract_hp_value(enemy_roi)
            if enemy_max and 1 not in self.enemy_max_hp:
                self.enemy_max_hp[1] = enemy_max
        
        # 记录
        self.history.append({
            "time": timestamp,
            "player_hp": player_hp,
            "enemy_hp": enemy_hp,
            "enemy_count": enemy_count
        })
        
        # 计算伤害
        if len(self.history) >= 2:
            prev = self.history[-2]
            curr = self.history[-1]
            
            if prev.get("enemy_hp") and curr.get("enemy_hp"):
                prev_hp = prev["enemy_hp"]
                curr_hp = curr["enemy_hp"]
                
                if prev_hp > curr_hp:
                    damage = prev_hp - curr_hp
                    self.total_damage += damage
                    self.damage_events.append({
                        "time": timestamp,
                        "damage": damage,
                        "enemy_hp": curr_hp
                    })
        
        return {
            "player_hp": player_hp,
            "enemy_hp": enemy_hp,
            "enemy_count": enemy_count,
            "total_damage": self.total_damage
        }
    
    def get_stats(self) -> dict:
        """获取统计"""
        duration = 0
        if self.battle_start_time:
            duration = time.time() - self.battle_start_time
        
        return {
            "duration": duration,
            "total_damage": self.total_damage,
            "dps": self.total_damage / duration if duration > 0 else 0,
            "events": len(self.damage_events)
        }
    
    def save_report(self):
        """保存报告"""
        stats = self.get_stats()
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": stats["duration"],
            "total_damage": stats["total_damage"],
            "dps": stats["dps"],
            "damage_events": len(self.damage_events),
            "damage_details": self.damage_events[-20:]  # 最近20次
        }
        
        filename = f"local_report_{int(time.time())}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return filename
    
    def run(self):
        """运行"""
        if not self.start():
            return
        
        print("\n开始监控... 按Ctrl+C停止\n")
        print("状态: 零Token消耗 | 纯本地处理\n")
        
        last_report = time.time()
        
        try:
            while self.running:
                result = self.process_frame()
                
                if time.time() - last_report >= 5:
                    stats = self.get_stats()
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                          f"伤害: {stats['total_damage']} | "
                          f"DPS: {stats['dps']:.1f} | "
                          f"时长: {stats['duration']:.0f}s")
                    last_report = time.time()
                
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("\n停止")
            self.stop()
    
    def stop(self):
        """停止"""
        self.running = False
        
        # 保存报告
        filename = self.save_report()
        
        stats = self.get_stats()
        
        print("\n" + "=" * 50)
        print("战斗统计报告")
        print("=" * 50)
        print(f"战斗时长: {stats['duration']:.1f}秒")
        print(f"总伤害: {stats['total_damage']}")
        print(f"DPS: {stats['dps']:.1f}")
        print(f"伤害次数: {len(self.damage_events)}")
        print(f"报告已保存: {filename}")
        
        self.capture.release()


if __name__ == "__main__":
    monitor = LocalMonitor()
    monitor.run()
