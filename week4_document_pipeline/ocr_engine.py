import cv2
import numpy as np
from PIL import Image
import pytesseract
from typing import Dict, List
from dataclasses import dataclass
import re


@dataclass
class OCRResult:
    """Simplified output for pipeline integration."""
    text: str
    confidence: float


class OCREngine:
    def __init__(self):
        # Tesseract configuration
        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        
        # OCR configs for different document types
        self.configs = {
            'receipt': '--psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz$.,:/- ',
            'statement': '--psm 6',
            'invoice': '--psm 6',
            'default': '--psm 3'
        }
    
    def extract(self, image: Image.Image, doc_type: str = 'default') -> Dict:
        """
        Full extraction with bounding boxes and structure.
        """
        config = self.configs.get(doc_type, self.configs['default'])
        
        # Convert PIL to OpenCV for preprocessing
        img_array = np.array(image.convert('RGB'))
        img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # Preprocess
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        if self._estimate_noise(gray) > 20:
            gray = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        
        processed = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        
        processed_pil = Image.fromarray(processed)
        
        # OCR with bounding box data
        ocr_data = pytesseract.image_to_data(
            processed_pil,
            config=config,
            output_type=pytesseract.Output.DICT
        )
        
        # Extract blocks and confidence
        blocks = []
        words = []
        total_confidence = 0
        conf_count = 0
        
        n_boxes = len(ocr_data['text'])
        for i in range(n_boxes):
            text = ocr_data['text'][i].strip()
            
            # Handle invalid confidence safely
            conf_str = ocr_data['conf'][i]
            conf = int(conf_str) if conf_str != '-1' else -1
            
            if text and conf > 30:
                words.append(text)
                total_confidence += conf
                conf_count += 1
                
                block = {
                    'text': text,
                    'confidence': conf,
                    'bbox': {
                        'x': ocr_data['left'][i],
                        'y': ocr_data['top'][i],
                        'width': ocr_data['width'][i],
                        'height': ocr_data['height'][i]
                    }
                }
                blocks.append(block)
        
        avg_confidence = total_confidence / conf_count if conf_count > 0 else 0
        
        raw_text = pytesseract.image_to_string(processed_pil, config=config)
        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
        
        return {
            'raw_text': raw_text,
            'lines': lines,
            'blocks': blocks,
            'word_count': len(words),
            'confidence': round(avg_confidence, 2),
            'config_used': config
        }
    
    def extract_simple(self, image_path: str, doc_type: str = "receipt") -> OCRResult:
        """
        Simplified interface for pipeline integration.
        """
        try:
            # Ensure RGB consistency
            img = Image.open(image_path).convert("RGB")
            result = self.extract(img, doc_type)
            
            # Safety: empty result
            if not result or result.get('word_count', 0) == 0:
                return OCRResult(text="", confidence=0.0)
            
            # Normalize text
            text = result['raw_text'].replace("\n", " ").strip()
            
            # Normalize confidence to 0-1 scale
            conf = result['confidence'] / 100 if result['confidence'] > 0 else 0.0
            
            return OCRResult(text=text, confidence=round(conf, 4))
            
        except Exception:
            return OCRResult(text="", confidence=0.0)
    
    def _estimate_noise(self, gray_img: np.ndarray) -> float:
        """Quick noise estimate using Laplacian variance."""
        laplacian = cv2.Laplacian(gray_img, cv2.CV_64F)
        return laplacian.var()
    
    def extract_structure(self, ocr_result: Dict) -> Dict:
        """Analyze OCR result and extract document structure."""
        lines = ocr_result.get('lines', [])
        
        # Headers (short, all caps)
        headers = [l for l in lines if len(l) < 50 and l.isupper()]
        
        # Amounts
        amounts = []
        for line in lines:
            nums = re.findall(r'\$?\d+\.\d{2}', line)
            if nums:
                amounts.append({'line': line, 'values': nums})
        
        # Dates
        dates = []
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{2,4}',
            r'\d{1,2}-\d{1,2}-\d{2,4}',
            r'\d{4}-\d{2}-\d{2}'
        ]
        for line in lines:
            for pattern in date_patterns:
                matches = re.findall(pattern, line)
                dates.extend(matches)
        
        return {
            'headers': headers[:5],
            'amounts': amounts[:10],
            'dates': dates[:5],
            'line_count': len(lines),
            'avg_line_length': sum(len(l) for l in lines) / len(lines) if lines else 0
        }