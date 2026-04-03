import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import uuid
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from week4_document_pipeline.extractors.receipt_extractor import ReceiptExtractor
from week4_document_pipeline.extractors.statement_extractor import StatementExtractor
from week4_document_pipeline.extractors.invoice_extractor import InvoiceExtractor
from week4_document_pipeline.evidence_chain import EvidenceChainBuilder
from week4_document_pipeline.ocr_engine import OCREngine, OCRResult


@dataclass
class Transaction:
    id: str
    merchant: Optional[str]
    amount: float
    date: str
    category: Optional[str] = None
    category_confidence: Optional[float] = None
    source_doc: Dict = field(default_factory=dict)
    confidence: float = 0.0
    status: str = "verified"


class Pipeline:
    def __init__(self, categorizer=None, threshold: float = 0.5):
        self.receipt_extractor = ReceiptExtractor()
        self.statement_extractor = StatementExtractor()
        self.invoice_extractor = InvoiceExtractor()
        self.ocr = OCREngine()
        self.evidence = EvidenceChainBuilder(threshold)
        self.categorizer = categorizer
        self.threshold = threshold
    
    def _detect_transaction_type(self, merchant: str, description: str) -> str:
        """Detect if transaction is income, expense, or transfer."""
        text = f"{merchant or ''} {description or ''}".lower().strip()
        
        income_keywords = [
            "payroll", "deposit", "salary", "refund",
            "direct deposit", "payment received", "interest"
        ]
        transfer_keywords = ["transfer", "atm", "withdrawal", "move money"]
        expense_keywords = [
            "store", "restaurant", "cafe", "fuel", "grocery",
            "shop", "market", "food", "yogurt", "oil", "shell",
            "consulting", "software", "services", "license"
        ]
        
        if any(k in text for k in income_keywords):
            return "income"
        if any(k in text for k in transfer_keywords):
            return "transfer"
        if any(k in text for k in expense_keywords):
            return "expense"
        return "expense"
    
    def _categorize(self, merchant, description, amount):
        if self.categorizer:
            txn_type = self._detect_transaction_type(merchant, description)
            
            if txn_type == "expense":
                amount = -abs(amount)
            elif txn_type == "income":
                amount = abs(amount)
            
            return self.categorizer.categorize(
                merchant or "Unknown",
                description,
                amount
            )
        
        # Mock fallback
        text = f"{merchant} {description}".lower()
        keywords = {
            "food": ["grocery", "restaurant", "cafe", "food", "trader", "yogurt"],
            "transport": ["gas", "uber", "shell", "fuel", "oil"],
            "income": ["payroll", "deposit", "salary"],
            "business": ["consulting", "software", "services", "license"]
        }
        for cat, words in keywords.items():
            if any(w in text for w in words):
                return {"category": cat, "confidence": 0.75}
        return {"category": "other", "confidence": 0.5}
    
    def _compute_confidence(self, evidence_conf: float, cat_conf: float) -> float:
        """Weighted confidence: evidence quality + categorization reliability."""
        return round((0.6 * evidence_conf) + (0.4 * cat_conf), 4)
    
    def _compute_status(self, composite_conf: float, cat_conf: float, evidence_conf: float) -> str:
        """
        Multi-factor validation for production robustness.
        All three signals must be healthy for auto-verification.
        """
        if cat_conf < 0.25:
            return "manual_review"
        if evidence_conf < 0.4:
            return "manual_review"
        if composite_conf >= 0.6:
            return "verified"
        elif composite_conf >= 0.45:
            return "low_confidence"
        return "manual_review"
    
    def process_receipt(self, text: str, ocr_conf: float = 0.0, doc_id: Optional[str] = None) -> List[Transaction]:
        if doc_id is None:
            doc_id = str(uuid.uuid4())
        
        facts = self.receipt_extractor.extract(text)
        results = []
        
        if not (facts.total_amount and facts.date):
            return results
        
        actual_ocr_conf = ocr_conf if ocr_conf > 0 else 0.95
        
        chain = self.evidence.build_chain(
            fact_type="receipt",
            value={"merchant": facts.merchant, "amount": facts.total_amount},
            source_doc=doc_id,
            ocr_conf=actual_ocr_conf,
            extraction_conf=facts.extraction_confidence,
            quality_score=0.92,
            raw_text=text,
            extractor_name="receipt",
            metadata={"items": len(facts.items)}
        )
        
        # Use item names for rich categorization signal
        item_text = " ".join([i.name for i in facts.items[:3]]) if facts.items else ""
        cat = self._categorize(facts.merchant, item_text, facts.total_amount)
        
        evidence_conf = chain.evidence.composite_confidence
        cat_conf = cat.get('confidence', 0.5)
        final_conf = self._compute_confidence(evidence_conf, cat_conf)
        status = self._compute_status(final_conf, cat_conf, evidence_conf)
        
        txn = Transaction(
            id=str(uuid.uuid4()),
            merchant=facts.merchant,
            amount=facts.total_amount,
            date=facts.date,
            category=cat.get('category'),
            category_confidence=cat_conf,
            source_doc={"id": doc_id, "type": "receipt"},
            confidence=final_conf,
            status=status
        )
        
        chain.status = status
        results.append(txn)
        return results
    
    def process_statement(self, text: str, ocr_conf: float = 0.0, doc_id: Optional[str] = None) -> List[Transaction]:
        if doc_id is None:
            doc_id = str(uuid.uuid4())
        
        facts = self.statement_extractor.extract(text)
        results = []
        
        for trans in facts.transactions:
            actual_ocr_conf = ocr_conf if ocr_conf > 0 else 0.93
            
            chain = self.evidence.build_chain(
                fact_type="statement",
                value={"desc": trans.description, "amount": trans.amount},
                source_doc=doc_id,
                ocr_conf=actual_ocr_conf,
                extraction_conf=facts.extraction_confidence,
                quality_score=0.90,
                raw_text=text,
                extractor_name="statement",
                metadata={"type": trans.transaction_type}
            )
            
            merchant = " ".join(trans.description.split()[:2]) if trans.description else None
            cat = self._categorize(merchant, trans.description, trans.amount)
            
            evidence_conf = chain.evidence.composite_confidence
            cat_conf = cat.get('confidence', 0.5)
            final_conf = self._compute_confidence(evidence_conf, cat_conf)
            status = self._compute_status(final_conf, cat_conf, evidence_conf)
            
            txn = Transaction(
                id=str(uuid.uuid4()),
                merchant=merchant,
                amount=trans.amount,
                date=trans.date,
                category=cat.get('category'),
                category_confidence=cat_conf,
                source_doc={"id": doc_id, "type": "statement"},
                confidence=final_conf,
                status=status
            )
            
            chain.status = status
            results.append(txn)
        
        return results
    
    def process_invoice(self, text: str, ocr_conf: float = 0.0, doc_id: Optional[str] = None) -> List[Transaction]:
        """Process invoice with line-item rich categorization."""
        if doc_id is None:
            doc_id = str(uuid.uuid4())
        
        facts = self.invoice_extractor.extract(text)
        results = []
        
        if not (facts.total_due and facts.invoice_date):
            return results
        
        actual_ocr_conf = ocr_conf if ocr_conf > 0 else 0.94
        
        chain = self.evidence.build_chain(
            fact_type="invoice",
            value={
                "vendor": facts.vendor,
                "client": facts.client,
                "amount": facts.total_due,
                "invoice_number": facts.invoice_number
            },
            source_doc=doc_id,
            ocr_conf=actual_ocr_conf,
            extraction_conf=facts.extraction_confidence,
            quality_score=0.91,
            raw_text=text,
            extractor_name="invoice",
            metadata={
                "line_items": len(facts.line_items),
                "subtotal": facts.subtotal,
                "tax": facts.tax
            }
        )
        
        # Use item.description (not item.name) for rich categorization signal
        item_text = " ".join([item.description for item in facts.line_items[:3]]) if facts.line_items else ""
        desc = f"Invoice from {facts.vendor}: {item_text}" if item_text else f"Invoice from {facts.vendor}"
        
        cat = self._categorize(facts.vendor, desc, -abs(facts.total_due))
        
        evidence_conf = chain.evidence.composite_confidence
        cat_conf = cat.get('confidence', 0.5)
        final_conf = self._compute_confidence(evidence_conf, cat_conf)
        status = self._compute_status(final_conf, cat_conf, evidence_conf)
        
        txn = Transaction(
            id=str(uuid.uuid4()),
            merchant=facts.vendor,
            amount=facts.total_due,
            date=facts.invoice_date,
            category=cat.get('category'),
            category_confidence=cat_conf,
            source_doc={"id": doc_id, "type": "invoice"},
            confidence=final_conf,
            status=status
        )
        
        # Set chain status (verify persistence in evidence_chain.py if needed)
        chain.status = status
        results.append(txn)
        return results
    
    def process_document(self, image_path: str, doc_type: str) -> List[Transaction]:
        """Unified entry point: image → OCR → extraction → categorization."""
        if doc_type not in ["receipt", "statement", "invoice"]:
            raise ValueError(f"Unknown doc_type: {doc_type}")
        
        ocr_result: OCRResult = self.ocr.extract_simple(image_path, doc_type)
        
        if not ocr_result.text:
            return []
        
        if doc_type == "receipt":
            return self.process_receipt(ocr_result.text, ocr_result.confidence)
        elif doc_type == "statement":
            return self.process_statement(ocr_result.text, ocr_result.confidence)
        else:
            return self.process_invoice(ocr_result.text, ocr_result.confidence)
    
    def report(self, file: str = "data/week6_evidence_report.json"):
        chains = self.evidence.chains
    
        data = {
            "docs": len(set(c.evidence.source_document for c in chains)),
            "facts": len(chains),
            "verified": len([c for c in chains if c.status == "verified"]),
            "low_confidence": len([c for c in chains if c.status == "low_confidence"]),
            "manual_review": len([c for c in chains if c.status == "manual_review"]),
            "chains": [c.to_dict() for c in chains]
        }

        os.makedirs(os.path.dirname(file), exist_ok=True)

        with open(file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Saved report to: {file}")
        return data


if __name__ == "__main__":
    try:
        from week2.pipeline import TransactionPipeline
        cat = TransactionPipeline()
        print("Using real TransactionPipeline")
    except ImportError:
        cat = None
        print("Using mock categorizer")
    
    pipe = Pipeline(categorizer=cat, threshold=0.5)
    
    print("\n" + "=" * 60)
    print("RECEIPT")
    print("=" * 60)
    
    receipt_text = """
    TRADER JOE'S #8839
    Date: 02/07/2026
    3x Greek Yogurt $14.97
    1x Avocados 4pk $5.99
    Subtotal: $36.91
    Tax 6.00%: $2.21
    TOTAL: $39.12
    Paid: DEBIT
    """
    
    for t in pipe.process_receipt(receipt_text, ocr_conf=0.96):
        print(f"\nID: {t.id}")
        print(f"  Merchant: {t.merchant}")
        print(f"  Amount: ${t.amount}")
        print(f"  Date: {t.date}")
        print(f"  Category: {t.category} (cat_conf: {t.category_confidence})")
        print(f"  Items: {[i.name for i in pipe.receipt_extractor.extract(receipt_text).items]}")  # FIX 3: Show items
        print(f"  Composite: {t.confidence} | Status: {t.status}")
    
    print("\n" + "=" * 60)
    print("STATEMENT")
    print("=" * 60)
    
    statement_text = """
    JOHN DOE
    Statement Period: 01/01/2026 to 01/31/2026
    
    01/05/2026 GROCERY STORE #1234 45.67 7,654.33
    01/15/2026 PAYROLL DEPOSIT 2,500.00 8,501.68
    01/20/2026 SHELL OIL 48.50 8,296.90
    
    Ending Balance: $8,206.91
    """
    
    for t in pipe.process_statement(statement_text, ocr_conf=0.94):
        print(f"\nID: {t.id}")
        print(f"  Merchant: {t.merchant}")
        print(f"  Amount: ${t.amount}")
        print(f"  Date: {t.date}")
        print(f"  Category: {t.category} (cat_conf: {t.category_confidence})")
        print(f"  Composite: {t.confidence} | Status: {t.status}")
    
    print("\n" + "=" * 60)
    print("INVOICE (with line-item signal)")
    print("=" * 60)
    
    invoice_text = """
    Tech Solutions LLC
    
    Invoice #: INV-2026-001234
    Date: 02/15/2026
    Due Date: 03/17/2026
    
    Bill To: Client Corp
    
    Consulting Services | 10 | $150.00 | $1,500.00
    Software License | 5 | $200.00 | $1,000.00
    
    Subtotal: $2,500.00
    Tax (8%): $200.00
    Total Due: $2,700.00
    """
    
    for t in pipe.process_invoice(invoice_text, ocr_conf=0.95):
        print(f"\nID: {t.id}")
        print(f"  Vendor: {t.merchant}")
        print(f"  Amount: ${t.amount}")
        print(f"  Date: {t.date}")
        print(f"  Category: {t.category} (cat_conf: {t.category_confidence})")
        print(f"  Line Items: {[i.description for i in pipe.invoice_extractor.extract(invoice_text).line_items]}")  # FIX 3: Show line items
        print(f"  Composite: {t.confidence} | Status: {t.status}")
    
    report = pipe.report()
    print(f"\n{'=' * 60}")
    print("REPORT")
    print(f"{'=' * 60}")
    print(f"Documents: {report['docs']}")
    print(f"Total Facts: {report['facts']}")
    print(f"Verified: {report['verified']}")
    print(f"Low Confidence: {report['low_confidence']}")
    print(f"Manual Review: {report['manual_review']}")