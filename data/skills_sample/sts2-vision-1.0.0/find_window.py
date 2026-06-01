#!/usr/bin/env python3
import win32gui
import win32con

def find_windows():
    windows = []
    
    def callback(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                windows.append({
                    "hwnd": hwnd,
                    "title": title
                })
        return True
    
    win32gui.EnumWindows(callback, windows)
    
    # 过滤包含关键词的窗口
    keywords = ["slay", "spire", "游戏", "steam"]
    
    print("=" * 50)
    print("所有可见窗口:")
    print("=" * 50)
    
    for w in windows:
        title_lower = w["title"].lower()
        if any(k in title_lower for k in keywords):
            print(f"[MATCH] {w['title']}")
        else:
            print(f"  {w['title']}")

if __name__ == "__main__":
    find_windows()
