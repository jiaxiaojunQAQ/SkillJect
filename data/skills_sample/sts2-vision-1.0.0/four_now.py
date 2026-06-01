from smart_capture import STS2Capture
import cv2

s = STS2Capture()
s.find_window()

# 获取所有敌人ROI
rois = s.get_all_roi()

# 保存4个敌人的截图
for i in range(1, 5):
    name = f"enemy{i}_hp"
    if name in rois:
        cv2.imwrite(f"four_now_enemy{i}.png", rois[name])
        print(f"已保存: {name}")

# 列出所有ROI
print("\n所有ROI:")
for name in sorted(rois.keys()):
    if "enemy" in name.lower():
        print(f"  {name}: {rois[name].shape}")

s.release()
