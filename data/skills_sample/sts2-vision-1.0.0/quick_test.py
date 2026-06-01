#!/usr/bin/env python3
print("开始测试...")

from smart_capture import STS2Capture
import cv2

capture = STS2Capture()
print("查找窗口...")
window = capture.find_window()

if window:
    print(f"找到: {window['title']}")
    print(f"大小: {window['width']} x {window['height']}")
    
    print("捕获...")
    img = capture.capture()
    
    if img is not None:
        print(f"图像: {img.shape}")
        
        # 获取ROI
        rois = capture.get_all_roi()
        print(f"ROI数量: {len(rois)}")
        
        # 保存
        cv2.imwrite("test_result.png", img)
        print("已保存: test_result.png")
        
        # 保存关键ROI
        for name in ["player1_hp_bottom", "enemy1_hp"]:
            if name in rois:
                cv2.imwrite(f"test_{name}.png", rois[name])
                print(f"已保存: test_{name}.png")
else:
    print("未找到窗口")

capture.release()
print("完成")
