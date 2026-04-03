import cv2
import numpy as np
from PIL import Image


class QualityScorer:
    def __init__(self):
        self.sharpness_thresholds = {
            'excellent': 500,
            'good': 300,
            'poor': 100
        }
    
    def sharpness(self, image) -> float:
        """Laplacian variance for sharpness detection"""
        if isinstance(image, Image.Image):
            gray = np.array(image.convert('L'))
        else:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()
        score = min(variance / 500, 1.0)
        
        return round(score, 4)
    
    def noise_level(self, image) -> float:
        """MAD-based noise estimation on flat regions"""
        if isinstance(image, Image.Image):
            gray = np.array(image.convert('L')).astype(np.float32)
        else:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32)
        
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(sobelx**2 + sobely**2)
        
        flat_mask = gradient_magnitude < 50
        
        if flat_mask.sum() < 100:
            return 0.5
        
        flat_pixels = gray[flat_mask]
        median = np.median(flat_pixels)
        mad = np.median(np.abs(flat_pixels - median))
        
        noise_score = min(mad / 20, 1.0)
        quality_score = 1.0 - noise_score
        
        return round(quality_score, 4)
    
    def contrast_score(self, image) -> float:
        """Histogram analysis for contrast and clipping detection"""
        if isinstance(image, Image.Image):
            gray = np.array(image.convert('L'))
        else:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
        total_pixels = gray.size
        
        black_clip = hist[0:5].sum() / total_pixels
        white_clip = hist[251:256].sum() / total_pixels
        
        # Only penalize severe black clipping (faded ink), not white background
        if black_clip > 0.15:
            return round(0.3, 4)
        
        cumsum = np.cumsum(hist) / total_pixels
        low_bound = np.where(cumsum > 0.025)[0][0]
        high_bound = np.where(cumsum > 0.975)[0][0]
        effective_range = high_bound - low_bound
        
        score = min(effective_range / 150, 1.0)
        return round(max(score, 0.1), 4)
    
    def compute_quality(self, image) -> dict:
        """Full quality analysis with weighted composite"""
        sharp = self.sharpness(image)
        noise = self.noise_level(image)
        contrast = self.contrast_score(image)
        
        if isinstance(image, Image.Image):
            width, height = image.size
        else:
            height, width = image.shape[:2]
        
        pixel_count = width * height
        # 1M pixels = full resolution score (600x800=480k, 800x1000=800k)
        resolution_score = min(pixel_count / 1000000, 1.0)
        
        overall = sharp * 0.40 + noise * 0.25 + contrast * 0.25 + resolution_score * 0.10
        
        return {
            'overall': round(overall, 4),
            'sharpness': sharp,
            'noise': noise,
            'contrast': contrast,
            'resolution': round(resolution_score, 4),
            'dimensions': (width, height),
            'pixel_count': pixel_count
        }
    
    def route_by_quality(self, quality_dict: dict) -> str:
        """Determine processing path"""
        score = quality_dict['overall']
        sharpness = quality_dict['sharpness']
        
        if score >= 0.7 and sharpness >= 0.6:
            return 'direct_ocr'
        elif score >= 0.4:
            return 'enhance_then_ocr'
        else:
            return 'reject_or_manual'
    
    def get_recommendations(self, quality_dict: dict) -> list:
        """Suggest preprocessing steps"""
        recs = []
        
        if quality_dict['sharpness'] < 0.5:
            recs.append('sharpen')
        if quality_dict['noise'] < 0.6:
            recs.append('denoise')
        if quality_dict['contrast'] < 0.5:
            recs.append('contrast_enhance')
        if quality_dict['resolution'] < 0.3:
            recs.append('upscale')
        
        return recs


if __name__ == "__main__":
    from synthetic_generator import SyntheticDocumentGenerator
    from PIL import Image
    
    print("Testing Quality Scorer...")
    gen = SyntheticDocumentGenerator("test_quality")
    scorer = QualityScorer()
    
    test_cases = [
        ("Clean Receipt", gen.generate_receipt(1, None)),
        ("Blur Receipt", gen.generate_receipt(2, {'blur': 2})),
        ("Noisy Statement", gen.generate_statement(3, {'noise': 0.05})),
        ("Rotated Invoice", gen.generate_invoice(4, {'rotation': 90})),
    ]
    
    for name, path in test_cases:
        img = Image.open(path)
        quality = scorer.compute_quality(img)
        route = scorer.route_by_quality(quality)
        recs = scorer.get_recommendations(quality)
        
        print(f"\n{name}:")
        print(f"  Overall: {quality['overall']}")
        print(f"  Sharpness: {quality['sharpness']}, Noise: {quality['noise']}, Contrast: {quality['contrast']}")
        print(f"  Route: {route}")
        print(f"  Recommendations: {recs}")