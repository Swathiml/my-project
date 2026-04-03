"""
Week 7 Day 5: Mismatch Handler
Categorizes unmatched transactions and documents with transparency markers.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Any
from datetime import datetime

try:
    from models import (
        TransactionDocumentMatch,
        MatchType,
        MatchStatus,
    )
except ImportError:
    from week7_reconciliation.models import (
        TransactionDocumentMatch,
        MatchType,
        MatchStatus,
    )


@dataclass
class UnmatchedTransaction:
    """A transaction with no supporting document."""
    transaction_id: str
    amount: float
    date: str
    merchant: str
    label: str = "Card transaction"
    reason: str = "no_document_found"
    category: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "transaction_id": self.transaction_id,
            "amount": self.amount,
            "date": self.date,
            "merchant": self.merchant,
            "label": self.label,
            "reason": self.reason,
            "category": self.category,
            "status": "UNSUPPORTED"
        }


@dataclass
class UnreconciledDocument:
    """A document with no matching transaction."""
    document_id: str
    amount: Optional[float]
    date: Optional[str]
    merchant: Optional[str]
    doc_type: str = "receipt"
    label: str = "Possible cash purchase"
    reason: str = "no_transaction_found"
    trust_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "document_id": self.document_id,
            "amount": self.amount,
            "date": self.date,
            "merchant": self.merchant,
            "doc_type": self.doc_type,
            "label": self.label,
            "reason": self.reason,
            "trust_score": self.trust_score,
            "status": "UNRECONCILED"
        }


class MismatchHandler:
    """
    Identifies and categorizes unmatched items after reconciliation.
    
    Categories:
    - SUPPORTED:    Transaction with matching document (confidence >= 0.6)
    - UNSUPPORTED:  Transaction without document -> "Card transaction"
    - UNRECONCILED: Document without transaction -> "Possible cash purchase"
    """

    CONFIDENCE_THRESHOLD = 0.6

    def __init__(self):
        self.unsupported: List[UnmatchedTransaction] = []
        self.unreconciled: List[UnreconciledDocument] = []

    def classify(
        self,
        all_transactions: List[Dict],
        all_documents: List[Dict],
        matches: List[TransactionDocumentMatch]
    ) -> Dict[str, Any]:
        """
        Classify all items into SUPPORTED / UNSUPPORTED / UNRECONCILED.
        """
        self.unsupported.clear()
        self.unreconciled.clear()

        # Build sets of matched IDs (only high-confidence matches = supported)
        matched_tx_ids: Set[str] = set()
        matched_doc_ids: Set[str] = set()
        supported_matches: List[TransactionDocumentMatch] = []

        for match in matches:
            if match.confidence >= self.CONFIDENCE_THRESHOLD:
                matched_tx_ids.add(match.transaction_id)
                if match.document_id:
                    matched_doc_ids.add(match.document_id)
                supported_matches.append(match)

        # Find unsupported transactions
        for tx in all_transactions:
            if tx["id"] not in matched_tx_ids:
                reason = self._classify_unsupported_reason(tx)
                label = self._get_unsupported_label(tx)

                self.unsupported.append(UnmatchedTransaction(
                    transaction_id=tx["id"],
                    amount=float(tx.get("amount", 0)),
                    date=str(tx.get("date", "")),
                    merchant=tx.get("merchant", "Unknown"),
                    label=label,
                    reason=reason,
                    category=tx.get("category"),
                    metadata={"original_tx": tx}
                ))

        # Find unreconciled documents
        for doc in all_documents:
            if doc["id"] not in matched_doc_ids:
                reason = self._classify_unreconciled_reason(doc)
                label = self._get_unreconciled_label(doc)

                # Handle amount=0.0 correctly (0.0 is valid, None is missing)
                amount_val = doc.get("amount")
                amount = float(amount_val) if amount_val is not None else None

                self.unreconciled.append(UnreconciledDocument(
                    document_id=doc["id"],
                    amount=amount,
                    date=str(doc.get("date", "")) if doc.get("date") else None,
                    merchant=doc.get("merchant"),
                    doc_type=doc.get("doc_type", "receipt"),
                    label=label,
                    reason=reason,
                    trust_score=float(doc.get("trust_score", 0.0)),
                    metadata={"original_doc": doc}
                ))

        return {
            "supported": supported_matches,
            "unsupported": self.unsupported,
            "unreconciled": self.unreconciled,
            "summary": self._build_summary(supported_matches, matches)
        }

    def _classify_unsupported_reason(self, tx: Dict) -> str:
        """Determine WHY a transaction has no document."""
        merchant = str(tx.get("merchant", "")).lower()
        category = str(tx.get("category", "")).lower()

        if any(k in merchant for k in ["amazon", "uber", "netflix", "spotify", "paypal", "apple"]):
            return "digital_purchase_no_receipt"
        if category in ["subscriptions", "utilities", "rent"]:
            return "recurring_payment_no_receipt"
        if category == "income":
            return "income_deposit"
        if category in ["transfer", "fees", "atm"]:
            return "transfer_or_fee"
        if "atm" in merchant or "cash" in merchant:
            return "cash_withdrawal"

        return "no_document_found"

    def _classify_unreconciled_reason(self, doc: Dict) -> str:
        """Determine WHY a document has no matching transaction."""
        trust = float(doc.get("trust_score", 0))

        if trust < 0.5:
            return "low_trust_document"
        if trust >= 0.8:
            return "likely_cash_purchase"
        if doc.get("doc_type") == "invoice":
            return "unpaid_invoice"

        return "no_transaction_found"

    def _get_unsupported_label(self, tx: Dict) -> str:
        """Human-readable label for unsupported transaction."""
        category = str(tx.get("category", "")).lower()
        merchant = str(tx.get("merchant", "")).lower()

        if category == "income":
            return "Direct deposit"
        if category in ["transfer", "fees"]:
            return "Bank transfer or fee"
        if "atm" in merchant or "cash" in merchant:
            return "Cash withdrawal"
        if any(k in merchant for k in ["netflix", "spotify", "adobe", "github", "apple"]):
            return "Digital subscription"
        if any(k in merchant for k in ["amazon", "uber", "paypal", "doordash"]):
            return "Online purchase"
        return "Card transaction"

    def _get_unreconciled_label(self, doc: Dict) -> str:
        """Human-readable label for unreconciled document."""
        doc_type = str(doc.get("doc_type", "receipt"))
        trust = float(doc.get("trust_score", 0))

        if doc_type == "invoice":
            return "Unpaid invoice"
        if doc_type == "statement":
            return "Unmatched statement"
        if trust < 0.5:
            return "Unverified document"
        return "Possible cash purchase"

    def _build_summary(
        self,
        supported: List[TransactionDocumentMatch],
        all_matches: List[TransactionDocumentMatch]
    ) -> Dict[str, Any]:
        """Build summary statistics."""
        low_conf_matches = [m for m in all_matches if m.confidence < self.CONFIDENCE_THRESHOLD]

        return {
            "total_supported": len(supported),
            "total_unsupported": len(self.unsupported),
            "total_unreconciled": len(self.unreconciled),
            "low_confidence_matches": len(low_conf_matches),
            "unsupported_reasons": self._count_reasons(self.unsupported),
            "unreconciled_reasons": self._count_reasons(self.unreconciled),
        }

    def _count_reasons(self, items: List) -> Dict[str, int]:
        """Count occurrences of each reason."""
        counts: Dict[str, int] = {}
        for item in items:
            counts[item.reason] = counts.get(item.reason, 0) + 1
        return counts

    def get_transparency_markers(self) -> List[Dict]:
        """
        Produce story-ready transparency markers for Week 10 generator.
        """
        markers = []

        for tx in self.unsupported:
            markers.append({
                "type": "unsupported_spending",
                "transaction_id": tx.transaction_id,
                "amount": tx.amount,
                "merchant": tx.merchant,
                "date": tx.date,
                "user_label": tx.label,
                "story_note": f"${tx.amount:.2f} at {tx.merchant} — no receipt found"
            })

        for doc in self.unreconciled:
            if doc.amount is not None:
                story_note = (
                    f"Receipt from {doc.merchant or 'unknown merchant'} "
                    f"(${doc.amount:.2f}) — no matching bank transaction"
                )
            else:
                story_note = (
                    f"Receipt from {doc.merchant or 'unknown'} "
                    f"— no matching bank transaction"
                )

            markers.append({
                "type": "unreconciled_receipt",
                "document_id": doc.document_id,
                "amount": doc.amount,
                "merchant": doc.merchant,
                "date": doc.date,
                "user_label": doc.label,
                "story_note": story_note
            })

        return markers


# Tests
if __name__ == "__main__":
    print("=== Mismatch Handler Tests ===\n")

    transactions = [
        {"id": "txn_001", "amount": 45.67, "date": "2026-01-15",
         "merchant": "Whole Foods", "category": "groceries"},
        {"id": "txn_002", "amount": 15.99, "date": "2026-01-16",
         "merchant": "Netflix", "category": "subscriptions"},
        {"id": "txn_003", "amount": 2500.0, "date": "2026-01-14",
         "merchant": "Direct Deposit", "category": "income"},
        {"id": "txn_004", "amount": 89.50, "date": "2026-01-20",
         "merchant": "Shell Oil", "category": "transportation"},
        {"id": "txn_005", "amount": 34.20, "date": "2026-01-22",
         "merchant": "Trader Joe's", "category": "groceries"},
        {"id": "txn_006", "amount": 0.0, "date": "2026-01-25",  # Edge case
         "merchant": "Free Sample Store", "category": "other"},
    ]

    documents = [
        {"id": "doc_001", "amount": 45.67, "date": "2026-01-15",
         "merchant": "Whole Foods Market", "doc_type": "receipt", "trust_score": 0.91},
        {"id": "doc_002", "amount": 34.20, "date": "2026-01-22",
         "merchant": "Trader Joe's", "doc_type": "receipt", "trust_score": 0.88},
        {"id": "doc_003", "amount": 22.00, "date": "2026-01-18",
         "merchant": "Coffee Shop", "doc_type": "receipt", "trust_score": 0.75},
        {"id": "doc_004", "amount": 0.0, "date": "2026-01-10",
         "merchant": "Blurry Receipt", "doc_type": "receipt", "trust_score": 0.35},
        {"id": "doc_005", "amount": None, "date": "2026-01-12",  # Missing amount
         "merchant": "Unknown", "doc_type": "receipt", "trust_score": 0.40},
    ]

    # Create mock matches (only txn_001 and txn_005 are supported)
    def make_match(tx_id, doc_id, conf):
        m = TransactionDocumentMatch(
            transaction_id=tx_id,
            document_id=doc_id,
            match_type=MatchType.EXACT,
            status=MatchStatus.SUPPORTED,
            confidence=conf
        )
        return m

    matches = [
        make_match("txn_001", "doc_001", 0.96),
        make_match("txn_005", "doc_002", 0.93),
    ]

    handler = MismatchHandler()
    result = handler.classify(transactions, documents, matches)

    print("Classification Results:")
    print(f"  Supported:    {result['summary']['total_supported']}")
    print(f"  Unsupported:  {result['summary']['total_unsupported']}")
    print(f"  Unreconciled: {result['summary']['total_unreconciled']}")

    print("\nUnsupported transactions:")
    for tx in result["unsupported"]:
        print(f"  {tx.transaction_id}: {tx.label} (${tx.amount:.2f}) — {tx.reason}")

    print("\nUnreconciled documents:")
    for doc in result["unreconciled"]:
        amount_str = f"${doc.amount:.2f}" if doc.amount is not None else "unknown amount"
        print(f"  {doc.document_id}: {doc.label} ({amount_str}) — {doc.reason}")

    print("\nTransparency markers:")
    for m in handler.get_transparency_markers():
        print(f"  [{m['type']}] {m['story_note']}")

    print("\nSummary statistics:")
    print(f"  Unsupported reasons: {result['summary']['unsupported_reasons']}")
    print(f"  Unreconciled reasons: {result['summary']['unreconciled_reasons']}")
    print(f"  Low confidence matches: {result['summary']['low_confidence_matches']}")