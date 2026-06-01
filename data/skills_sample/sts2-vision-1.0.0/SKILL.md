---
name: sts2-vision-monitor
description: 杀戮尖塔2视觉识别DPS监控系统 - 通过屏幕捕获和OCR识别实时监控战斗数据
---

# STS2 视觉监控技能

## 功能
- 屏幕捕获游戏窗口
- OCR识别HP、伤害等数值
- 实时DPS统计
- 战斗数据报告

## 使用方法

### 启动监控
```bash
python sts2_vision/main.py
```

### 校准ROI
```bash
python sts2_vision/main.py --calibrate
```

### 配置文件
创建 `sts2_vision/config.json`:
```json
{
    "fps": 2,
    "window_title": "Slay The Spire 2",
    "rois": {
        "player1_hp": {"x": 50, "y": 50, "w": 150, "h": 30}
    }
}
```

## 输出
- 实时伤害统计
- DPS计算
- JSON格式报告

## 依赖
- mss
- opencv-python
- pytesseract (可选)
- numpy
