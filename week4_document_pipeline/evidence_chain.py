from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import json


@dataclass
class Evidence:
    source_document: str  # document UUID
    ocr_confidence: float  # from Tesseract
    extraction_confidence: float  # from your extractor
    document_quality: float  # from quality scorer
    raw_text_snippet: str  # the raw text that produced this fact
    extraction_method: str  # "receipt_extractor", "statement_extractor", etc.
    
    @property
    def composite_confidence(self) -> float:
        """Calculate overall confidence score."""
        return round(
            self.ocr_confidence * 
            self.extraction_confidence * 
            self.document_quality, 
            4
        )


@dataclass
class Fact:
    fact_type: str  # "transaction", "merchant", "date", "amount", etc.
    value: Any  # the extracted value
    metadata: Dict = field(default_factory=dict)  # extra context
    
    def to_dict(self) -> Dict:
        return {
            "type": self.fact_type,
            "value": self.value,
            "metadata": self.metadata
        }


@dataclass
class EvidenceChain:
    fact: Fact
    evidence: Evidence
    status: str  # "verified", "low_confidence", "manual_review", "failed"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "fact": self.fact.to_dict(),
            "evidence": {
                "source_document": self.evidence.source_document,
                "ocr_confidence": self.evidence.ocr_confidence,
                "extraction_confidence": self.evidence.extraction_confidence,
                "document_quality": self.evidence.document_quality,
                "composite_confidence": self.evidence.composite_confidence,
                "raw_text_snippet": self.evidence.raw_text_snippet[:200],  # truncate
                "extraction_method": self.evidence.extraction_method
            },
            "status": self.status,
            "timestamp": self.timestamp
        }


class EvidenceChainBuilder:
    def __init__(self, confidence_threshold: float = 0.7):
        self.confidence_threshold = confidence_threshold
        self.chains: List[EvidenceChain] = []
    
    def build_chain(
        self,
        fact_type: str,
        value: Any,
        source_doc: str,
        ocr_conf: float,
        extraction_conf: float,
        quality_score: float,
        raw_text: str,
        extractor_name: str,
        metadata: Optional[Dict] = None
    ) -> EvidenceChain:
        """Build an evidence chain for a single fact."""
        
        fact = Fact(fact_type=fact_type, value=value, metadata=metadata or {})
        
        evidence = Evidence(
            source_document=source_doc,
            ocr_confidence=ocr_conf,
            extraction_confidence=extraction_conf,
            document_quality=quality_score,
            raw_text_snippet=raw_text,
            extraction_method=extractor_name
        )
        
        # Determine status based on composite confidence
        composite = evidence.composite_confidence
        if composite >= self.confidence_threshold:
            status = "verified"
        elif composite >= 0.5:
            status = "low_confidence"
        else:
            status = "manual_review"
        
        chain = EvidenceChain(fact=fact, evidence=evidence, status=status)
        self.chains.append(chain)
        
        return chain
    
    def get_chains_by_status(self, status: str) -> List[EvidenceChain]:
        """Get all chains with a specific status."""
        return [c for c in self.chains if c.status == status]
    
    def get_low_confidence_facts(self) -> List[EvidenceChain]:
        """Get facts that need manual review."""
        return self.get_chains_by_status("manual_review") + \
               self.get_chains_by_status("low_confidence")
    
    def export_report(self, filepath: str):
        """Export all evidence chains to JSON."""
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_facts": len(self.chains),
            "verified": len(self.get_chains_by_status("verified")),
            "low_confidence": len(self.get_chains_by_status("low_confidence")),
            "manual_review": len(self.get_chains_by_status("manual_review")),
            "chains": [c.to_dict() for c in self.chains]
        }
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report


# Integration helper for your extractors
class DocumentProcessor:
    """Connects OCR + Extractor + Evidence Chain."""
    
    def __init__(self, ocr_engine, quality_scorer, confidence_threshold=0.7):
        self.ocr_engine = ocr_engine  # your Tesseract wrapper
        self.quality_scorer = quality_scorer  # document quality checker
        self.chain_builder = EvidenceChainBuilder(confidence_threshold)
    
    def process_document(self, image_path: str, doc_type: str) -> List[EvidenceChain]:
        """
        Full pipeline: Image → OCR → Extract → Evidence Chain.
        
        Args:
            image_path: path to document image
            doc_type: "receipt", "statement", or "invoice"
        """
        # Step 1: OCR
        ocr_result = self.ocr_engine.extract(image_path)
        raw_text = ocr_result.text
        ocr_conf = ocr_result.confidence  # character-level confidence
        
        # Step 2: Document quality
        quality_score = self.quality_scorer.score(raw_text, image_path)
        
        # Step 3: Extract based on document type
        if doc_type == "receipt":
            from extractors.receipt_extractor import ReceiptExtractor
            extractor = ReceiptExtractor()
            facts = extractor.extract(raw_text)
            extractor_name = "receipt_extractor"
            
            # Build chains for each fact
            chains = []
            
            # Merchant
            if facts.merchant:
                chains.append(self.chain_builder.build_chain(
                    fact_type="merchant",
                    value=facts.merchant,
                    source_doc=image_path,
                    ocr_conf=ocr_conf,
                    extraction_conf=facts.extraction_confidence,
                    quality_score=quality_score,
                    raw_text=raw_text,
                    extractor_name=extractor_name,
                    metadata={"field": "merchant"}
                ))
            
            # Date
            if facts.date:
                chains.append(self.chain_builder.build_chain(
                    fact_type="date",
                    value=facts.date,
                    source_doc=image_path,
                    ocr_conf=ocr_conf,
                    extraction_conf=facts.extraction_confidence,
                    quality_score=quality_score,
                    raw_text=raw_text,
                    extractor_name=extractor_name,
                    metadata={"field": "transaction_date"}
                ))
            
            # Total amount
            if facts.total_amount:
                chains.append(self.chain_builder.build_chain(
                    fact_type="amount",
                    value=facts.total_amount,
                    source_doc=image_path,
                    ocr_conf=ocr_conf,
                    extraction_conf=facts.extraction_confidence,
                    quality_score=quality_score,
                    raw_text=raw_text,
                    extractor_name=extractor_name,
                    metadata={"field": "total_amount", "currency": "USD"}
                ))
            
            # Items count
            if facts.items:
                chains.append(self.chain_builder.build_chain(
                    fact_type="item_count",
                    value=len(facts.items),
                    source_doc=image_path,
                    ocr_conf=ocr_conf,
                    extraction_conf=facts.extraction_confidence,
                    quality_score=quality_score,
                    raw_text=raw_text,
                    extractor_name=extractor_name,
                    metadata={"field": "items", "details": [i.name for i in facts.items]}
                ))
            
            return chains
        
        # TODO: Add statement and invoice processing similarly
        
        return []


if __name__ == "__main__":
    # Test without OCR (using your existing test data)
    builder = EvidenceChainBuilder(confidence_threshold=0.7)
    
    # Simulate a receipt extraction
    sample_receipt = """
    TRADER JOE'S #8839
    Date: 02/07/2026
    TOTAL: $39.12
    """
    
    # Build evidence chains for each fact
    merchant_chain = builder.build_chain(
        fact_type="merchant",
        value="Trader Joe's",
        source_doc="receipt_001.jpg",
        ocr_conf=0.95,
        extraction_conf=0.94,
        quality_score=0.92,
        raw_text=sample_receipt,
        extractor_name="receipt_extractor",
        metadata={"location": "store_8839"}
    )
    
    date_chain = builder.build_chain(
        fact_type="date",
        value="2026-02-07",
        source_doc="receipt_001.jpg",
        ocr_conf=0.95,
        extraction_conf=0.98,
        quality_score=0.92,
        raw_text=sample_receipt,
        extractor_name="receipt_extractor"
    )
    
    amount_chain = builder.build_chain(
        fact_type="amount",
        value=39.12,
        source_doc="receipt_001.jpg",
        ocr_conf=0.95,
        extraction_conf=0.96,
        quality_score=0.92,
        raw_text=sample_receipt,
        extractor_name="receipt_extractor",
        metadata={"currency": "USD"}
    )
    
    # Print results
    print("Evidence Chains Built:")
    for chain in builder.chains:
        print(f"\n  Fact: {chain.fact.fact_type} = {chain.fact.value}")
        print(f"  Composite Confidence: {chain.evidence.composite_confidence}")
        print(f"  Status: {chain.status}")
        print(f"  Source: {chain.evidence.source_document}")
    
    # Check for low confidence
    low_conf = builder.get_low_confidence_facts()
    print(f"\n\nLow Confidence Facts: {len(low_conf)}")
    
    # Export report
    report = builder.export_report("evidence_report.json")
    print(f"\nReport exported: {report['verified']} verified, {report['low_confidence']} low confidence")