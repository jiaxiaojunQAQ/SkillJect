from smart_capture import STS2Capture
import cv2

capture = STS2Capture()
window = capture.find_window()

if window:
    print(f"窗口: {window['title']}")
    
    # 获取所有ROI
    rois = capture.get_all_roi()
    
    # 保存三个敌人截图
    for name in ["enemy1_hp", "enemy2_hp", "enemy3_hp"]:
        if name in rois:
            cv2.imwrite(f"three_enemies_{name}.png", rois[name])
            print(f"已保存: three_enemies_{name}.png")

capture.release()
print("完成")
