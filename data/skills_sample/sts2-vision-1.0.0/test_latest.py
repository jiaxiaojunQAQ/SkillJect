from smart_capture import STS2Capture
import cv2

s = STS2Capture()
s.find_window()

img = s.capture()
if img is not None:
    # 用户给的是绝对坐标
    x1, y1 = 1718, 997
    x2, y2 = 2306, 1119
    
    # 转换
    wx, wy = 304, 176
    
    # 裁剪
    roi = img[y1:y2, x1:x2]
    cv2.imwrite("four_enemies_latest.png", roi)
    print(f"已保存: {roi.shape}")

s.release()
