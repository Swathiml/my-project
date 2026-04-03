import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import imagehash
from PIL import Image
import hashlib
import re
from typing import Set, Tuple


class DuplicateDetector:
    
    def __init__(self):
        self.seen_hashes: Set[Tuple[str, str]] = set()
    
    def is_duplicate(self, image_path: str, extracted_text: str) -> bool:
        """
        Two-layer detection:
        1. Perceptual hash (catches re-uploads, screenshots, minor edits)
        2. Content fingerprint (catches OCR retries, format conversions)
        
        Returns True if this document was seen before.
        """
        # Layer 1: Visual hash
        try:
            img = Image.open(image_path)
            phash = str(imagehash.phash(img))
        except Exception:
            # If image can't be opened, fall back to content only
            phash = "invalid_image"
        
        # Layer 2: Content fingerprint
        fingerprint = self._content_fingerprint(extracted_text)
        
        combined = (phash, fingerprint)
        
        if combined in self.seen_hashes:
            return True
        
        self.seen_hashes.add(combined)
        return False
    
    def _content_fingerprint(self, text: str) -> str:
        """Extract stable content signature from OCR text."""
        if not text:
            return "empty_text"
        
        # Find amounts (e.g., $39.12)
        amounts = re.findall(r'\$\d+\.\d{2}', text)
        amounts_str = ",".join(sorted(set(amounts))) if amounts else "no_amounts"
        
        # Find dates (MM/DD/YYYY or similar)
        dates = re.findall(r'\d{1,2}/\d{1,2}/\d{2,4}', text)
        dates_str = ",".join(sorted(set(dates))) if dates else "no_dates"
        
        # First non-empty line (often merchant name)
        first_line = ""
        for line in text.strip().split('\n'):
            clean = line.strip()
            if clean and len(clean) > 2:
                first_line = clean[:30].lower()
                break
        
        # Create hash
        content = f"{amounts_str}:{dates_str}:{first_line}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def get_seen_count(self) -> int:
        """Return number of unique documents processed."""
        return len(self.seen_hashes)


if __name__ == "__main__":
    # Test
    from week4_document_pipeline.synthetic_generator import SyntheticDocumentGenerator
    
    print("Testing Duplicate Detector...")
    gen = SyntheticDocumentGenerator("test_dedup")
    detector = DuplicateDetector()
    
    # Generate two different receipts
    receipt1_path = gen.generate_receipt(1, None)
    receipt2_path = gen.generate_receipt(2, None)
    
    # Simulate OCR text (in real use, from OCREngine)
    text1 = "Trader Joe's\nDate: 02/07/2026\nTotal: $39.12"
    text2 = "Whole Foods\nDate: 02/08/2026\nTotal: $45.67"
    
    # First time - not duplicate
    is_dup1 = detector.is_duplicate(receipt1_path, text1)
    print(f"First receipt: is_duplicate={is_dup1} (expected: False)")
    
    # Same receipt again - duplicate
    is_dup2 = detector.is_duplicate(receipt1_path, text1)
    print(f"Same receipt again: is_duplicate={is_dup2} (expected: True)")
    
    # Different receipt - not duplicate
    is_dup3 = detector.is_duplicate(receipt2_path, text2)
    print(f"Different receipt: is_duplicate={is_dup3} (expected: False)")
    
    print(f"\nTotal unique documents: {detector.get_seen_count()}")