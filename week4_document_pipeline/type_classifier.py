import re
from PIL import Image
from typing import Dict, List, Tuple


class TypeClassifier:
    def __init__(self):
        # Keyword dictionaries for each type
        self.type_keywords = {
            'receipt': [
                'total', 'change', 'cashier', 'thank you', 'receipt', 
                'subtotal', 'tax', 'payment', 'cash', 'credit', 'debit',
                'transaction', 'store', 'purchase', 'item', 'qty',
                'mcdonald', 'starbucks', 'walmart', 'target', 'cvs',
                'trader', 'joe',           # ← ADD THESE
                'whole', 'foods',          # ← ADD THESE
                'grocery', 'supermarket',
                'gas', 'grocery', 'restaurant', 'coffee',
                'debit', 'credit', 'trans', 'reg:'
            ],
            'statement': [
                'statement', 'account', 'balance', 'deposit', 'withdrawal',
                'transaction history', 'beginning balance', 'ending balance',
                'account number', 'routing number', 'summary', 'period',
                'checking', 'savings', 'credit card', 'bank', 'federal'
            ],
            'invoice': [
                'invoice', 'bill to', 'ship to', 'due date', 'payment due',
                'line item', 'description', 'quantity', 'unit price',
                'subtotal', 'total due', 'amount due', 'please remit',
                'purchase order', 'po number', 'terms', 'net 30', 'net 15'
            ]
        }
        
        # Layout features
        self.type_layout_hints = {
            'receipt': {
                'aspect_ratio_range': (0.5, 1.5),  # Tall or square
                'typical_height_range': (400, 1200),
                'has_table': False,  # Usually itemized list, not table
            },
            'statement': {
                'aspect_ratio_range': (0.7, 1.0),  # Portrait
                'typical_height_range': (800, 1500),
                'has_table': True,  # Transaction table
            },
            'invoice': {
                'aspect_ratio_range': (0.7, 1.3),  # Portrait or slightly wide
                'typical_height_range': (600, 1200),
                'has_table': True,  # Line items table
            }
        }
        
        self.confidence_threshold = 0.3
    
    def classify(self, image: Image.Image, ocr_text: str) -> Dict:
        """
        Classify document type using keyword matching and layout analysis.
        
        Returns: {
            'type': 'receipt'/'statement'/'invoice'/'unknown',
            'confidence': float,
            'method': 'rule_based',
            'features': {...},
            'evidence': {...}
        }
        """
        text_lower = ocr_text.lower()
        
        # Score each type
        scores = {}
        evidence = {}
        
        for doc_type, keywords in self.type_keywords.items():
            # Keyword matching
            keyword_hits = [kw for kw in keywords if kw in text_lower]
            keyword_score = len(keyword_hits) / len(keywords) * 3  # Weight: 3x
            
            # Unique keyword ratio (distinct matches)
            unique_ratio = len(set(keyword_hits)) / max(len(keyword_hits), 1)
            
            scores[doc_type] = keyword_score * (0.5 + 0.5 * unique_ratio)
            evidence[doc_type] = {
                'keywords_matched': keyword_hits[:5],  # Top 5
                'keyword_count': len(keyword_hits)
            }
        
        # Layout analysis (secondary signal)
        layout_scores = self._analyze_layout(image, text_lower)
        
        # Combine scores
        for doc_type in scores:
            layout_boost = layout_scores.get(doc_type, 0)
            scores[doc_type] += layout_boost * 0.3  # Layout weight: 0.3
        
        # Determine winner
        if not scores:
            return self._unknown_result()
        
        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]
        
        # Calculate confidence based on margin to second best
        second_best = sorted(scores.values(), reverse=True)[1] if len(scores) > 1 else 0
        margin = best_score - second_best
        
        # Normalize to 0-1 confidence
        confidence = min(best_score / 2.0, 1.0)  # Cap at 2.0 raw score
        
        # Determine status
        if confidence >= 0.7 and margin > 0.3:
            status = 'high_confidence'
        elif confidence >= 0.4:
            status = 'medium_confidence'
        else:
            status = 'low_confidence'
            best_type = 'unknown'
        
        return {
            'type': best_type,
            'confidence': round(confidence, 4),
            'status': status,
            'method': 'rule_based',
            'margin_to_second': round(margin, 4),
            'all_scores': {k: round(v, 4) for k, v in scores.items()},
            'evidence': evidence.get(best_type, {}),
            'layout_features': layout_scores
        }
    
    def _analyze_layout(self, image: Image.Image, text_lower: str) -> Dict[str, float]:
        """
        Analyze layout features to boost classification.
        """
        width, height = image.size
        aspect = width / height
        
        scores = {}
        
        # Receipt: narrow, tall
        if 0.5 <= aspect <= 0.8 and height > width:
            scores['receipt'] = 0.5
        
        # Statement: strict portrait, mentions of "statement"
        if 0.7 <= aspect <= 1.0 and 'statement' in text_lower:
            scores['statement'] = 0.8
        
        # Invoice: mentions of "invoice" with table-like structure
        if 'invoice' in text_lower:
            scores['invoice'] = 1.0
        
        # Check for table structure (multiple aligned columns)
        lines = text_lower.split('\n')
        table_like = self._detect_table_structure(lines)
        
        if table_like:
            scores['statement'] = scores.get('statement', 0) + 0.3
            scores['invoice'] = scores.get('invoice', 0) + 0.4
        
        return scores
    
    def _detect_table_structure(self, lines: List[str]) -> bool:
        """
        Detect if text has table-like structure (multiple numeric columns).
        """
        numeric_lines = 0
        
        for line in lines:
            # Count numbers in line
            numbers = re.findall(r'\$?\d+\.?\d*', line)
            if len(numbers) >= 2:  # Multiple numbers = potential table row
                numeric_lines += 1
        
        # If >30% of lines have multiple numbers, likely a table
        if len(lines) > 0 and numeric_lines / len(lines) > 0.3:
            return True
        
        return False
    
    def _unknown_result(self) -> Dict:
        """Return unknown classification."""
        return {
            'type': 'unknown',
            'confidence': 0.0,
            'status': 'low_confidence',
            'method': 'rule_based',
            'margin_to_second': 0.0,
            'all_scores': {},
            'evidence': {},
            'layout_features': {}
        }
    
    def get_routing_decision(self, classification: Dict) -> str:
        """
        Determine processing strategy based on type.
        """
        doc_type = classification['type']
        confidence = classification['confidence']
        
        if confidence < 0.4:
            return 'manual_review'
        
        routing = {
            'receipt': 'key_value_extraction',  # Extract merchant, total, date
            'statement': 'table_extraction',    # Extract transaction rows
            'invoice': 'structured_parsing',     # Extract line items, totals
            'unknown': 'generic_ocr'
        }
        
        return routing.get(doc_type, 'generic_ocr')


if __name__ == "__main__":
    from synthetic_generator import SyntheticDocumentGenerator
    from PIL import Image
    import pytesseract
    
    # Configure Tesseract
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    
    print("Testing Document Type Classifier...")
    gen = SyntheticDocumentGenerator("test_type")
    classifier = TypeClassifier()
    
    test_cases = [
        ("Receipt", gen.generate_receipt(1, None)),
        ("Statement", gen.generate_statement(2, None)),
        ("Invoice", gen.generate_invoice(3, None)),
    ]
    
    for name, path in test_cases:
        img = Image.open(path)
        
        # Run OCR (simulate Day 5)
        ocr_text = pytesseract.image_to_string(img)
        
        # Classify
        result = classifier.classify(img, ocr_text)
        routing = classifier.get_routing_decision(result)
        
        print(f"\n{name}:")
        print(f"  Detected Type: {result['type']}")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Status: {result['status']}")
        print(f"  Routing: {routing}")
        print(f"  Evidence: {result['evidence']}")
        print(f"  All Scores: {result['all_scores']}")