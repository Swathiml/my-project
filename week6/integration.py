import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from typing import List, Optional
import uuid

from week4_document_pipeline.week4_pipeline import Week4Pipeline
from week4_document_pipeline.document_pipeline import Pipeline as Week5Pipeline, Transaction
from week4_document_pipeline.extractors.receipt_extractor import ReceiptExtractor
from week4_document_pipeline.extractors.statement_extractor import StatementExtractor
from week4_document_pipeline.extractors.invoice_extractor import InvoiceExtractor
from week4_document_pipeline.evidence_chain import EvidenceChainBuilder

from week6.trust_scorer import DocumentTrustScorer
from week6.duplicate_detector import DuplicateDetector
from week6.partial_matcher import PartialMatchFlagger


class EnhancedPipeline:
    """
    Integrated pipeline with validation, trust scoring, and duplicate detection.
    """
    
    def __init__(self, week4_pipeline: Optional[Week4Pipeline] = None, 
                 week5_pipeline: Optional[Week5Pipeline] = None):
        self.preprocessor = week4_pipeline or Week4Pipeline()
        self.base_pipeline = week5_pipeline or Week5Pipeline()
        
        self.trust_scorer = DocumentTrustScorer()
        self.duplicate_detector = DuplicateDetector()
        self.partial_matcher = PartialMatchFlagger()
        
        self.receipt_extractor = ReceiptExtractor()
        self.statement_extractor = StatementExtractor()
        self.invoice_extractor = InvoiceExtractor()
        
        self.evidence = EvidenceChainBuilder(confidence_threshold=0.6)
    
    def process_document(self, image_path: str) -> List[Transaction]:
        """Full pipeline: preprocess -> validate -> extract -> score."""
        transactions = []
        
        print(f"\nProcessing: {os.path.basename(image_path)}")
        
        # Preprocessing
        prep_result = self.preprocessor.process_document(image_path)
        
        if prep_result.get('status') != 'success':
            print(f"  Failed: {prep_result.get('error', 'Unknown error')}")
            return []
        
        doc_type = prep_result.get('type', 'unknown')
        raw_text = prep_result.get('ocr', {}).get('raw_text', '')
        
        print(f"  Type: {doc_type} (confidence: {prep_result.get('classification_confidence', 0):.2f})")
        print(f"  Image quality: {prep_result.get('quality_score', 0):.2f}")
        
        # Use raw image quality, not trust score
        image_quality = prep_result.get('quality_score', 0.0)
        
        # Duplicate detection
        if self.duplicate_detector.is_duplicate(image_path, raw_text):
            print(f"  Duplicate detected - skipping")
            return []
        
        # Fallback for unknown type instead of skip
        if doc_type == 'unknown':
            print(f"  Warning: Low confidence type detection, using receipt fallback")
            doc_type = 'receipt'
        
        # Extraction
        facts = None
        extractor_name = ""
        
        if doc_type == 'receipt':
            facts = self.receipt_extractor.extract(raw_text)
            extractor_name = "receipt_extractor"
        elif doc_type == 'statement':
            facts = self.statement_extractor.extract(raw_text)
            extractor_name = "statement_extractor"
        elif doc_type == 'invoice':
            facts = self.invoice_extractor.extract(raw_text)
            extractor_name = "invoice_extractor"
        else:
            print(f"  Unknown document type: {doc_type}")
            return []
        
        if not facts:
            print(f"  Extraction failed")
            return []
        
        # Trust scoring
        trust_result = self.trust_scorer.calculate_trust(prep_result, facts, doc_type)
        trust_score = trust_result['trust_score']
        trust_status = trust_result['status']
        
        print(f"  Trust score: {trust_score:.3f} ({trust_status})")
        print(f"    Image: {trust_result['breakdown']['image_quality']:.2f}, "
              f"OCR: {trust_result['breakdown']['ocr_confidence']:.2f}, "
              f"Fields: {trust_result['breakdown']['extraction_completeness']:.2f}, "
              f"Consistency: {trust_result['breakdown']['consistency_checks']:.2f}")
        
        # Partial match flagging
        partial_flags = self.partial_matcher.flag(facts, raw_text)
        
        if partial_flags['partial_match_eligible']:
            print(f"  Flagged: {partial_flags['reason']} "
                  f"(tolerance: {partial_flags['suggested_tolerance']*100:.0f}%)")
        
        # Build transaction
        ocr_conf = prep_result.get('ocr', {}).get('confidence', 0.0)
        extraction_conf = getattr(facts, 'extraction_confidence', 0.5)
        doc_id = prep_result.get('document_id', str(uuid.uuid4()))
        
        if doc_type == 'statement':
            return self._process_statement_transactions(
                facts, prep_result, trust_result, partial_flags, doc_id
            )
        
        # Determine fields based on type
        if doc_type == 'receipt':
            amount = getattr(facts, 'total_amount', None)
            date = getattr(facts, 'date', None)
            merchant = getattr(facts, 'merchant', None)
        else:  # invoice
            amount = getattr(facts, 'total_due', None)
            date = getattr(facts, 'invoice_date', None)
            merchant = getattr(facts, 'vendor', None)
        
        if amount is None or date is None:
            print(f"  Missing required fields")
            return []
        
        #Use image_quality for quality_score, trust_score for confidence
        chain = self.evidence.build_chain(
            fact_type=doc_type,
            value={"merchant": merchant, "amount": amount, "date": date},
            source_doc=doc_id,
            ocr_conf=ocr_conf,
            extraction_conf=extraction_conf,
            quality_score=image_quality,  
            raw_text=raw_text,
            extractor_name=extractor_name,
            metadata={
                "partial_match_eligible": partial_flags['partial_match_eligible'],
                "partial_match_reason": partial_flags['reason'],
                "trust_breakdown": trust_result['breakdown']
            }
        )
        
        chain.status = trust_status
        
        txn = Transaction(
            id=str(uuid.uuid4()),
            merchant=merchant,
            amount=amount,
            date=date,
            category=None,
            category_confidence=None,
            source_doc={"id": doc_id, "type": doc_type},
            confidence=trust_score,  # Trust score is final confidence
            status=trust_status
        )
        
        txn.partial_match_eligible = partial_flags['partial_match_eligible']
        txn.suggested_tolerance = partial_flags['suggested_tolerance']
        
        transactions.append(txn)
        print(f"  Created: {txn.id[:8]}... (status: {trust_status})")
        
        return transactions
    
    def _process_statement_transactions(self, facts, prep_result, trust_result, 
                                        partial_flags, doc_id) -> List[Transaction]:
        """Handle statement with multiple transactions."""
        transactions = []
        raw_text = prep_result.get('ocr', {}).get('raw_text', '')
        ocr_conf = prep_result.get('ocr', {}).get('confidence', 0.0)
        trust_score = trust_result['trust_score']
        trust_status = trust_result['status']
        image_quality = prep_result.get('quality_score', 0.0)  
        
        statement_trans = getattr(facts, 'transactions', [])
        
        # Warn if no transactions found
        if not statement_trans:
            print(f"  Warning: No transactions found in statement")
            print(f"    Raw text preview: {raw_text[:200]}...")
            return []
        
        print(f"  Statement with {len(statement_trans)} transactions")
        
        for stmt_txn in statement_trans:
            chain = self.evidence.build_chain(
                fact_type='statement_transaction',
                value={"desc": stmt_txn.description, "amount": stmt_txn.amount},
                source_doc=doc_id,
                ocr_conf=ocr_conf,
                extraction_conf=getattr(facts, 'extraction_confidence', 0.5),
                quality_score=image_quality,  
                raw_text=raw_text,
                extractor_name='statement_extractor',
                metadata={"statement_transaction": True}
            )
            chain.status = trust_status
            
            merchant = " ".join(stmt_txn.description.split()[:2]) if stmt_txn.description else "Unknown"
            
            txn = Transaction(
                id=str(uuid.uuid4()),
                merchant=merchant,
                amount=stmt_txn.amount,
                date=stmt_txn.date,
                category=None,
                category_confidence=None,
                source_doc={"id": doc_id, "type": "statement"},
                confidence=trust_score,
                status=trust_status
            )
            
            transactions.append(txn)
        
        print(f"  Created {len(transactions)} transactions")
        return transactions
    
    def get_summary(self) -> dict:
        """Get processing summary."""
        chains = self.evidence.chains
        
        return {
            "total_documents": len(set(c.evidence.source_document for c in chains)),
            "total_facts": len(chains),
            "by_status": {
                "verified": len([c for c in chains if c.status == "verified"]),
                "low_confidence": len([c for c in chains if c.status == "low_confidence"]),
                "manual_review": len([c for c in chains if c.status == "manual_review"])
            },
            "duplicates_prevented": len(self.duplicate_detector.seen_hashes) - len(chains)
        }


if __name__ == "__main__":
    from week4_document_pipeline.synthetic_generator import SyntheticDocumentGenerator
    print("=" * 60)
    print("INTEGRATION TEST")
    print("=" * 60)
    
    gen = SyntheticDocumentGenerator("test_integration")
    
    test_docs = [
        ("Clean Receipt", gen.generate_receipt(1, None)),
        ("Blurred Receipt", gen.generate_receipt(2, {'blur': 2})),
        ("Statement", gen.generate_statement(3, None)),
        ("Invoice", gen.generate_invoice(4, None)),
    ]
    
    pipeline = EnhancedPipeline()
    all_transactions = []
    
    for name, path in test_docs:
        print(f"\n{'='*60}")
        print(f"Test: {name}")
        print(f"{'='*60}")
        txns = pipeline.process_document(path)
        all_transactions.extend(txns)
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    summary = pipeline.get_summary()
    print(f"Total transactions: {len(all_transactions)}")
    print(f"Documents processed: {summary['total_documents']}")
    print(f"Status breakdown:")
    for status, count in summary['by_status'].items():
        print(f"  {status}: {count}")
    print(f"Duplicates prevented: {summary['duplicates_prevented']}")