#!/usr/bin/env python3
"""
杀戮尖塔2 智能屏幕捕获
自动检测窗口并使用相对坐标
"""

import os
import sys
import time
import mss
import cv2
import numpy as np
from typing import Optional, Dict
import win32gui
import win32con
import win32ui
from ctypes import windll

# 导入相对坐标配置
from roi_relative import RELATIVE_ROI, get_adaptive_roi

class STS2Capture:
    """杀戮尖塔2智能捕获"""
    
    def __init__(self, window_title: str = "Slay the Spire 2"):
        self.window_title = window_title
        self.sct = mss.mss()
        self.window_info = None
        self.adaptive_roi = {}
        
    def find_window(self) -> Optional[Dict]:
        """查找游戏窗口"""
        def callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if self.window_title.lower() in title.lower():
                    rect = win32gui.GetWindowRect(hwnd)
                    windows.append({
                        "hwnd": hwnd,
                        "title": title,
                        "x": rect[0],
                        "y": rect[1],
                        "width": rect[2] - rect[0],
                        "height": rect[3] - rect[1]
                    })
            return True
        
        windows = []
        win32gui.EnumWindows(callback, windows)
        
        if windows:
            self.window_info = windows[0]
            # 计算自适应ROI
            self.adaptive_roi = get_adaptive_roi(
                self.window_info["width"],
                self.window_info["height"]
            )
            return self.window_info
        return None
    
    def capture(self) -> Optional[np.ndarray]:
        """捕获窗口"""
        if not self.window_info:
            self.find_window()
        
        if not self.window_info:
            print("未找到游戏窗口")
            return None
        
        # 窗口区域
        monitor = {
            "left": self.window_info["x"],
            "top": self.window_info["y"],
            "width": self.window_info["width"],
            "height": self.window_info["height"]
        }
        
        try:
            screenshot = self.sct.grab(monitor)
            img = np.array(screenshot)
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            return img
        except Exception as e:
            print(f"捕获失败: {e}")
            return None
    
    def get_roi(self, name: str) -> Optional[np.ndarray]:
        """获取指定ROI区域"""
        img = self.capture()
        if img is None:
            return None
        
        if name not in self.adaptive_roi:
            return None
        
        roi = self.adaptive_roi[name]
        x, y, w, h = roi["x"], roi["y"], roi["w"], roi["h"]
        
        # 边界检查
        if y + h > img.shape[0] or x + w > img.shape[1]:
            return None
        
        return img[y:y+h, x:x+w]
    
    def get_all_roi(self) -> Dict[str, np.ndarray]:
        """获取所有ROI"""
        img = self.capture()
        if img is None:
            return {}
        
        results = {}
        for name, roi in self.adaptive_roi.items():
            x, y, w, h = roi["x"], roi["y"], roi["w"], roi["h"]
            if y + h <= img.shape[0] and x + w <= img.shape[1]:
                results[name] = img[y:y+h, x:x+w]
        
        return results
    
    def release(self):
        """释放资源"""
        self.sct.close()


def test_capture():
    """测试捕获"""
    print("=" * 50)
    print("杀戮尖塔2 智能捕获测试")
    print("=" * 50)
    
    capture = STS2Capture()
    
    # 查找窗口
    window = capture.find_window()
    if not window:
        print("未找到游戏窗口")
        return
    
    print(f"窗口: {window['title']}")
    print(f"位置: ({window['x']}, {window['y']})")
    print(f"大小: {window['width']} x {window['height']}")
    
    # 捕获
    print("\n捕获图像...")
    img = capture.capture()
    if img is not None:
        print(f"图像尺寸: {img.shape}")
        
        # 保存
        cv2.imwrite("smart_capture.png", img)
        print("已保存: smart_capture.png")
        
        # 获取关键ROI
        print("\n关键区域:")
        for name in ["player_hp_top", "energy", "enemy1_hp", "draw_pile"]:
            roi_img = capture.get_roi(name)
            if roi_img is not None:
                cv2.imwrite(f"smart_{name}.png", roi_img)
                print(f"  {name}: {roi_img.shape}")
    
    capture.release()


if __name__ == "__main__":
    test_capture()
