"""
Week 7 Day 3: Fuzzy Matcher
Handles real-world discrepancies: tips, posting delays, merchant variations
Confidence range: 0.70 - 0.95
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from rapidfuzz import fuzz

try:
    from models import (
        TransactionDocumentMatch, 
        MatchComponents, 
        MatchType, 
        MatchStatus,
        EvidenceLink
    )
    from exact_matcher import ExactMatcher
except ImportError:
    from week7_reconciliation.models import (
        TransactionDocumentMatch, 
        MatchComponents, 
        MatchType, 
        MatchStatus,
        EvidenceLink
    )
    from week7_reconciliation.exact_matcher import ExactMatcher


class FuzzyMatcher:
    """
    Fuzzy matching layer for real-world tolerance.
    
    Criteria:
    - Amount: Within 1% or $5 tolerance (tips, currency conversion)
    - Date: Within +-3 days (bank posting delays)
    - Merchant: RapidFuzz token_set_ratio >= 85%
    
    Expected confidence: 0.70 - 0.95
    """
    
    # Tolerance constants (more lenient than ExactMatcher)
    AMOUNT_TOLERANCE_PERCENT = 0.01  # 1%
    AMOUNT_TOLERANCE_ABSOLUTE = Decimal('5.00')  # $5 for tips
    DATE_TOLERANCE_DAYS = 3
    MERCHANT_THRESHOLD = 85.0  # token_set_ratio
    
    def __init__(self):
        self.match_count = 0
        self.reject_count = 0
        self.tip_adjustments = 0  # Track tip-related matches
        self.currency_matches = 0  # Track currency/fee matches
    
    def _parse_date(self, date_input) -> datetime:
        """Parse date from string or datetime object."""
        if isinstance(date_input, datetime):
            return date_input
        
        if isinstance(date_input, str):
            try:
                return datetime.fromisoformat(date_input.replace('Z', '+00:00'))
            except ValueError:
                formats = ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y', '%d/%m/%Y']
                for fmt in formats:
                    try:
                        return datetime.strptime(date_input, fmt)
                    except ValueError:
                        continue
                raise ValueError(f"Cannot parse date: {date_input}")
        
        if hasattr(date_input, 'year'):
            return datetime(date_input.year, date_input.month, date_input.day)
        
        raise TypeError(f"Unsupported date type: {type(date_input)}")
    
    def _parse_amount(self, amount_input) -> Decimal:
        """Parse amount from string, float, int, or Decimal."""
        if isinstance(amount_input, Decimal):
            return amount_input
        
        if isinstance(amount_input, (int, float)):
            return Decimal(str(amount_input))
        
        if isinstance(amount_input, str):
            cleaned = amount_input.replace('$', '').replace(',', '').replace('EUR', '').replace('GBP', '').strip()
            return Decimal(cleaned)
        
        raise TypeError(f"Unsupported amount type: {type(amount_input)}")
    
    def _normalize_merchant(self, merchant: str) -> str:
        """Normalize merchant name."""
        if not merchant:
            return ""
        
        normalized = merchant.lower()
        prefixes = ['sq *', 'tst *', 'tse *', 'sp *', 'square ', 'paypal *', 'pp *']
        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):].strip()
        
        # Remove common suffixes (location codes, etc.)
        suffixes = [' - ', ' #', ' ltd', ' inc', ' llc', ' corp']
        for suffix in suffixes:
            if suffix in normalized:
                normalized = normalized.split(suffix)[0].strip()
        
        normalized = ' '.join(normalized.split())
        return normalized
    
    def _calculate_amount_match(self, tx_amount: Decimal, doc_amount: Decimal) -> tuple[float, Optional[str]]:
        """
        Calculate amount similarity and classify discrepancy type.
        Returns (score, discrepancy_reason).
        """
        if tx_amount == 0 and doc_amount == 0:
            return (1.0, None)
        if tx_amount == 0 or doc_amount == 0:
            return (0.0, "zero_amount")
        
        # Calculate percentage difference
        diff = abs(tx_amount - doc_amount)
        max_amount = max(tx_amount, doc_amount)
        percent_diff = float(diff / max_amount)
        
        # Check absolute tolerance (for small amounts/tips)
        within_absolute = diff <= self.AMOUNT_TOLERANCE_ABSOLUTE
        
        # Check percentage tolerance
        within_percent = percent_diff <= self.AMOUNT_TOLERANCE_PERCENT
        
        if within_absolute or within_percent:
            # Scale confidence based on how close (1.0 = exact, 0.7 = at tolerance)
            if percent_diff == 0:
                return (1.0, None)
            
            # Linear scale: exact=1.0, at_tolerance=0.7
            tolerance_used = min(percent_diff / self.AMOUNT_TOLERANCE_PERCENT, 1.0)
            score = 1.0 - (tolerance_used * 0.3)
            
            # Classify type
            if diff <= Decimal('0.01'):
                reason = None
            elif within_absolute and not within_percent:
                reason = "tip_adjustment"
            else:
                reason = "currency_or_fee"
            
            return (score, reason)
        
        return (0.0, f"amount_mismatch_{percent_diff:.2%}")
    
    def _calculate_date_proximity(self, tx_date: datetime, doc_date: datetime) -> float:
        """
        Calculate date proximity.
        1.0 = same day, scales down to 0.7 at +-3 days.
        """
        # Handle timezone
        if tx_date.tzinfo is None and doc_date.tzinfo is not None:
            doc_date = doc_date.replace(tzinfo=None)
        elif tx_date.tzinfo is not None and doc_date.tzinfo is None:
            tx_date = tx_date.replace(tzinfo=None)
        
        diff_days = abs((tx_date - doc_date).days)
        
        if diff_days <= self.DATE_TOLERANCE_DAYS:
            # Linear scale: 0 days=1.0, 3 days=0.7
            return 1.0 - (diff_days * 0.1)
        
        return 0.0
    
    def _calculate_string_similarity(self, tx_merchant: str, doc_merchant: str) -> float:
        """
        Use token_set_ratio for better handling of word order/abbreviations.
        """
        if not tx_merchant or not doc_merchant:
            return 0.0
        
        # token_set_ratio handles "Coffee Shop Downtown" vs "Downtown Coffee Shop"
        ratio = fuzz.token_set_ratio(tx_merchant, doc_merchant)
        return ratio / 100.0
    
    def match(
        self,
        transaction_id: str,
        transaction_amount,
        transaction_date,
        transaction_merchant: str,
        document_id: str,
        document_amount,
        document_date,
        document_merchant: str,
        document_trust_score: float = 1.0
    ) -> Optional[TransactionDocumentMatch]:
        """
        Attempt fuzzy match.
        Returns match if criteria met, None otherwise.
        """
        
        # Parse inputs
        tx_amount = self._parse_amount(transaction_amount)
        doc_amount = self._parse_amount(document_amount)
        tx_date = self._parse_date(transaction_date)
        doc_date = self._parse_date(document_date)
        tx_merchant = self._normalize_merchant(transaction_merchant)
        doc_merchant = self._normalize_merchant(document_merchant)
        
        # Calculate components
        amount_score, amount_reason = self._calculate_amount_match(tx_amount, doc_amount)
        date_proximity = self._calculate_date_proximity(tx_date, doc_date)
        string_similarity = self._calculate_string_similarity(tx_merchant, doc_merchant)
        
        # Check thresholds
        is_fuzzy = (
            amount_score >= 0.7 and  # At least 70% on amount
            date_proximity >= 0.7 and  # At least +-3 days
            string_similarity >= 0.85  # 85% token_set_ratio
        )
        
        if not is_fuzzy:
            self.reject_count += 1
            return None
        
        # Track statistics
        if amount_reason == "tip_adjustment":
            self.tip_adjustments += 1
        elif amount_reason == "currency_or_fee":
            self.currency_matches += 1
        
        self.match_count += 1
        
        # Build detailed reasoning
        discrepancy_parts = []
        if amount_reason:
            discrepancy_parts.append(amount_reason.replace("_", " "))
        if date_proximity < 1.0:
            date_diff = abs((tx_date - doc_date).days)
            discrepancy_parts.append(f"date offset {date_diff} day(s)")
        
        reasoning = f"Fuzzy match: {tx_merchant} vs {doc_merchant}"
        if discrepancy_parts:
            reasoning += f" ({', '.join(discrepancy_parts)})"
        
        # Create match
        match = TransactionDocumentMatch(
            transaction_id=transaction_id,
            document_id=document_id,
            match_type=MatchType.FUZZY,
            status=MatchStatus.SUPPORTED if amount_score == 1.0 else MatchStatus.PARTIAL,
            reasoning=reasoning
        )
        
        match.components = MatchComponents(
            string_similarity=string_similarity,
            amount_match=amount_score,
            date_proximity=date_proximity,
            document_trust=document_trust_score
        )
        
        confidence = match.calculate_confidence()
        
        # Store discrepancy if partial
        if amount_score < 1.0:
            match.amount_discrepancy = abs(tx_amount - doc_amount)
        
        date_diff = abs((tx_date - doc_date).days)
        match.date_offset_days = date_diff
        
        # Evidence chain
        match.add_evidence(
            stage="week7_fuzzy_matcher",
            input_hash=f"{transaction_id}:{document_id}",
            output_result=f"FUZZY_MATCH: confidence={confidence:.4f}",
            metadata={
                "tx_merchant_raw": transaction_merchant,
                "doc_merchant_raw": document_merchant,
                "tx_merchant_normalized": tx_merchant,
                "doc_merchant_normalized": doc_merchant,
                "amount_match": amount_score,
                "amount_reason": amount_reason,
                "date_proximity": date_proximity,
                "string_similarity": string_similarity,
                "date_offset_days": date_diff
            }
        )
        
        return match
    
    def get_stats(self) -> Dict[str, Any]:
        """Return matching statistics."""
        total = self.match_count + self.reject_count
        return {
            "fuzzy_matches": self.match_count,
            "tip_adjustments": self.tip_adjustments,
            "currency_matches": self.currency_matches,
            "rejected": self.reject_count,
            "total_processed": total,
            "match_rate": self.match_count / total if total > 0 else 0.0
        }


class CascadingMatcher:
    """
    Combines ExactMatcher and FuzzyMatcher.
    Tries exact first, then fuzzy if exact fails.
    """
    
    def __init__(self):
        self.exact = ExactMatcher()
        self.fuzzy = FuzzyMatcher()
        self.cascade_stats = {
            "exact_hits": 0,
            "fuzzy_hits": 0,
            "total_misses": 0
        }
    
    def match(self, transaction: Dict, document: Dict) -> Optional[TransactionDocumentMatch]:
        """
        Try exact match first, fall back to fuzzy.
        """
        # Try exact first
        exact_match = self.exact.match(
            transaction_id=transaction['id'],
            transaction_amount=transaction['amount'],
            transaction_date=transaction['date'],
            transaction_merchant=transaction['merchant'],
            document_id=document['id'],
            document_amount=document['amount'],
            document_date=document['date'],
            document_merchant=document['merchant'],
            document_trust_score=document.get('trust_score', 1.0)
        )
        
        if exact_match:
            self.cascade_stats["exact_hits"] += 1
            return exact_match
        
        # Fall back to fuzzy
        fuzzy_match = self.fuzzy.match(
            transaction_id=transaction['id'],
            transaction_amount=transaction['amount'],
            transaction_date=transaction['date'],
            transaction_merchant=transaction['merchant'],
            document_id=document['id'],
            document_amount=document['amount'],
            document_date=document['date'],
            document_merchant=document['merchant'],
            document_trust_score=document.get('trust_score', 1.0)
        )
        
        if fuzzy_match:
            self.cascade_stats["fuzzy_hits"] += 1
            return fuzzy_match
        
        self.cascade_stats["total_misses"] += 1
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Combined statistics from both matchers."""
        return {
            "exact": self.exact.get_stats(),
            "fuzzy": self.fuzzy.get_stats(),
            "cascade": self.cascade_stats
        }


# Tests
if __name__ == "__main__":
    print("=== Fuzzy Matcher Tests ===\n")
    
    # Use single instance for cumulative statistics
    fuzzy = FuzzyMatcher()
    
    # Test 1: Tip adjustment (amount differs by $4)
    print("Test 1: Tip Adjustment (+$4.00 tip)")
    match = fuzzy.match(
        transaction_id="txn_tip_001",
        transaction_amount="45.67",
        transaction_date="2024-03-15",
        transaction_merchant="John's Coffee",
        document_id="doc_tip_001",
        document_amount="49.67",  # +$4 tip
        document_date="2024-03-15",
        document_merchant="John's Coffee Shop",
        document_trust_score=0.90
    )
    if match:
        print(f"[PASS] MATCH: {match.confidence:.4f}")
        print(f"       Reasoning: {match.reasoning}")
        print(f"       Status: {match.status.name}")
        print(f"       Discrepancy: ${match.amount_discrepancy}")
    else:
        print("[FAIL] No match")
    
    # Test 2: Date delay (+2 days posting) - reuse same fuzzy instance
    print("\nTest 2: Date Delay (+2 days)")
    match = fuzzy.match(
        transaction_id="txn_delay_001",
        transaction_amount="123.45",
        transaction_date="2024-03-15",
        transaction_merchant="Whole Foods Market",
        document_id="doc_delay_001",
        document_amount="123.45",
        document_date="2024-03-17",  # +2 days
        document_merchant="Whole Foods",
        document_trust_score=0.85
    )
    if match:
        print(f"[PASS] MATCH: {match.confidence:.4f}")
        print(f"       Reasoning: {match.reasoning}")
        print(f"       Date offset: {match.date_offset_days} days")
    else:
        print("[FAIL] No match")
    
    # Test 3: Merchant abbreviation - reuse same fuzzy instance
    print("\nTest 3: Merchant Abbreviation")
    match = fuzzy.match(
        transaction_id="txn_abbr_001",
        transaction_amount="67.89",
        transaction_date="2024-03-20",
        transaction_merchant="AMZN MKTP",
        document_id="doc_abbr_001",
        document_amount="67.89",
        document_date="2024-03-20",
        document_merchant="Amazon Marketplace",
        document_trust_score=0.88
    )
    if match:
        print(f"[PASS] MATCH: {match.confidence:.4f}")
        print(f"       Reasoning: {match.reasoning}")
        print(f"       String similarity: {match.components.string_similarity:.2f}")
    else:
        print("[FAIL] No match")
    
    # Test 4: Currency conversion (small percentage difference) - reuse same fuzzy instance
    print("\nTest 4: Currency Conversion (0.8% difference)")
    match = fuzzy.match(
        transaction_id="txn_curr_001",
        transaction_amount="100.00",
        transaction_date="2024-03-15",
        transaction_merchant="Uber",
        document_id="doc_curr_001",
        document_amount="100.80",  # 0.8% fee
        document_date="2024-03-15",
        document_merchant="Uber Technologies Inc",
        document_trust_score=0.90
    )
    if match:
        print(f"[PASS] MATCH: {match.confidence:.4f}")
        print(f"       Reasoning: {match.reasoning}")
    else:
        print("[FAIL] No match")
    
    # Test 5: Too different (should reject) - reuse same fuzzy instance
    print("\nTest 5: Too Different (should reject)")
    match = fuzzy.match(
        transaction_id="txn_bad_001",
        transaction_amount="100.00",
        transaction_date="2024-03-15",
        transaction_merchant="Starbucks",
        document_id="doc_bad_001",
        document_amount="500.00",  # Way off
        document_date="2024-03-25",  # Way off
        document_merchant="Best Buy",  # Different merchant
        document_trust_score=0.90
    )
    print("[PASS] Correctly rejected" if not match else f"[FAIL] Unexpected match: {match.confidence:.4f}")
    
    # Print fuzzy statistics before cascade test
    print("\n=== Fuzzy Matcher Statistics (Before Cascade) ===")
    stats = fuzzy.get_stats()
    print(f"Fuzzy matches: {stats['fuzzy_matches']}")
    print(f"Tip adjustments: {stats['tip_adjustments']}")
    print(f"Currency/fee matches: {stats['currency_matches']}")
    print(f"Rejected: {stats['rejected']}")
    
    # Test 6: Cascading matcher (separate instance)
    print("\n=== Cascading Matcher Test ===")
    cascade = CascadingMatcher()
    
    test_cases = [
        # Exact match case
        {
            "transaction": {"id": "txn_ex", "amount": "50.00", "date": "2024-03-15", "merchant": "Coffee Shop"},
            "document": {"id": "doc_ex", "amount": "50.00", "date": "2024-03-15", "merchant": "Coffee Shop", "trust_score": 0.95}
        },
        # Fuzzy match case (tip)
        {
            "transaction": {"id": "txn_fz", "amount": "50.00", "date": "2024-03-15", "merchant": "Coffee Shop"},
            "document": {"id": "doc_fz", "amount": "55.00", "date": "2024-03-16", "merchant": "Coffee Shop Downtown", "trust_score": 0.90}
        },
        # No match case
        {
            "transaction": {"id": "txn_no", "amount": "50.00", "date": "2024-03-15", "merchant": "Coffee Shop"},
            "document": {"id": "doc_no", "amount": "500.00", "date": "2024-03-25", "merchant": "Best Buy", "trust_score": 0.90}
        }
    ]
    
    for case in test_cases:
        result = cascade.match(case["transaction"], case["document"])
        tx_id = case["transaction"]["id"]
        if result:
            print(f"{tx_id}: {result.match_type.name} (confidence: {result.confidence:.4f})")
        else:
            print(f"{tx_id}: NO MATCH")
    
    # Final cascade statistics
    print("\n=== Cascade Statistics ===")
    cascade_stats = cascade.get_stats()
    print(f"Exact matches: {cascade_stats['exact']['exact_matches']}")
    print(f"Fuzzy matches: {cascade_stats['fuzzy']['fuzzy_matches']}")
    print(f"Tip adjustments: {cascade_stats['fuzzy']['tip_adjustments']}")
    print(f"Currency/fee matches: {cascade_stats['fuzzy']['currency_matches']}")
    print(f"Cascade: {cascade_stats['cascade']}")