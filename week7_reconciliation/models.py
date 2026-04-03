"""
Week 7 Day 1: Data Models & Schema
Transaction ↔ Document Reconciliation Engine
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum, auto
from typing import List, Optional, Dict, Any
from uuid import uuid4


class MatchType(Enum):
    EXACT = auto()      # Amount + Date + Merchant all match precisely
    FUZZY = auto()      # Within tolerances (tips, posting delays)
    SEMANTIC = auto()   # Embedding-based match for abbreviations/OCR errors
    NONE = auto()       # No match found


class MatchStatus(Enum):
    SUPPORTED = auto()       # Transaction has matching document
    UNSUPPORTED = auto()      # Transaction without document
    UNRECONCILED = auto()    # Document without transaction
    PARTIAL = auto()         # Match with discrepancies (tips, refunds)


@dataclass
class MatchComponents:
    """Breakdown of confidence calculation for explainability"""
    string_similarity: float = 0.0   # Merchant name match (0.0-1.0)
    amount_match: float = 0.0        # Amount similarity (0.0-1.0)
    date_proximity: float = 0.0      # Date closeness (0.0-1.0)
    document_trust: float = 0.0      # From Week 6 quality score (0.0-1.0)
    
    def to_dict(self) -> Dict[str, float]:
        return {
            'string_similarity': round(self.string_similarity, 4),
            'amount_match': round(self.amount_match, 4),
            'date_proximity': round(self.date_proximity, 4),
            'document_trust': round(self.document_trust, 4)
        }


@dataclass
class EvidenceLink:
    """Traceable link in the evidence chain (Week 1 requirement)"""
    stage: str                          # e.g., "week2_normalization"
    input_hash: str                     # Verification fingerprint
    output_result: str                  # What this stage produced
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TransactionDocumentMatch:
    """
    Core reconciliation record linking transaction to document
    with full provenance for explainability
    """
    # Identifiers
    match_id: str = field(default_factory=lambda: str(uuid4()))
    transaction_id: str = ""
    document_id: Optional[str] = None
    
    # Match classification
    match_type: MatchType = MatchType.NONE
    status: MatchStatus = MatchStatus.UNSUPPORTED
    confidence: float = 0.0  # 0.0-1.0 composite score
    
    # Component breakdown (for explainability)
    components: MatchComponents = field(default_factory=MatchComponents)
    
    # Match details
    amount_discrepancy: Optional[Decimal] = None  # For partial matches (tips)
    date_offset_days: int = 0  # Days between transaction and document
    
    # Evidence chain (Week 1 requirement: transaction_id + document_id + confidence)
    evidence_chain: List[EvidenceLink] = field(default_factory=list)
    
    # Human-readable reasoning for final demo
    reasoning: str = ""
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: Optional[datetime] = None
    
    def calculate_confidence(self) -> float:
        """Weighted aggregation per Week 7 specification"""
        weights = {
            'string_similarity': 0.4,
            'amount_match': 0.3,
            'date_proximity': 0.2,
            'document_trust': 0.1
        }
        
        self.confidence = (
            self.components.string_similarity * weights['string_similarity'] +
            self.components.amount_match * weights['amount_match'] +
            self.components.date_proximity * weights['date_proximity'] +
            self.components.document_trust * weights['document_trust']
        )
        return self.confidence
    
    def add_evidence(self, stage: str, input_hash: str, 
                     output_result: str, metadata: Dict = None):
        """Add traceable evidence link"""
        self.evidence_chain.append(EvidenceLink(
            stage=stage,
            input_hash=input_hash,
            output_result=output_result,
            metadata=metadata or {}
        ))
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialization for API/database storage"""
        return {
            'match_id': self.match_id,
            'transaction_id': self.transaction_id,
            'document_id': self.document_id,
            'match_type': self.match_type.name,
            'status': self.status.name,
            'confidence': round(self.confidence, 4),
            'components': self.components.to_dict(),
            'amount_discrepancy': str(self.amount_discrepancy) if self.amount_discrepancy else None,
            'date_offset_days': self.date_offset_days,
            'reasoning': self.reasoning,
            'evidence_count': len(self.evidence_chain),
            'created_at': self.created_at.isoformat()
        }


@dataclass
class ReconciliationResult:
    """Container for batch reconciliation output"""
    matches: List[TransactionDocumentMatch] = field(default_factory=list)
    unsupported_transactions: List[str] = field(default_factory=list)
    unreconciled_documents: List[str] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    
    def generate_stats(self):
        """Summary for monitoring and debugging"""
        total = len(self.matches)
        if total == 0:
            self.statistics = {}
            return
        
        self.statistics = {
            'total_matches': total,
            'exact_matches': sum(1 for m in self.matches if m.match_type == MatchType.EXACT),
            'fuzzy_matches': sum(1 for m in self.matches if m.match_type == MatchType.FUZZY),
            'semantic_matches': sum(1 for m in self.matches if m.match_type == MatchType.SEMANTIC),
            'average_confidence': sum(m.confidence for m in self.matches) / total,
            'unsupported_count': len(self.unsupported_transactions),
            'unreconciled_count': len(self.unreconciled_documents)
        }
        return self.statistics


# Example usage / test
if __name__ == "__main__":
    # Create a sample match
    match = TransactionDocumentMatch(
        transaction_id="txn_001",
        document_id="doc_abc_123",
        match_type=MatchType.EXACT,
        status=MatchStatus.SUPPORTED,
        reasoning="Exact amount, date within 1 day, merchant similarity 0.95"
    )
    
    # Set components
    match.components = MatchComponents(
        string_similarity=0.95,
        amount_match=1.0,
        date_proximity=1.0,
        document_trust=0.89
    )
    
    # Calculate confidence
    match.calculate_confidence()
    
    # Add evidence chain
    match.add_evidence(
        stage="week2_normalization",
        input_hash="SQ * COFFEE SHOP",
        output_result="coffee_shop",
        metadata={"method": "rapidfuzz"}
    )
    match.add_evidence(
        stage="week6_validation",
        input_hash="receipt_img_001",
        output_result="quality_score: 0.89",
        metadata={"blur_check": "passed"}
    )
    
    print("Match Record:")
    print(match.to_dict())
    print(f"\nConfidence: {match.confidence:.4f}")
    print(f"Evidence chain length: {len(match.evidence_chain)}")