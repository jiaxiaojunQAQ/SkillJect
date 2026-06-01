from smart_capture import STS2Capture
import cv2

s = STS2Capture()
s.find_window()

r = s.get_roi("enemies_hp")
if r is not None:
    cv2.imwrite("four_enemies_new.png", r)
    print(f"已保存: {r.shape}")
else:
    print("未找到")

s.release()
