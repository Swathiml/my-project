"""
Week 7 Day 2: Exact Matcher
Matches transactions to documents with high precision (confidence >= 0.95)
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
except ImportError:
    from week7_reconciliation.models import (
        TransactionDocumentMatch, 
        MatchComponents, 
        MatchType, 
        MatchStatus,
        EvidenceLink
    )


class ExactMatcher:
    """
    Exact matching layer for reconciliation engine.
    
    Criteria:
    - Amount: Exact equality (+-0.01 tolerance for float precision)
    - Date: Within +-1 day (bank posting delays)
    - Merchant: RapidFuzz ratio >= 90%
    
    Expected confidence: >= 0.95
    """
    
    # Tolerance constants
    AMOUNT_TOLERANCE = Decimal('0.01')
    DATE_TOLERANCE_DAYS = 1
    MERCHANT_THRESHOLD = 90.0  # RapidFuzz ratio
    
    def __init__(self):
        self.match_count = 0
        self.reject_count = 0
    
    def _parse_date(self, date_input) -> datetime:
        """
        Parse date from string or datetime object.
        Handles: ISO strings, datetime objects, date objects
        """
        if isinstance(date_input, datetime):
            return date_input
        
        if isinstance(date_input, str):
            # Try ISO format first (2024-03-15 or 2024-03-15T10:30:00)
            try:
                return datetime.fromisoformat(date_input.replace('Z', '+00:00'))
            except ValueError:
                # Try common formats
                formats = [
                    '%Y-%m-%d',
                    '%Y-%m-%d %H:%M:%S',
                    '%m/%d/%Y',
                    '%d/%m/%Y'
                ]
                for fmt in formats:
                    try:
                        return datetime.strptime(date_input, fmt)
                    except ValueError:
                        continue
                raise ValueError(f"Cannot parse date: {date_input}")
        
        # Handle date objects (convert to datetime)
        if hasattr(date_input, 'year'):
            return datetime(date_input.year, date_input.month, date_input.day)
        
        raise TypeError(f"Unsupported date type: {type(date_input)}")
    
    def _parse_amount(self, amount_input) -> Decimal:
        """
        Parse amount from string, float, int, or Decimal.
        """
        if isinstance(amount_input, Decimal):
            return amount_input
        
        if isinstance(amount_input, (int, float)):
            return Decimal(str(amount_input))
        
        if isinstance(amount_input, str):
            # Remove currency symbols and commas
            cleaned = amount_input.replace('$', '').replace(',', '').replace('EUR', '').replace('GBP', '').strip()
            return Decimal(cleaned)
        
        raise TypeError(f"Unsupported amount type: {type(amount_input)}")
    
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
        Attempt exact match between transaction and document.
        
        Args:
            transaction_amount: Decimal, float, int, or string (e.g., "45.67" or "$45.67")
            transaction_date: datetime or ISO string (e.g., "2024-03-15")
            document_amount: Same as transaction_amount
            document_date: Same as transaction_date
        
        Returns:
            TransactionDocumentMatch if criteria met, None otherwise
        """
        
        # Parse inputs (handles both strings and objects)
        tx_amount = self._normalize_amount(self._parse_amount(transaction_amount))
        doc_amount = self._normalize_amount(self._parse_amount(document_amount))
        tx_date = self._parse_date(transaction_date)
        doc_date = self._parse_date(document_date)
        tx_merchant = self._normalize_merchant(transaction_merchant)
        doc_merchant = self._normalize_merchant(document_merchant)
        
        # Calculate component scores
        amount_match = self._calculate_amount_match(tx_amount, doc_amount)
        date_proximity = self._calculate_date_proximity(tx_date, doc_date)
        string_similarity = self._calculate_string_similarity(tx_merchant, doc_merchant)
        
        # Check if meets exact match criteria
        is_exact = (
            amount_match == 1.0 and
            date_proximity == 1.0 and
            string_similarity >= 0.90
        )
        
        if not is_exact:
            self.reject_count += 1
            return None
        
        # Create match record
        self.match_count += 1
        
        match = TransactionDocumentMatch(
            transaction_id=transaction_id,
            document_id=document_id,
            match_type=MatchType.EXACT,
            status=MatchStatus.SUPPORTED,
            reasoning=(
                f"Exact amount (${tx_amount}), "
                f"date within {self.DATE_TOLERANCE_DAYS} day(s), "
                f"merchant similarity {string_similarity:.2f}"
            )
        )
        
        # Set components
        match.components = MatchComponents(
            string_similarity=string_similarity,
            amount_match=amount_match,
            date_proximity=date_proximity,
            document_trust=document_trust_score
        )
        
        # Calculate final confidence
        confidence = match.calculate_confidence()
        
        # Calculate date offset for record
        date_diff = abs((tx_date - doc_date).days)
        match.date_offset_days = date_diff
        
        # Add evidence chain
        match.add_evidence(
            stage="week7_exact_matcher",
            input_hash=f"{transaction_id}:{document_id}",
            output_result=f"EXACT_MATCH: confidence={confidence:.4f}",
            metadata={
                "tx_merchant_raw": transaction_merchant,
                "doc_merchant_raw": document_merchant,
                "tx_merchant_normalized": tx_merchant,
                "doc_merchant_normalized": doc_merchant,
                "amount_match": amount_match,
                "date_proximity": date_proximity,
                "string_similarity": string_similarity
            }
        )
        
        return match
    
    def _normalize_amount(self, amount: Decimal) -> Decimal:
        """Round to 2 decimal places for comparison"""
        return amount.quantize(Decimal('0.01'))
    
    def _normalize_merchant(self, merchant: str) -> str:
        """
        Normalize merchant name for comparison.
        Uses Week 2 normalization patterns.
        """
        if not merchant:
            return ""
        
        # Lowercase
        normalized = merchant.lower()
        
        # Remove common prefixes (Square, Toast, etc.)
        prefixes = ['sq *', 'tst *', 'tse *', 'sp *', 'square ', 'paypal *']
        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):].strip()
        
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        
        return normalized
    
    def _calculate_amount_match(self, tx_amount: Decimal, doc_amount: Decimal) -> float:
        """1.0 if within tolerance, 0.0 otherwise"""
        diff = abs(tx_amount - doc_amount)
        if diff <= self.AMOUNT_TOLERANCE:
            return 1.0
        return 0.0
    
    def _calculate_date_proximity(self, tx_date: datetime, doc_date: datetime) -> float:
        """1.0 if within tolerance days, 0.0 otherwise"""
        # Handle timezone-aware vs naive
        if tx_date.tzinfo is None and doc_date.tzinfo is not None:
            doc_date = doc_date.replace(tzinfo=None)
        elif tx_date.tzinfo is not None and doc_date.tzinfo is None:
            tx_date = tx_date.replace(tzinfo=None)
        
        diff_days = abs((tx_date - doc_date).days)
        
        if diff_days <= self.DATE_TOLERANCE_DAYS:
            return 1.0
        return 0.0
    
    def _calculate_string_similarity(self, tx_merchant: str, doc_merchant: str) -> float:
        """RapidFuzz ratio 0.0-1.0"""
        if not tx_merchant or not doc_merchant:
            return 0.0
        
        ratio = fuzz.ratio(tx_merchant, doc_merchant)
        return ratio / 100.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Return matching statistics"""
        total = self.match_count + self.reject_count
        return {
            "exact_matches": self.match_count,
            "rejected": self.reject_count,
            "total_processed": total,
            "match_rate": self.match_count / total if total > 0 else 0.0
        }


class ExactMatcherBatch:
    """Process multiple transaction-document pairs"""
    
    def __init__(self, matcher: ExactMatcher = None):
        self.matcher = matcher or ExactMatcher()
        self.results: List[TransactionDocumentMatch] = []
    
    def process_pair(self, transaction: Dict, document: Dict) -> Optional[TransactionDocumentMatch]:
        """Process a single transaction-document pair"""
        
        match = self.matcher.match(
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
        
        if match:
            self.results.append(match)
        
        return match
    
    def get_all_matches(self) -> List[TransactionDocumentMatch]:
        return self.results


# Enhanced tests with full reasoning output
if __name__ == "__main__":
    print("=== Exact Matcher Tests ===\n")
    
    matcher = ExactMatcher()
    
    # Test 1: Perfect match with datetime objects
    print("Test 1: Perfect Match (datetime objects)")
    match = matcher.match(
        transaction_id="txn_001",
        transaction_amount=Decimal("45.67"),
        transaction_date=datetime(2024, 3, 15, 10, 30),
        transaction_merchant="SQ * COFFEE SHOP",
        document_id="doc_001",
        document_amount=Decimal("45.67"),
        document_date=datetime(2024, 3, 15, 14, 20),
        document_merchant="Coffee Shop",
        document_trust_score=0.95
    )
    
    if match:
        print(f"[PASS] MATCH: confidence={match.confidence:.4f}")
        print(f"       Reasoning: {match.reasoning}")
        print(f"       Components: {match.components.to_dict()}")
        print(f"       Evidence chain: {len(match.evidence_chain)} links")
        print(f"       Date offset: {match.date_offset_days} day(s)")
    else:
        print("[FAIL] No match")
    
    print()
    
    # Test 2: String inputs (JSON-style)
    print("Test 2: String Inputs (JSON-style)")
    match = matcher.match(
        transaction_id="txn_002",
        transaction_amount="45.67",
        transaction_date="2024-03-15",
        transaction_merchant="SQ * COFFEE SHOP",
        document_id="doc_002",
        document_amount="$45.67",
        document_date="2024-03-15T14:20:00",
        document_merchant="Coffee Shop",
        document_trust_score=0.95
    )
    
    if match:
        print(f"[PASS] MATCH: confidence={match.confidence:.4f}")
        print(f"       Reasoning: {match.reasoning}")
        print(f"       Components: {match.components.to_dict()}")
    else:
        print("[FAIL] No match")
    
    print()
    
    # Test 3: Amount mismatch (show rejection reason)
    print("Test 3: Amount Mismatch (rejection details)")
    tx_amount = Decimal("50.00")
    doc_amount = Decimal("45.67")
    tx_date = datetime(2024, 3, 15)
    doc_date = datetime(2024, 3, 15)
    tx_merchant = "Whole Foods"
    doc_merchant = "Whole Foods Market"
    
    # Calculate what failed
    amount_diff = abs(tx_amount - doc_amount)
    string_sim = fuzz.ratio(tx_merchant.lower(), doc_merchant.lower()) / 100.0
    
    print(f"       Transaction: ${tx_amount} at {tx_merchant} on {tx_date.date()}")
    print(f"       Document:    ${doc_amount} at {doc_merchant} on {doc_date.date()}")
    print(f"       Amount diff: ${amount_diff} (tolerance: $0.01)")
    print(f"       String sim:  {string_sim:.2f} (threshold: 0.90)")
    
    match = matcher.match(
        transaction_id="txn_003",
        transaction_amount=tx_amount,
        transaction_date=tx_date,
        transaction_merchant=tx_merchant,
        document_id="doc_003",
        document_amount=doc_amount,
        document_date=doc_date,
        document_merchant=doc_merchant,
        document_trust_score=0.90
    )
    
    if not match:
        print("[PASS] Correctly rejected")
        print("       Reason: Amount mismatch ($50.00 vs $45.67)")
    else:
        print(f"[FAIL] Unexpected match: {match.confidence:.4f}")
    
    print()
    
    # Stats
    print("=== Statistics ===")
    stats = matcher.get_stats()
    print(f"Matches: {stats['exact_matches']}")
    print(f"Rejected: {stats['rejected']}")
    print(f"Match rate: {stats['match_rate']:.1%}")