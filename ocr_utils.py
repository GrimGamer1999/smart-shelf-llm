import pytesseract
from PIL import Image
import cv2
import numpy as np
import re
import calendar

def preprocess_image(pil_image, mode="product"):
    img = np.array(pil_image)
    
    if len(img.shape) == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    if mode == "expiry":
        gray = cv2.equalizeHist(gray)
        gray = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return Image.fromarray(otsu)
    else:
        height, width = gray.shape
        if height < 300:
            scale = 300 / height
            gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        
        gray = cv2.fastNlMeansDenoising(gray, None, 7, 7, 21)
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        gray = cv2.filter2D(gray, -1, kernel)
        gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=10)
        
        return Image.fromarray(gray)

def extract_text_multiconfig(pil_image):
    configs = ['--psm 6', '--psm 3', '--psm 11']
    results = []
    for config in configs:
        try:
            text = pytesseract.image_to_string(pil_image, config=config)
            if text.strip():
                results.append(text.strip())
        except:
            continue
    return max(results, key=len) if results else ""

def parse_expiry_date(text):
    patterns = [
        r'(\d{2})\.(\d{4})',
        r'(\d{2})/(\d{4})',
        r'EXP[:\s]*([A-Z]{3,9})[-\s\.]*(\d{4})',
        r'EXP[:\s]*(\d{2}[-/\.]\d{2}[-/\.]\d{4})',
        r'BEST\s*BEFORE[:\s]*([A-Z]{3,9})[-\s\.]*(\d{4})',
        r'USE\s*BY[:\s]*([A-Z]{3,9})[-\s\.]*(\d{4})',
        r'HALTBAR\s*BIS[:\s]*(\d{2}[-/\.]\d{4})',
        r'MHD[:\s]*(\d{2}[-/\.]\d{4})',
        r'\b([A-Z]{3,9})[-\s\.]+(\d{4})\b',
    ]
    
    month_map = {
        'JAN': 1, 'JANUARY': 1, 'FEB': 2, 'FEBRUARY': 2,
        'MAR': 3, 'MARCH': 3, 'APR': 4, 'APRIL': 4, 'MAY': 5,
        'JUN': 6, 'JUNE': 6, 'JUL': 7, 'JULY': 7,
        'AUG': 8, 'AUGUST': 8, 'SEP': 9, 'SEPT': 9, 'SEPTEMBER': 9,
        'OCT': 10, 'OCTOBER': 10, 'NOV': 11, 'NOVEMBER': 11,
        'DEC': 12, 'DECEMBER': 12
    }
    
    text_upper = text.upper()
    
    for pattern in patterns:
        match = re.search(pattern, text_upper)
        if match:
            try:
                groups = match.groups()
                
                if len(groups) == 2 and groups[0].isdigit() and len(groups[0]) == 2:
                    month = int(groups[0])
                    year = int(groups[1])
                    if 1 <= month <= 12:
                        last_day = calendar.monthrange(year, month)[1]
                        return f"{last_day:02d}-{month:02d}-{year}"
                
                if len(groups) == 2 and groups[0] in month_map:
                    month = month_map[groups[0]]
                    year = int(groups[1])
                    last_day = calendar.monthrange(year, month)[1]
                    return f"{last_day:02d}-{month:02d}-{year}"
                
                if len(groups) == 1 and '-' in groups[0]:
                    date_str = groups[0].replace(' ', '-').replace('.', '-').replace('/', '-')
                    parts = date_str.split('-')
                    
                    if len(parts) == 2:
                        month_str, year_str = parts
                        
                        if month_str in month_map:
                            month = month_map[month_str]
                            year = int(year_str)
                            last_day = calendar.monthrange(year, month)[1]
                            return f"{last_day:02d}-{month:02d}-{year}"
                        
                        try:
                            month = int(month_str)
                            year = int(year_str)
                            if 1 <= month <= 12:
                                last_day = calendar.monthrange(year, month)[1]
                                return f"{last_day:02d}-{month:02d}-{year}"
                        except:
                            pass
            except:
                continue
    
    return None