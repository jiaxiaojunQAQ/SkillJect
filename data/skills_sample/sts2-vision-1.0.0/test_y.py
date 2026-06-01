from smart_capture import STS2Capture
import cv2

s = STS2Capture()
s.find_window()

# 捕获大区域尝试
rois = s.get_all_roi()

# 尝试不同y值
for y in [800, 820, 840, 860, 880]:
    test_roi = {"x": 1414, "y": y, "w": 588, "h": 122}
    img = s.capture()
    if img is not None:
        roi = img[y:y+122, 1414:1414+588]
        cv2.imwrite(f"test_y{y}.png", roi)
        print(f"y={y}: {roi.shape}")

s.release()
