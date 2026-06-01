#!/usr/bin/env python3
"""
杀戮尖塔2 视觉识别系统
模块二：OCR识别
"""

import os
import cv2
import numpy as np
from typing import Optional, List, Tuple
import re

class OCRRecognizer:
    """OCR识别器"""
    
    def __init__(self):
        # 尝试导入pytesseract
        try:
            import pytesseract
            self.tesseract_available = True
            self.tesseract = pytesseract
        except ImportError:
            self.tesseract_available = False
            print("警告: pytesseract未安装，将使用简单数字识别")
        
        # 尝试导入easyocr
        try:
            import easyocr
            self.easyocr_available = True
            self.reader = easyocr.Reader(['en'], gpu=False)
        except ImportError:
            self.easyocr_available = False
    
    def preprocess_for_ocr(self, image: np.ndarray) -> np.ndarray:
        """图像预处理"""
        if image is None or image.size == 0:
            return None
        
        # 转为灰度
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # 二值化
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 膨胀文字
        kernel = np.ones((2, 2), np.uint8)
        binary = cv2.dilate(binary, kernel, iterations=1)
        
        return binary
    
    def extract_numbers_simple(self, image: np.ndarray) -> List[int]:
        """简单的数字提取（基于连通域分析）"""
        if image is None:
            return []
        
        # 找轮廓
        contours, _ = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        numbers = []
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # 过滤太小的区域
            if w < 5 or h < 10:
                continue
            
            # 提取数字区域
            digit_img = image[y:y+h, x:x+w]
            
            # 简单数字匹配
            number = self._match_digit(digit_img)
            if number is not None:
                numbers.append(number)
        
        return numbers
    
    def _match_digit(self, digit_img: np.ndarray) -> Optional[int]:
        """简单的数字匹配"""
        # 简化的数字识别 - 基于宽高比和像素分布
        h, w = digit_img.shape
        ratio = w / h if h > 0 else 0
        
        # 简单规则
        if ratio < 0.3:
            return 1
        elif ratio < 0.6:
            return 7
        else:
            return None
    
    def recognize_numbers(self, image: np.ndarray) -> List[int]:
        """识别数字"""
        # 预处理
        processed = self.preprocess_for_ocr(image)
        
        if processed is None:
            return []
        
        # 方法1: 简单数字提取
        numbers = self.extract_numbers_simple(processed)
        
        # 方法2: 使用tesseract
        if self.tesseract_available and not numbers:
            try:
                text = self.tesseract.image_to_string(
                    processed, 
                    config='--psm 7 -c tessedit_char_whitelist=0123456789'
                )
                # 提取数字
                numbers = [int(n) for n in re.findall(r'\d+', text)]
            except Exception as e:
                print(f"Tesseract识别失败: {e}")
        
        # 方法3: 使用easyocr
        if self.easyocr_available and not numbers:
            try:
                results = self.reader.readtext(processed)
                for (bbox, text, prob) in results:
                    if prob > 0.5:
                        nums = re.findall(r'\d+', text)
                        numbers.extend([int(n) for n in nums])
            except Exception as e:
                print(f"EasyOCR识别失败: {e}")
        
        return numbers
    
    def recognize_hp(self, hp_image: np.ndarray) -> Optional[int]:
        """识别HP值"""
        numbers = self.recognize_numbers(hp_image)
        
        if not numbers:
            return None
        
        # 通常HP是最大的数字
        return max(numbers) if numbers else None
    
    def recognize_damage(self, damage_image: np.ndarray) -> List[int]:
        """识别伤害数字"""
        numbers = self.recognize_numbers(damage_image)
        return numbers


class TemplateMatcher:
    """模板匹配器"""
    
    def __init__(self):
        self.templates = {}
    
    def load_template(self, name: str, template_path: str):
        """加载模板"""
        if os.path.exists(template_path):
            self.templates[name] = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
            print(f"已加载模板: {name}")
    
    def find_template(self, image: np.ndarray, template_name: str, threshold: float = 0.8) -> List[Tuple]:
        """查找模板位置"""
        if template_name not in self.templates:
            return []
        
        template = self.templates[template_name]
        
        if image is None or template is None:
            return []
        
        # 转为灰度
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # 模板匹配
        result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
        
        # 找匹配位置
        locations = np.where(result >= threshold)
        
        matches = []
        h, w = template.shape[:2]
        
        for pt in zip(*locations[::-1]):
            matches.append((pt[0], pt[1], w, h))
        
        return matches


def test_ocr():
    """测试OCR"""
    print("=" * 50)
    print("OCR识别测试")
    print("=" * 50)
    
    ocr = OCRRecognizer()
    
    # 尝试读取之前的截图
    screenshot_path = "game_screen.png"
    
    if os.path.exists(screenshot_path):
        img = cv2.imread(screenshot_path)
        print(f"已加载截图: {img.shape}")
        
        # 假设玩家HP区域
        # 实际需要根据游戏窗口位置调整
        hp_roi = img[100:130, 100:250] if img.shape[0] > 130 else None
        
        if hp_roi is not None:
            print(f"HP区域: {hp_roi.shape}")
            
            # 识别
            numbers = ocr.recognize_numbers(hp_roi)
            print(f"识别结果: {numbers}")
    else:
        print("未找到截图，请先运行屏幕捕获")


if __name__ == "__main__":
    test_ocr()
