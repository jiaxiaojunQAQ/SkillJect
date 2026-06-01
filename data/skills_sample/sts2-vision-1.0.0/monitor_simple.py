#!/usr/bin/env python3
"""
杀戮尖塔2 简化监控系统
只捕获屏幕，不依赖鼠标监听
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


class STS2SimpleMonitor:
    """简化监控系统"""
    
    def __init__(self):
        self.capture = STS2Capture()
        self.history = deque(maxlen=1000)
        self.damage_events = deque(maxlen=500)
        self.player1_hp = 0
        self.player1_max_hp = 0
        self.player1_block = 0
        self.enemy_hp = {}
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
        
        self.running = True
        return True
    
    def process_frame(self):
        """处理帧"""
        rois = self.capture.get_all_roi()
        if not rois:
            return
        
        timestamp = time.time()
        
        # 提取各区域
        player1_hp_roi = rois.get("player1_hp_bottom")
        enemy1_hp_roi = rois.get("enemy1_hp")
        
        # 简化的血量检测（使用白色像素数量估算）
        player1_hp = self._estimate_hp(player1_hp_roi)
        enemy1_hp = self._estimate_hp(enemy1_hp_roi)
        
        # 记录敌人伤害
        if enemy1_hp is not None:
            old_enemy_hp = self.enemy_hp.get(1, 0)
            if old_enemy_hp > 0 and enemy1_hp < old_enemy_hp:
                damage = old_enemy_hp - enemy1_hp
                self.damage_events.append({
                    "time": timestamp,
                    "target": "enemy1",
                    "damage": damage,
                    "hp": enemy1_hp
                })
            self.enemy_hp[1] = enemy1_hp
        
        # 记录历史
        self.history.append({
            "time": timestamp,
            "player1_hp": player1_hp,
            "enemy1_hp": enemy1_hp
        })
        
        return {"player1_hp": player1_hp, "enemy1_hp": enemy1_hp}
    
    def _estimate_hp(self, roi_img) -> int:
        """估算HP（简化版）"""
        if roi_img is None or roi_img.size == 0:
            return None
        
        try:
            # 转为灰度
            if len(roi_img.shape) == 3:
                gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
            else:
                gray = roi_img
            
            # 高斯模糊
            blurred = cv2.GaussianBlur(gray, (3, 3), 0)
            
            # 自适应阈值
            thresh = cv2.adaptiveThreshold(blurred, 255, 
                                          cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                          cv2.THRESH_BINARY_INV, 11, 2)
            
            # 白色像素数量（估算数字存在）
            white_pixels = cv2.countNonZero(thresh)
            
            # 简单估算（需要校准）
            if white_pixels > 500:
                return white_pixels // 50  # 估算值
            
            return None
            
        except Exception as e:
            return None
    
    def get_stats(self) -> dict:
        """获取统计"""
        total_damage = sum(e["damage"] for e in self.damage_events if e["target"].startswith("enemy"))
        
        duration = 0
        if self.history:
            duration = self.history[-1]["time"] - self.history[0]["time"]
        
        dps = total_damage / duration if duration > 0 else 0
        
        return {
            "damage_dealt": total_damage,
            "dps": dps,
            "duration": duration,
            "enemy_hp": self.enemy_hp.get(1, "N/A")
        }
    
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
                    stats = self.get_stats()
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                          f"伤害: {stats['damage_dealt']} | "
                          f"DPS: {stats['dps']:.1f} | "
                          f"敌人HP: {stats['enemy_hp']}")
                    last_report = time.time()
                
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("\n停止")
            self.stop()
    
    def stop(self):
        """停止"""
        self.running = False
        
        stats = self.get_stats()
        
        print("\n" + "=" * 50)
        print("战斗统计")
        print("=" * 50)
        print(f"时长: {stats['duration']:.1f}秒")
        print(f"造成伤害: {stats['damage_dealt']}")
        print(f"DPS: {stats['dps']:.1f}")
        
        # 保存报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "statistics": stats,
            "damage_events": list(self.damage_events)
        }
        
        filename = f"sts2_report_{int(time.time())}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"报告已保存: {filename}")
        
        self.capture.release()


if __name__ == "__main__":
    monitor = STS2SimpleMonitor()
    monitor.run()
