#!/usr/bin/env python3
"""
杀戮尖塔2 视觉识别系统
模块一：屏幕捕获
"""

import os
import sys
import time
import mss
import cv2
import numpy as np
from typing import Optional, Tuple, Dict, List
import json

class ScreenCapture:
    """屏幕捕获模块"""
    
    def __init__(self, fps: int = 2):
        self.fps = fps
        self.sct = mss.mss()
        self.last_capture_time = 0
        self.capture_interval = 1.0 / fps
        
    def get_game_window(self, window_title: str = None) -> Optional[Dict]:
        """获取游戏窗口信息"""
        import win32gui
        import win32con
        
        if window_title is None:
            window_title = "Slay The Spire 2"
        
        def callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if window_title.lower() in title.lower():
                    rect = win32gui.GetWindowRect(hwnd)
                    windows.append({
                        "hwnd": hwnd,
                        "title": title,
                        "rect": rect,
                        "x": rect[0],
                        "y": rect[1],
                        "width": rect[2] - rect[0],
                        "height": rect[3] - rect[1]
                    })
            return True
        
        windows = []
        win32gui.EnumWindows(callback, windows)
        
        return windows[0] if windows else None
    
    def capture_window(self, window_info: Dict) -> Optional[np.ndarray]:
        """捕获窗口图像"""
        # 限制捕获频率
        now = time.time()
        if now - self.last_capture_time < self.capture_interval:
            return None
        
        self.last_capture_time = now
        
        # 捕获指定区域
        monitor = {
            "left": window_info["x"],
            "top": window_info["y"],
            "width": window_info["width"],
            "height": window_info["height"]
        }
        
        try:
            screenshot = self.sct.grab(monitor)
            # 转换为numpy数组 (BGRA -> BGR)
            img = np.array(screenshot)
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            return img
        except Exception as e:
            print(f"捕获失败: {e}")
            return None
    
    def capture_region(self, x: int, y: int, width: int, height: int) -> Optional[np.ndarray]:
        """捕获指定区域"""
        monitor = {"left": x, "top": y, "width": width, "height": height}
        
        try:
            screenshot = self.sct.grab(monitor)
            img = np.array(screenshot)
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            return img
        except Exception as e:
            print(f"区域捕获失败: {e}")
            return None
    
    def save_screenshot(self, img: np.ndarray, filename: str = None):
        """保存截图"""
        if filename is None:
            filename = f"screenshot_{int(time.time())}.png"
        
        cv2.imwrite(filename, img)
        print(f"截图已保存: {filename}")
        return filename
    
    def release(self):
        """释放资源"""
        self.sct.close()


class ROIDetector:
    """兴趣区域检测器"""
    
    # 典型的杀戮尖塔2 UI布局（需要根据实际游戏调整）
    # 这是一个示例配置
    DEFAULT_ROIS = {
        "player1_hp": {"x": 100, "y": 100, "w": 150, "height": 30},
        "player2_hp": {"x": 100, "y": 150, "w": 150, "height": 30},
        "enemy_hp": {"x": 500, "y": 100, "w": 150, "height": 30},
        "damage_numbers": {"x": 300, "y": 200, "w": 200, "height": 100},
    }
    
    def __init__(self, config_path: str = None):
        self.rois = self.DEFAULT_ROIS.copy()
        
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.rois = json.load(f)
    
    def add_roi(self, name: str, x: int, y: int, width: int, height: int):
        """添加兴趣区域"""
        self.rois[name] = {"x": x, "y": y, "w": width, "height": height}
    
    def get_roi_image(self, full_image: np.ndarray, roi_name: str) -> Optional[np.ndarray]:
        """获取兴趣区域图像"""
        if roi_name not in self.rois:
            return None
        
        roi = self.rois[roi_name]
        x, y = roi["x"], roi["y"]
        w, h = roi["w"], roi["height"]
        
        # 确保不超出图像范围
        if y + h > full_image.shape[0] or x + w > full_image.shape[1]:
            return None
        
        return full_image[y:y+h, x:x+w]
    
    def save_config(self, config_path: str):
        """保存配置"""
        with open(config_path, 'w') as f:
            json.dump(self.rois, f, indent=2)
        print(f"ROI配置已保存: {config_path}")


def find_game_window():
    """查找游戏窗口"""
    capture = ScreenCapture()
    window = capture.get_game_window()
    
    if window:
        print(f"找到游戏窗口: {window['title']}")
        print(f"位置: ({window['x']}, {window['y']})")
        print(f"大小: {window['width']} x {window['height']}")
        return window
    else:
        print("未找到游戏窗口")
        return None


def test_capture():
    """测试捕获"""
    print("=" * 50)
    print("屏幕捕获测试")
    print("=" * 50)
    
    capture = ScreenCapture(fps=1)
    
    # 查找窗口
    window = find_game_window()
    if not window:
        return
    
    # 捕获一帧
    print("\n捕获窗口...")
    img = capture.capture_window(window)
    
    if img is not None:
        print(f"图像尺寸: {img.shape}")
        
        # 保存截图
        filename = capture.save_screenshot(img, "game_screen.png")
        
        # 测试ROI
        detector = ROIDetector()
        
        # 假设玩家1血量在 (100, 100)
        player_hp = detector.get_roi_image(img, "player1_hp")
        if player_hp is not None:
            print(f"玩家HP区域: {player_hp.shape}")
            cv2.imwrite("roi_test.png", player_hp)
    
    capture.release()


if __name__ == "__main__":
    test_capture()
