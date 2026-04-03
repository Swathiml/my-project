import cv2
import numpy as np
from PIL import Image
import pytesseract
import os

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
os.environ["TESSDATA_PREFIX"] = r"C:\Program Files\Tesseract-OCR\tessdata"

class GeometricCorrector:
    def __init__(self):
        self.osd_confidence_threshold = 1
        self.deskew_angle_limit = 5.0
        
    def detect_orientation(self, image) -> tuple:
        """
        Detect image rotation using Tesseract OSD.
        Returns: (angle: 0/90/180/270, confidence: float, method: str)
        """
        if isinstance(image, Image.Image):
            # Convert PIL to OpenCV
            img_array = np.array(image.convert('RGB'))
            img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        else:
            img_cv = image.copy()
        
        try:
            # Tesseract OSD
            osd_data = pytesseract.image_to_osd(img_cv, config="--psm 0", output_type=pytesseract.Output.DICT)

            angle = osd_data['rotate']
            confidence = osd_data['orientation_conf']
            
            if confidence >= self.osd_confidence_threshold:
                return angle, confidence, 'tesseract_osd'
            else:
                # Low confidence - try fallback
                return self._fallback_orientation(image)
                
        except Exception as e:
            # OSD failed (no text, image too small, etc.)
            return self._fallback_orientation(image)
    
    def _fallback_orientation(self, image) -> tuple:
        """
        Fallback: Use aspect ratio heuristics.
        Receipts/statements are typically portrait.
        """
        if isinstance(image, Image.Image):
            width, height = image.size
        else:
            height, width = image.shape[:2]
        
        # If landscape and tall content, might be rotated
        aspect = width / height
        
        if aspect > 1.3:
            # Very wide - likely 90 or 270
            return 90, 0.0, 'aspect_ratio_fallback'
        elif aspect < 0.7:
            # Very tall - correct orientation
            return 0, 0.0, 'aspect_ratio_fallback'
        else:
            # Unclear - assume correct
            return 0, 0.0, 'assumed_correct'
    
    def rotate(self, image, angle: int) -> Image.Image:
        """
        Rotate image to correct orientation.
        Supports: 0, 90, 180, 270
        """
        if angle == 0:
            return image.copy() if isinstance(image, Image.Image) else Image.fromarray(image)
        
        if isinstance(image, Image.Image):
            # PIL rotation
            rotated = image.rotate(-angle, expand=True, fillcolor='white')
            return rotated
        else:
            # OpenCV rotation
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, -angle, 1.0)
            rotated = cv2.warpAffine(image, M, (w, h), borderValue=(255, 255, 255))
            return Image.fromarray(cv2.cvtColor(rotated, cv2.COLOR_BGR2RGB))
    
    def detect_skew(self, image) -> float:
        """
        Detect small skew angle (-5 to +5 degrees) using projection profile.
        Returns angle in degrees.
        """
        if isinstance(image, Image.Image):
            gray = np.array(image.convert('L'))
        else:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Threshold to binary
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Find contours of text lines
        contours, _ = cv2.findContours(binary, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) < 5:
            return 0.0  # Not enough text to detect
        
        # Get bounding boxes of text regions
        angles = []
        for cnt in contours:
            if cv2.contourArea(cnt) > 100:
                rect = cv2.minAreaRect(cnt)
                angle = rect[2]
                
                # Normalize angle
                if angle < -45:
                    angle += 90
                elif angle > 45:
                    angle -= 90
                
                angles.append(angle)
        
        if not angles:
            return 0.0
        
        # Median angle (robust to outliers)
        median_angle = np.median(angles)
        
        # Clamp to valid range
        if abs(median_angle) > self.deskew_angle_limit:
            median_angle = 0.0
        
        return round(median_angle, 2)
    
    def deskew(self, image, angle: float) -> Image.Image:
        """
        Correct small skew angle.
        """
        if abs(angle) < 0.5:
            return image.copy() if isinstance(image, Image.Image) else Image.fromarray(image)
        
        if isinstance(image, Image.Image):
            # PIL deskew via rotation
            rotated = image.rotate(-angle, expand=True, fillcolor='white')
            return rotated
        else:
            # OpenCV
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, -angle, 1.0)
            rotated = cv2.warpAffine(image, M, (w, h), borderValue=(255, 255, 255))
            return Image.fromarray(cv2.cvtColor(rotated, cv2.COLOR_BGR2RGB))
    
    def detect_content_region(self, image) -> tuple:
        """
        Detect actual content bounding box (remove white borders).
        Returns: (x, y, w, h) or None if detection fails
        """
        if isinstance(image, Image.Image):
            gray = np.array(image.convert('L'))
        else:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Threshold
        _, binary = cv2.threshold(gray, 250, 255, cv2.THRESH_BINARY_INV)
        
        # Find content contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None
        
        # Get bounding box of all content
        all_points = []
        for cnt in contours:
            if cv2.contourArea(cnt) > 50:  # Filter tiny noise
                x, y, w, h = cv2.boundingRect(cnt)
                all_points.extend([(x, y), (x+w, y+h)])
        
        if not all_points:
            return None
        
        # Compute overall bounding box
        xs = [p[0] for p in all_points]
        ys = [p[1] for p in all_points]
        
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        
        # Add small padding
        padding = 10
        x_min = max(0, x_min - padding)
        y_min = max(0, y_min - padding)
        x_max = min(gray.shape[1], x_max + padding)
        y_max = min(gray.shape[0], y_max + padding)
        
        return (x_min, y_min, x_max - x_min, y_max - y_min)
    
    def auto_crop(self, image, margin: int = 10) -> Image.Image:
        """
        Crop to content region with margin.
        """
        bbox = self.detect_content_region(image)
        
        if bbox is None:
            return image.copy() if isinstance(image, Image.Image) else Image.fromarray(image)
        
        x, y, w, h = bbox
        
        if isinstance(image, Image.Image):
            width, height = image.size
            # Ensure within bounds
            x = max(0, x - margin)
            y = max(0, y - margin)
            w = min(width - x, w + 2*margin)
            h = min(height - y, h + 2*margin)
            return image.crop((x, y, x+w, y+h))
        else:
            height, width = image.shape[:2]
            x = max(0, x - margin)
            y = max(0, y - margin)
            w = min(width - x, w + 2*margin)
            h = min(height - y, h + 2*margin)
            cropped = image[y:y+h, x:x+w]
            return Image.fromarray(cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB))
    
    def correct_geometry(self, image) -> dict:
        """
        Full geometric correction pipeline.
        
        Returns: {
            'image': corrected PIL.Image,
            'orientation_angle': int,
            'orientation_confidence': float,
            'orientation_method': str,
            'skew_angle': float,
            'preprocessing_applied': list,
            'original_size': (w, h),
            'final_size': (w, h)
        }
        """
        preprocessing = []
        original_size = image.size if isinstance(image, Image.Image) else (image.shape[1], image.shape[0])
        
        # Step 1: Orientation detection and correction
        orient_angle, orient_conf, orient_method = self.detect_orientation(image)
        
        if orient_angle != 0:
            image = self.rotate(image, orient_angle)
            preprocessing.append(f'rotated_{orient_angle}')
        
        # Step 2: Deskew
        skew_angle = self.detect_skew(image)
        
        if abs(skew_angle) > 0.5:
            image = self.deskew(image, skew_angle)
            preprocessing.append(f'deskewed_{skew_angle}')
        
        # Step 3: Auto-crop
        cropped = self.auto_crop(image, margin=15)
        
        if cropped.size != image.size:
            preprocessing.append('auto_cropped')
            image = cropped
        
        final_size = image.size
        
        return {
            'image': image,
            'orientation_angle': orient_angle,
            'orientation_confidence': orient_conf,
            'orientation_method': orient_method,
            'skew_angle': skew_angle,
            'preprocessing_applied': preprocessing,
            'original_size': original_size,
            'final_size': final_size
        }


if __name__ == "__main__":
    from synthetic_generator import SyntheticDocumentGenerator
    
    print("Testing Geometric Corrector...")
    gen = SyntheticDocumentGenerator("test_geo")
    corrector = GeometricCorrector()
    
    test_cases = [
        ("Normal Receipt", gen.generate_receipt(1, None), 0),
        ("Rotated 90", gen.generate_receipt(2, {'rotation': 90}), 90),
        ("Rotated 180", gen.generate_statement(3, {'rotation': 180}), 180),
        ("Rotated 270", gen.generate_invoice(4, {'rotation': 270}), 270),
    ]
    
    for name, path, expected_angle in test_cases:
        img = Image.open(path)
        result = corrector.correct_geometry(img)
        
        print(f"\n{name}:")
        print(f"  Expected rotation: {expected_angle}°")
        print(f"  Detected angle: {result['orientation_angle']}°")
        print(f"  Method: {result['orientation_method']}")
        print(f"  Confidence: {result['orientation_confidence']:.1f}")
        print(f"  Skew: {result['skew_angle']}°")
        print(f"  Preprocessing: {result['preprocessing_applied']}")
        print(f"  Size: {result['original_size']} → {result['final_size']}")
        
        # Save corrected image for visual inspection
        corrected_path = f"test_geo/corrected_{name.replace(' ', '_')}.png"
        result['image'].save(corrected_path)
        print(f"  Saved: {corrected_path}")