# week6/trust_scorer.py
import re
from datetime import datetime
from typing import Dict, Any


class DocumentTrustScorer:
    
    def __init__(self):
        self.thresholds = {
            'verified': 0.75,
            'low_confidence': 0.50,
            'manual_review': 0.0
        }
    
    def calculate_trust(
        self, 
        week4_output: Dict[str, Any], 
        extracted_facts: Any, 
        doc_type: str
    ) -> Dict[str, Any]:
       
        # Get raw values from document_pipeline
        image_quality = week4_output.get('quality_score', 0.0)
        ocr_confidence = week4_output.get('ocr', {}).get('confidence', 0.0)
        
        #Normalize if values are on 0-100 scale instead of 0-1
        if ocr_confidence > 1.0:
            ocr_confidence = ocr_confidence / 100.0
        if image_quality > 1.0:
            image_quality = image_quality / 100.0
        
        # Ensure bounds
        image_quality = max(0.0, min(1.0, image_quality))
        ocr_confidence = max(0.0, min(1.0, ocr_confidence))
        
        #components
        extraction_completeness = self._score_completeness(extracted_facts, doc_type)
        consistency = self._validate_consistency(extracted_facts)
        
        # Weighted trust score
        trust_score = (
            image_quality * 0.30 +
            ocr_confidence * 0.30 +
            extraction_completeness * 0.20 +
            consistency * 0.20
        )
        
        return {
            'trust_score': round(trust_score, 4),
            'breakdown': {
                'image_quality': round(image_quality, 4),
                'ocr_confidence': round(ocr_confidence, 4),
                'extraction_completeness': round(extraction_completeness, 4),
                'consistency_checks': round(consistency, 4)
            },
            'status': self._status_from_score(trust_score),
            'thresholds_applied': {
                'verified': '>= 0.6',
                'low_confidence': '>= 0.45',
                'manual_review': '< 0.45'
            }
        }
    
    def _score_completeness(self, facts: Any, doc_type: str) -> float:
        """Score 0-1 based on percentage of required fields found."""
        required_fields = {
            'receipt': ['merchant', 'date', 'total_amount'],
            'statement': ['account_holder', 'statement_period', 'transactions'],
            'invoice': ['vendor', 'invoice_date', 'total_due']
        }
        
        fields = required_fields.get(doc_type, ['merchant', 'date', 'amount'])
        
        found = 0
        for field in fields:
            value = getattr(facts, field, None)
            if field == 'statement_period' and isinstance(value, dict):
                found += 1 if value.get('start') and value.get('end') else 0
            elif field == 'transactions' and isinstance(value, list):
                found += 1 if len(value) > 0 else 0
            elif value is not None and value != [] and value != {}:
                found += 1
        
        return found / len(fields) if fields else 0.0
    
    def _validate_consistency(self, facts: Any) -> float:
        """Check logical consistency of extracted facts."""
        score = 1.0
        
        # Date check
        date_value = getattr(facts, 'date', None) or getattr(facts, 'invoice_date', None)
        if date_value:
            try:
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%Y/%m/%d']:
                    try:
                        parsed_date = datetime.strptime(date_value, fmt)
                        if parsed_date > datetime.now():
                            score -= 0.3
                        break
                    except ValueError:
                        continue
            except Exception:
                pass
        
        # Amount check
        total_amount = getattr(facts, 'total_amount', None) or getattr(facts, 'total_due', None)
        if total_amount is not None:
            if total_amount <= 0:
                score -= 0.3
        
        # Math check
        subtotal = getattr(facts, 'subtotal', None)
        tax = getattr(facts, 'tax', None)
        if all([subtotal, tax, total_amount]):
            expected = subtotal + tax
            if abs(total_amount - expected) > 0.01:
                score -= 0.2
        
        return max(score, 0.0)
    
    def _status_from_score(self, score: float) -> str:
        """Determine status based on trust score thresholds."""
        if score >= self.thresholds['verified']:
            return 'verified'
        elif score >= self.thresholds['low_confidence']:
            return 'low_confidence'
        else:
            return 'manual_review'


if __name__ == "__main__":
    from dataclasses import dataclass
    
    @dataclass
    class MockFacts:
        merchant = "Trader Joe's"
        date = "2026-02-07"
        total_amount = 39.12
        subtotal = 36.91
        tax = 2.21
    
    scorer = DocumentTrustScorer()
    
    # Test with normalized values
    week4_output = {
        'quality_score': 0.89,
        'ocr': {'confidence': 0.95}
    }
    
    result = scorer.calculate_trust(week4_output, MockFacts(), 'receipt')
    print(f"Trust score: {result['trust_score']}")
    print(f"Status: {result['status']}")
    print(f"Breakdown: {result['breakdown']}")
    
    # Test with unnormalized values (simulating bug)
    week4_output_bug = {
        'quality_score': 89.0,  # Wrong scale
        'ocr': {'confidence': 95.0}  # Wrong scale
    }
    
    result_bug = scorer.calculate_trust(week4_output_bug, MockFacts(), 'receipt')
    print(f"\nWith bug input (89, 95):")
    print(f"Trust score: {result_bug['trust_score']}")
    print(f"Status: {result_bug['status']}")
    print(f"Breakdown: {result_bug['breakdown']}")
    print(f"Normalized correctly: {result_bug['trust_score'] == result['trust_score']}")