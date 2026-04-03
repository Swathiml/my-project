import re
from typing import Dict, Any


class PartialMatchFlagger:
    """
    Flags documents where extracted amount may not match bank transaction amount.
    Enables fuzzy matching for tips, currency conversion, refunds.
    """
    
    def __init__(self):
        self.tip_keywords = ['TIP', 'GRATUITY', 'TIP ADJUSTMENT', 'GRATUITY ADDED']
        self.currency_keywords = ['EUR', '€', 'GBP', '£', 'CAD', '¥', 'JPY','INR', '₹','FOREIGN TXN', 'CONVERSION RATE']
        self.refund_keywords = ['REFUND', 'RETURN', 'CREDIT', 'REVERSAL']
    
    def flag(self, extracted_facts: Any, raw_text: str) -> Dict[str, Any]:
        """
        Analyze document for partial match indicators.
        
        Returns:
            Dict with partial_match_eligible, reason, confidence_penalty, suggested_tolerance
        """
        flags = {
            'partial_match_eligible': False,
            'reason': None,
            'confidence_penalty': 0.0,
            'suggested_tolerance': 0.0  # Percentage amount difference to allow
        }
        
        text_upper = raw_text.upper()
        
        # Check 1: Tip detection
        if any(word in text_upper for word in self.tip_keywords):
            flags['partial_match_eligible'] = True
            flags['reason'] = 'tip_detected'
            flags['confidence_penalty'] = 0.05
            flags['suggested_tolerance'] = 0.20  # 20% tolerance for tips
        
        # Check 2: Currency conversion
        elif any(curr in text_upper for curr in self.currency_keywords):
            flags['partial_match_eligible'] = True
            flags['reason'] = 'currency_conversion'
            flags['confidence_penalty'] = 0.03
            flags['suggested_tolerance'] = 0.05  # 5% for forex
        
        # Check 3: Refund indicators
        elif any(word in text_upper for word in self.refund_keywords):
            flags['partial_match_eligible'] = True
            flags['reason'] = 'refund'
            flags['confidence_penalty'] = 0.02
            flags['suggested_tolerance'] = 0.02  # 2% for refunds
        
        # Check 4: Math discrepancy in receipt itself
        subtotal = getattr(extracted_facts, 'subtotal', None)
        tax = getattr(extracted_facts, 'tax', None)
        total = getattr(extracted_facts, 'total_amount', None) or getattr(extracted_facts, 'total_due', None)
        
        if all([subtotal, tax, total]):
            expected = subtotal + tax
            if abs(total - expected) > 0.01:
                # Already flagged by trust scorer, but note for partial match
                if not flags['partial_match_eligible']:
                    flags['partial_match_eligible'] = True
                    flags['reason'] = 'internal_math_discrepancy'
                    flags['confidence_penalty'] = 0.03
                    flags['suggested_tolerance'] = 0.03
        
        return flags
    
    def get_explanation(self, flags: Dict[str, Any]) -> str:
        """Human-readable explanation of partial match flag."""
        if not flags['partial_match_eligible']:
            return "Exact match expected"
        
        reason_map = {
            'tip_detected': 'Tip may cause amount mismatch with bank transaction',
            'currency_conversion': 'Foreign currency conversion may cause small discrepancy',
            'refund': 'Refund transaction - negative amount expected',
            'internal_math_discrepancy': 'Receipt math error detected'
        }
        
        base = reason_map.get(flags['reason'], flags['reason'])
        return f"{base} (tolerance: {flags['suggested_tolerance']*100:.0f}%)"


if __name__ == "__main__":
    # Test
    from dataclasses import dataclass
    
    @dataclass
    class MockFacts:
        total_amount = 45.67
        subtotal = 42.00
        tax = 3.67
    
    print("Testing Partial Match Flagger...")
    flagger = PartialMatchFlagger()
    
    test_cases = [
        ("Standard receipt", "Trader Joe's\nTotal: $39.12"),
        ("Receipt with tip", "Restaurant\nSubtotal: $40.00\nTip: $8.00\nTotal: $48.00"),
        ("Foreign currency", "Cafe Paris\nAmount: €35.00\nConversion: $38.50"),
        ("Refund", "Return processed\nCredit: $25.00"),
    ]
    
    for name, text in test_cases:
        facts = MockFacts()
        flags = flagger.flag(facts, text)
        explanation = flagger.get_explanation(flags)
        
        print(f"\n{name}:")
        print(f"  Eligible: {flags['partial_match_eligible']}")
        print(f"  Reason: {flags['reason']}")
        print(f"  Penalty: {flags['confidence_penalty']}")
        print(f"  Tolerance: {flags['suggested_tolerance']*100:.0f}%")
        print(f"  Explanation: {explanation}")