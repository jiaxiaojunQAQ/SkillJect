#!/usr/bin/env python3
"""
杀戮尖塔2 视觉识别DPS监控器
主程序 - 整合所有模块
"""

import os
import sys
import time
import json
import threading
import argparse
from datetime import datetime

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from screen_capture import ScreenCapture, ROIDetector
from ocr_recognizer import OCRRecognizer
from state_tracker import StateTracker, PlayerState


class STS2VisionMonitor:
    """杀戮尖塔2视觉监控器"""
    
    def __init__(self, config_file: str = None):
        # 模块
        self.capture = None
        self.ocr = None
        self.tracker = StateTracker()
        self.roi_detector = None
        
        # 配置
        self.config = self._load_config(config_file)
        
        # 状态
        self.running = False
        self.window_info = None
        
        # 自动校准
        self.calibration_mode = False
    
    def _load_config(self, config_file: str = None) -> dict:
        """加载配置"""
        default_config = {
            "fps": 2,
            "window_title": "Slay The Spire 2",
            " rois": {
                "player1_hp": {"x": 50, "y": 50, "w": 150, "h": 30},
                "player2_hp": {"x": 50, "y": 90, "w": 150, "h": 30},
                "enemy_hp": {"x": 500, "y": 50, "w": 150, "h": 30},
                "player1_block": {"x": 50, "y": 85, "w": 80, "h": 20},
                "player2_block": {"x": 50, "y": 125, "w": 80, "h": 20}
            },
            "auto_fight_detection": True,
            "save_screenshots": False,
            "screenshot_dir": "screenshots"
        }
        
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        
        return default_config
    
    def initialize(self):
        """初始化"""
        print("=" * 50)
        print("杀戮尖塔2 视觉监控器")
        print("=" * 50)
        
        # 初始化屏幕捕获
        fps = self.config.get("fps", 2)
        self.capture = ScreenCapture(fps=fps)
        
        # 初始化OCR
        self.ocr = OCRRecognizer()
        
        # 初始化ROI
        self.roi_detector = ROIDetector()
        
        # 查找窗口
        window_title = self.config.get("window_title", "Slay The Spire 2")
        self.window_info = self.capture.get_game_window(window_title)
        
        if not self.window_info:
            print("错误: 未找到游戏窗口")
            print(f"请确保游戏 '{window_title}' 正在运行")
            return False
        
        print(f"找到游戏窗口: {self.window_info['title']}")
        print(f"窗口大小: {self.window_info['width']} x {self.window_info['height']}")
        
        # 创建截图目录
        if self.config.get("save_screenshots"):
            os.makedirs(self.config.get("screenshot_dir", "screenshots"), exist_ok=True)
        
        return True
    
    def capture_frame(self):
        """捕获一帧"""
        if not self.window_info:
            return None
        
        img = self.capture.capture_window(self.window_info)
        
        # 保存截图
        if self.config.get("save_screenshots") and img is not None:
            filename = f"{self.config['screenshot_dir']}/frame_{int(time.time())}.png"
            self.capture.save_screenshot(img, filename)
        
        return img
    
    def process_frame(self, img):
        """处理帧"""
        if img is None:
            return
        
        # 识别各个区域
        for roi_name, roi in self.config.get("rois", {}).items():
            roi_img = self.roi_detector.get_roi_image(img, roi_name)
            
            if roi_img is not None:
                # OCR识别
                numbers = self.ocr.recognize_numbers(roi_img)
                
                if numbers:
                    # 更新状态
                    if "player1_hp" in roi_name:
                        hp = max(numbers) if numbers else 0
                        self.tracker.update_player(0, hp=hp)
                    elif "enemy_hp" in roi_name:
                        hp = max(numbers) if numbers else 0
                        self.tracker.update_enemy(0, hp=hp)
    
    def run(self):
        """运行主循环"""
        if not self.initialize():
            return
        
        self.running = True
        last_status_time = time.time()
        
        print("\n开始监控...")
        print("按 Ctrl+C 停止\n")
        
        try:
            while self.running:
                # 捕获
                img = self.capture_frame()
                
                # 处理
                if img is not None:
                    self.process_frame(img)
                
                # 定期显示状态
                if time.time() - last_status_time > 5:
                    stats = self.tracker.get_statistics()
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] "
                          f"战斗{stats['fight_number']} | "
                          f"伤害: {stats['total_damage']} | "
                          f"DPS: {stats['dps']:.1f}")
                    last_status_time = time.time()
                
                # 控制帧率
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print("\n\n停止监控")
            self.stop()
    
    def stop(self):
        """停止"""
        self.running = False
        
        # 显示最终报告
        print(self.tracker.export_report())
        
        # 保存报告
        self.tracker.save_report()
        
        # 释放资源
        if self.capture:
            self.capture.release()
    
    def calibrate(self):
        """校准ROI区域"""
        print("\n=== ROI 校准模式 ===")
        
        if not self.initialize():
            return
        
        # 捕获一帧
        img = self.capture_frame()
        
        if img is not None:
            filename = f"calibration_{int(time.time())}.png"
            self.capture.save_screenshot(img, filename)
            print(f"截图已保存: {filename}")
            print("\n请查看截图，手动调整 ROI 配置")


def main():
    parser = argparse.ArgumentParser(description="杀戮尖塔2 视觉DPS监控器")
    parser.add_argument("--config", "-c", help="配置文件路径")
    parser.add_argument("--calibrate", action="store_true", help="校准ROI区域")
    parser.add_argument("--fps", type=int, default=2, help="捕获帧率")
    
    args = parser.parse_args()
    
    # 创建监控器
    monitor = STS2VisionMonitor(args.config)
    
    if args.fps:
        monitor.config["fps"] = args.fps
    
    if args.calibrate:
        monitor.calibrate()
    else:
        monitor.run()


if __name__ == "__main__":
    main()
