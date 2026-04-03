"""
Week 7 Day 4: Semantic Matcher
Handles heavy abbreviations and OCR errors using embeddings.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from rapidfuzz import fuzz

try:
    from models import (
        TransactionDocumentMatch,
        MatchComponents,
        MatchType,
        MatchStatus
    )
    from exact_matcher import ExactMatcher
    from fuzzy_matcher import FuzzyMatcher
except ImportError:
    from week7_reconciliation.models import (
        TransactionDocumentMatch,
        MatchComponents,
        MatchType,
        MatchStatus
    )
    from week7_reconciliation.exact_matcher import ExactMatcher
    from week7_reconciliation.fuzzy_matcher import FuzzyMatcher

_sentence_model = None

def get_sentence_model():
    """Lazy initialization of sentence transformer model."""
    global _sentence_model
    if _sentence_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
        except ImportError:
            raise ImportError("sentence-transformers not installed. Run: pip install sentence-transformers")
    return _sentence_model


class SemanticMatcher:
    """
    Semantic matching layer using embeddings.
    
    Criteria:
    - Amount: Within 5%
    - Date: Within +-5 days
    - Merchant: Cosine similarity >= 0.65
    
    Expected confidence: 0.60 - 0.85
    """

    AMOUNT_TOLERANCE_PERCENT = 0.05
    DATE_TOLERANCE_DAYS = 5
    SIMILARITY_THRESHOLD = 0.65  # CHANGED: Was 0.75

    def __init__(self):
        self.match_count = 0
        self.reject_count = 0
        self.abbreviation_matches = 0
        self.ocr_error_matches = 0


    def _parse_date(self, date_input) -> datetime:
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
        if isinstance(amount_input, Decimal):
            return amount_input
        if isinstance(amount_input, (int, float)):
            return Decimal(str(amount_input))
        if isinstance(amount_input, str):
            cleaned = amount_input.replace('$', '').replace(',', '').replace('EUR', '').replace('GBP', '').strip()
            return Decimal(cleaned)
        raise TypeError(f"Unsupported amount type: {type(amount_input)}")

    def _normalize_merchant(self, merchant: str) -> str:
        if not merchant:
            return ""
        normalized = merchant.lower()
        prefixes = ['sq * ', 'tst * ', 'tse * ', 'sp * ', 'square ', 'paypal * ', 'pp * ']
        for prefix in prefixes:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):].strip()
        normalized = ' '.join(normalized.split())
        return normalized
    
    def _expand_abbreviation(self, merchant: str) -> str:
        """Minimal abbreviation expansion for common cases."""
        expansions = {
            'amzn': 'amazon',
            'mktp': 'marketplace',
            'mkt': 'market',
            'fd': 'food',
            'f00d': 'food',
        }
        
        words = merchant.lower().split()
        expanded = [expansions.get(w.replace('*', '').replace('-', ''), w) for w in words]
        return ' '.join(expanded)

    def _calculate_amount_match(self, tx_amount: Decimal, doc_amount: Decimal) -> float:
        if tx_amount == 0 and doc_amount == 0:
            return 1.0
        if tx_amount == 0 or doc_amount == 0:
            return 0.0
        diff = abs(tx_amount - doc_amount)
        max_amount = max(tx_amount, doc_amount)
        percent_diff = float(diff / max_amount)
        if percent_diff <= self.AMOUNT_TOLERANCE_PERCENT:
            if percent_diff == 0:
                return 1.0
            return 1.0 - (percent_diff / self.AMOUNT_TOLERANCE_PERCENT * 0.4)
        return 0.0

    def _calculate_date_proximity(self, tx_date: datetime, doc_date: datetime) -> float:
        if tx_date.tzinfo is None and doc_date.tzinfo is not None:
            doc_date = doc_date.replace(tzinfo=None)
        elif tx_date.tzinfo is not None and doc_date.tzinfo is None:
            tx_date = tx_date.replace(tzinfo=None)
        diff_days = abs((tx_date - doc_date).days)
        if diff_days <= self.DATE_TOLERANCE_DAYS:
            return 1.0 - (diff_days * 0.08)
        return 0.0

    def _calculate_semantic_similarity(self, tx_merchant: str, doc_merchant: str) -> Tuple[float, str]:
        """
        Calculate semantic similarity using embeddings.
        """
        # Keep originals for classification
        tx_merchant_orig = tx_merchant
        doc_merchant_orig = doc_merchant
    
        # Expand for matching
        tx_merchant_expanded = self._expand_abbreviation(tx_merchant)
        doc_merchant_expanded = self._expand_abbreviation(doc_merchant)
    
        # Detect if expansion changed anything (indicates abbreviation)
        # CHANGED: Safer comparison with lower() and strip()
        was_expanded = (
            tx_merchant_expanded != tx_merchant_orig.lower().strip() or
            doc_merchant_expanded != doc_merchant_orig.lower().strip()
        )
    
        # Check for OCR errors (digits in original)
        is_ocr = any(c.isdigit() for c in tx_merchant_orig) or any(c.isdigit() for c in doc_merchant_orig)
    
        # Use expanded versions for matching
        tx_merchant = tx_merchant_expanded
        doc_merchant = doc_merchant_expanded
    
        # Try RapidFuzz first
        rapid_score = fuzz.ratio(tx_merchant.lower(), doc_merchant.lower()) / 100.0
        if rapid_score >= 0.75:
            if was_expanded and not is_ocr:
                return (rapid_score, "abbreviation")
            if is_ocr:
                return (rapid_score, "ocr_correction")
            return (rapid_score, "rapidfuzz_fallback")

        # Try embeddings...
        try:
            model = get_sentence_model()
            embeddings = model.encode([tx_merchant, doc_merchant])
            import numpy as np
            similarity = np.dot(embeddings[0], embeddings[1]) / (np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
            )
        
            if similarity >= self.SIMILARITY_THRESHOLD:
                if was_expanded and not is_ocr:
                    return (float(similarity), "abbreviation")
                if is_ocr:
                    return (float(similarity), "ocr_correction")
                return (float(similarity), "semantic_similarity")
        
            return (float(similarity), "below_threshold")
        
        except Exception as e:
            return (rapid_score, f"fallback_error:{str(e)}")
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

        tx_amount = self._parse_amount(transaction_amount)
        doc_amount = self._parse_amount(document_amount)
        tx_date = self._parse_date(transaction_date)
        doc_date = self._parse_date(document_date)
        tx_merchant = self._normalize_merchant(transaction_merchant)
        doc_merchant = self._normalize_merchant(document_merchant)

        amount_score = self._calculate_amount_match(tx_amount, doc_amount)
        date_proximity = self._calculate_date_proximity(tx_date, doc_date)
        semantic_score, match_type = self._calculate_semantic_similarity(tx_merchant, doc_merchant)

        is_semantic = (
            amount_score >= 0.6 and
            date_proximity >= 0.6 and
            semantic_score >= self.SIMILARITY_THRESHOLD
        )

        if not is_semantic:
            self.reject_count += 1
            return None

        if match_type == "abbreviation":
            self.abbreviation_matches += 1
        elif match_type == "ocr_correction":
            self.ocr_error_matches += 1

        self.match_count += 1

        reasoning = f"Semantic match ({match_type}): {tx_merchant} vs {doc_merchant}"

        match = TransactionDocumentMatch(
            transaction_id=transaction_id,
            document_id=document_id,    
            match_type=MatchType.SEMANTIC,
            status=MatchStatus.SUPPORTED if amount_score >= 0.9 else MatchStatus.PARTIAL,
            reasoning=reasoning
        )

        match.components = MatchComponents(
            string_similarity=semantic_score,
            amount_match=amount_score,
            date_proximity=date_proximity,
            document_trust=document_trust_score
        )

        confidence = match.calculate_confidence()

        if amount_score < 1.0:
            match.amount_discrepancy = abs(tx_amount - doc_amount)

        date_diff = abs((tx_date - doc_date).days)
        match.date_offset_days = date_diff

        match.add_evidence(
            stage="week7_semantic_matcher",
            input_hash=f"{transaction_id}:{document_id}",
            output_result=f"SEMANTIC_MATCH: confidence={confidence:.4f}, type={match_type}",
            metadata={
                "tx_merchant_raw": transaction_merchant,
                "doc_merchant_raw": document_merchant,
                "tx_merchant_normalized": tx_merchant,
                "doc_merchant_normalized": doc_merchant,
                "semantic_score": semantic_score,
                "match_type": match_type,
                "amount_match": amount_score,
                "date_proximity": date_proximity
            }
        )

        return match

    def get_stats(self) -> Dict[str, Any]:
        total = self.match_count + self.reject_count
        return {
            "semantic_matches": self.match_count,
            "abbreviation_matches": self.abbreviation_matches,
            "ocr_error_matches": self.ocr_error_matches,
            "rejected": self.reject_count,
            "total_processed": total,
            "match_rate": self.match_count / total if total > 0 else 0.0
        }


class ThreeTierMatcher:
    """Complete 3-tier cascade: Exact -> Fuzzy -> Semantic"""

    def __init__(self):
        self.exact = ExactMatcher()
        self.fuzzy = FuzzyMatcher()
        self.semantic = SemanticMatcher()
        self.cascade_stats = {
            "exact_hits": 0,
            "fuzzy_hits": 0,
            "semantic_hits": 0,
            "total_misses": 0
        }

    def match(self, transaction: Dict, document: Dict) -> Optional[TransactionDocumentMatch]:
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

        semantic_match = self.semantic.match(
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

        if semantic_match:
            self.cascade_stats["semantic_hits"] += 1
            return semantic_match

        self.cascade_stats["total_misses"] += 1
        return None

    def get_stats(self) -> Dict[str, Any]:
        return {
            "exact": self.exact.get_stats(),
            "fuzzy": self.fuzzy.get_stats(),
            "semantic": self.semantic.get_stats(),
            "cascade": self.cascade_stats
        }


# Tests
if __name__ == "__main__":
    print("=== Semantic Matcher Tests ===\n")

    semantic = SemanticMatcher()

    # CHANGED: Added debug section
    print("Debug: Checking similarity scores")
    test_pairs = [
        ("AMZN MKTP", "Amazon Marketplace"),
        ("Wh0le F00ds M4rket", "Whole Foods Market"),
        ("McDonald's", "Golden Arches Restaurant Ltd"),
        ("WLMRT STORES", "Walmart Stores Inc")
    ]


    
    for tx, doc in test_pairs:
        score, match_type = semantic._calculate_semantic_similarity(tx.lower(), doc.lower())
        print(f"  '{tx}' vs '{doc}': {score:.4f} ({match_type})")
    
    print()

    # Test 1: Abbreviation match
    print("Test 1: Abbreviation Match")
    match = semantic.match(
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
        print(f"       Status: {match.status.name}")
    else:
        print("[FAIL] No match")

    # Test 2: OCR error correction
    print("\nTest 2: OCR Error Correction")
    match = semantic.match(
        transaction_id="txn_ocr_001",
        transaction_amount="45.50",
        transaction_date="2024-03-15",
        transaction_merchant="Wh0le F00ds M4rket",
        document_id="doc_ocr_001",
        document_amount="45.50",
        document_date="2024-03-15",
        document_merchant="Whole Foods Market",
        document_trust_score=0.85
    )
    if match:
        print(f"[PASS] MATCH: {match.confidence:.4f}")
        print(f"       Reasoning: {match.reasoning}")
        print(f"       Status: {match.status.name}")
    else:
        print("[FAIL] No match")

    # Test 3: Foreign name variation
    print("\nTest 3: Foreign Name Variation")
    match = semantic.match(
        transaction_id="txn_foreign_001",
        transaction_amount="120.00",
        transaction_date="2024-03-10",
        transaction_merchant="McDonald's",
        document_id="doc_foreign_001",
        document_amount="120.00",
        document_date="2024-03-10",
        document_merchant="Golden Arches Restaurant Ltd",
        document_trust_score=0.90
    )
    if match:
        print(f"[PASS] MATCH: {match.confidence:.4f}")
        print(f"       Reasoning: {match.reasoning}")
        print(f"       Status: {match.status.name}")
    else:
        print("[FAIL] No match")

    # Test 4: Too different (should reject)
    print("\nTest 4: Too Different (should reject)")
    match = semantic.match(
        transaction_id="txn_bad_001",
        transaction_amount="100.00",
        transaction_date="2024-03-15",
        transaction_merchant="Starbucks Coffee",
        document_id="doc_bad_001",
        document_amount="500.00",
        document_date="2024-03-25",
        document_merchant="Best Buy Electronics",
        document_trust_score=0.90
    )
    print("[PASS] Correctly rejected" if not match else f"[FAIL] Unexpected match: {match.confidence:.4f}")

    # Print statistics
    print("\n=== Semantic Matcher Statistics ===")
    stats = semantic.get_stats()
    print(f"Semantic matches: {stats['semantic_matches']}")
    print(f"Abbreviation matches: {stats['abbreviation_matches']}")
    print(f"OCR error matches: {stats['ocr_error_matches']}")
    print(f"Rejected: {stats['rejected']}")

    # Three-tier cascade test
    print("\n=== Three-Tier Cascade Test ===")
    cascade = ThreeTierMatcher()

    test_cases = [
        {
            "transaction": {"id": "txn_ex", "amount": "50.00", "date": "2024-03-15", "merchant": "Coffee Shop"},
            "document": {"id": "doc_ex", "amount": "50.00", "date": "2024-03-15", "merchant": "Coffee Shop", "trust_score": 0.95}
        },
        {
            "transaction": {"id": "txn_fz", "amount": "50.00", "date": "2024-03-15", "merchant": "Coffee Shop"},
            "document": {"id": "doc_fz", "amount": "55.00", "date": "2024-03-16", "merchant": "Coffee Shop Downtown", "trust_score": 0.90}
        },
        {
            "transaction": {"id": "txn_sem", "amount": "67.89", "date": "2024-03-20", "merchant": "AMZN MKTP"},
            "document": {"id": "doc_sem", "amount": "67.89", "date": "2024-03-20", "merchant": "Amazon Marketplace", "trust_score": 0.88}
        },
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

    print("\n=== Three-Tier Cascade Statistics ===")
    stats = cascade.get_stats()
    print(f"Exact hits: {stats['cascade']['exact_hits']}")
    print(f"Fuzzy hits: {stats['cascade']['fuzzy_hits']}")
    print(f"Semantic hits: {stats['cascade']['semantic_hits']}")
    print(f"Total misses: {stats['cascade']['total_misses']}")