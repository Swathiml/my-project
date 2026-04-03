"""
Week 7 Day 6: Reconciliation Engine Integration
Combines all matchers and mismatch handler into unified pipeline.
Includes CSV input and JSON export for Week 12 demo readiness.
"""

import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional, Set

try:
    from models import TransactionDocumentMatch, MatchType, MatchStatus
    from exact_matcher import ExactMatcher
    from fuzzy_matcher import FuzzyMatcher
    from semantic_matcher import SemanticMatcher
    from mismatch_handler import MismatchHandler
except ImportError:
    from week7_reconciliation.models import TransactionDocumentMatch, MatchType, MatchStatus
    from week7_reconciliation.exact_matcher import ExactMatcher
    from week7_reconciliation.fuzzy_matcher import FuzzyMatcher
    from week7_reconciliation.semantic_matcher import SemanticMatcher
    from week7_reconciliation.mismatch_handler import MismatchHandler


class ReconciliationEngine:
    """
    Complete Week 7 reconciliation pipeline.
    Includes CSV input and JSON export for full project integration.
    """

    def __init__(self, confidence_threshold: float = 0.6):
        self.exact_matcher = ExactMatcher()
        self.fuzzy_matcher = FuzzyMatcher()
        self.semantic_matcher = SemanticMatcher()
        self.mismatch_handler = MismatchHandler()
        self.confidence_threshold = confidence_threshold
        self.statistics = {
            "total_processed": 0,
            "exact_matches": 0,
            "fuzzy_matches": 0,
            "semantic_matches": 0,
            "unsupported": 0,
            "unreconciled": 0,
            "failed": 0
        }

    def reconcile(
        self,
        transactions: List[Dict],
        documents: List[Dict]
    ) -> Dict[str, Any]:
        """
        Main entry point: reconcile transactions with documents.
        """
        start_time = time.time()
        matches: List[TransactionDocumentMatch] = []
        matched_doc_ids: Set[str] = set()

        for tx in transactions:
            available_docs = [d for d in documents if d["id"] not in matched_doc_ids]
            best_match = self._find_best_match(tx, available_docs)
            
            if best_match and best_match.confidence >= self.confidence_threshold:
                matches.append(best_match)
                matched_doc_ids.add(best_match.document_id)
                self._update_match_stats(best_match.match_type)

        result = self.mismatch_handler.classify(transactions, documents, matches)
        
        elapsed = time.time() - start_time
        self.statistics["total_processed"] = len(transactions) + len(documents)
        self.statistics["unsupported"] = len(result["unsupported"])
        self.statistics["unreconciled"] = len(result["unreconciled"])
        
        return {
            "matches": matches,
            "supported": result["supported"],
            "unsupported": result["unsupported"],
            "unreconciled": result["unreconciled"],
            "statistics": self._build_final_stats(result, elapsed),
            "evidence_chains": self._extract_evidence_chains(matches),
            "transparency_markers": self.mismatch_handler.get_transparency_markers()
        }

    def _find_best_match(
        self,
        transaction: Dict,
        documents: List[Dict]
    ) -> Optional[TransactionDocumentMatch]:
        """
        Find highest confidence match across all documents and all matchers.
        """
        tx_id = transaction["id"]
        best_match = None
        best_conf = 0.0

        for doc in documents:
            for matcher in [self.exact_matcher, self.fuzzy_matcher, self.semantic_matcher]:
                match = matcher.match(
                    transaction_id=tx_id,
                    transaction_amount=transaction["amount"],
                    transaction_date=transaction["date"],
                    transaction_merchant=transaction["merchant"],
                    document_id=doc["id"],
                    document_amount=doc["amount"],
                    document_date=doc["date"],
                    document_merchant=doc["merchant"],
                    document_trust_score=doc.get("trust_score", 1.0)
                )
                if match and match.confidence > best_conf:
                    best_match = match
                    best_conf = match.confidence

        return best_match

    def reconcile_from_csv(
        self,
        transactions_csv: str,
        documents: List[Dict],
        output_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Load transactions from Week 2 CSV and run reconciliation.
        
        Args:
            transactions_csv: Path to CSV file with transactions
            documents: List of document dicts from Week 6
            output_file: Optional path to save JSON report
        """
        import pandas as pd

        df = pd.read_csv(transactions_csv)

        transactions = []
        for idx, row in df.iterrows():
            transactions.append({
                "id": str(row.get("transaction_id", f"txn_{idx}")),
                "amount": str(abs(float(row.get("amount", 0)))),
                "date": str(row.get("date", "")),
                "merchant": str(row.get("merchant_canonical", 
                                        row.get("merchant_raw", "Unknown"))),
                "category": str(row.get("category", "")),
            })

        result = self.reconcile(transactions, documents)

        if output_file:
            self.export(result, output_file)

        return result

    def export(self, result: Dict[str, Any], filepath: str):
        """
        Save full reconciliation result to JSON.
        """
        import os
        os.makedirs(os.path.dirname(filepath), exist_ok=True) if os.path.dirname(filepath) else None

        # Convert matches to serializable format
        serializable_matches = []
        for match in result["matches"]:
            match_dict = {
                "match_id": match.match_id,
                "transaction_id": match.transaction_id,
                "document_id": match.document_id,
                "match_type": match.match_type.name,
                "confidence": match.confidence,
                "status": match.status.name,
                "reasoning": match.reasoning,
                "components": match.components.to_dict() if match.components else {},
                "evidence_count": len(match.evidence_chain),
                "date_offset_days": match.date_offset_days,
                "amount_discrepancy": str(match.amount_discrepancy) if match.amount_discrepancy else None
            }
            serializable_matches.append(match_dict)

        data = {
            "generated_at": datetime.now().isoformat(),
            "statistics": result["statistics"],
            "matches": serializable_matches,
            "unsupported": [u.to_dict() for u in result["unsupported"]],
            "unreconciled": [d.to_dict() for d in result["unreconciled"]],
            "transparency_markers": result["transparency_markers"]
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        print(f"Reconciliation report saved: {filepath}")

    def _update_match_stats(self, match_type: MatchType):
        """Update internal statistics based on match type."""
        if match_type == MatchType.EXACT:
            self.statistics["exact_matches"] += 1
        elif match_type == MatchType.FUZZY:
            self.statistics["fuzzy_matches"] += 1
        elif match_type == MatchType.SEMANTIC:
            self.statistics["semantic_matches"] += 1

    def _build_final_stats(self, handler_result: Dict, elapsed: float) -> Dict[str, Any]:
        """Build comprehensive statistics."""
        total_tx = len(handler_result["supported"]) + len(handler_result["unsupported"])
        
        return {
            "pipeline": self.statistics,
            "elapsed_seconds": round(elapsed, 3),
            "match_rate": len(handler_result["supported"]) / total_tx if total_tx else 0.0,
            "coverage": {
                "transaction_coverage": len(handler_result["supported"]) / max(total_tx, 1),
                "document_coverage": len(handler_result["supported"]) / max(
                    len(handler_result["supported"]) + len(handler_result["unreconciled"]), 1)
            }
        }

    def _extract_evidence_chains(self, matches: List[TransactionDocumentMatch]) -> List[Dict]:
        """Extract evidence chains for explainability."""
        chains = []
        for match in matches:
            chain = {
                "match_id": match.match_id,
                "transaction_id": match.transaction_id,
                "document_id": match.document_id,
                "confidence": match.confidence,
                "components": match.components.to_dict() if match.components else {},
                "evidence_count": len(match.evidence_chain),
                "stages": [link.stage for link in match.evidence_chain]
            }
            chains.append(chain)
        return chains


# Tests
if __name__ == "__main__":
    print("=== Reconciliation Engine Integration Tests ===\n")

    transactions = [
        {"id": "txn_001", "amount": "45.67", "date": "2024-03-15", "merchant": "SQ * COFFEE SHOP", "category": "dining"},
        {"id": "txn_002", "amount": "120.00", "date": "2024-03-15", "merchant": "Whole Foods", "category": "groceries"},
        {"id": "txn_003", "amount": "55.00", "date": "2024-03-16", "merchant": "John's Coffee", "category": "dining"},
        {"id": "txn_004", "amount": "67.89", "date": "2024-03-20", "merchant": "AMZN MKTP", "category": "shopping"},
    ]

    documents = [
        {"id": "doc_001", "amount": "45.67", "date": "2024-03-15", "merchant": "Coffee Shop", "trust_score": 0.95},
        {"id": "doc_002", "amount": "120.00", "date": "2024-03-15", "merchant": "Whole Foods Market", "trust_score": 0.90},
        {"id": "doc_003", "amount": "50.00", "date": "2024-03-16", "merchant": "John's Coffee Shop", "trust_score": 0.88},
        {"id": "doc_004", "amount": "67.89", "date": "2024-03-20", "merchant": "Amazon Marketplace", "trust_score": 0.85},
    ]

    engine = ReconciliationEngine(confidence_threshold=0.6)
    result = engine.reconcile(transactions, documents)

    print("Match Results:")
    for match in result["matches"]:
        print(f"  {match.transaction_id} -> {match.document_id}: {match.match_type.name} (confidence: {match.confidence:.4f})")

    print(f"\nSupported: {len(result['supported'])}")
    print(f"Unsupported: {len(result['unsupported'])}")
    print(f"Unreconciled: {len(result['unreconciled'])}")

    print("\nPipeline Statistics:")
    stats = result["statistics"]
    print(f"  Exact matches: {stats['pipeline']['exact_matches']}")
    print(f"  Fuzzy matches: {stats['pipeline']['fuzzy_matches']}")
    print(f"  Semantic matches: {stats['pipeline']['semantic_matches']}")
    print(f"  Elapsed: {stats['elapsed_seconds']:.3f}s")

    # Test JSON export
    engine.export(result, "data/week7_reconciliation_report.json")
    print(f"\nExported to: data/week7_reconciliation_report.json")

   