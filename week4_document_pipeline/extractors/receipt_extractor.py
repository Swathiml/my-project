import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ReceiptItem:
    quantity: int
    name: str
    price: float


@dataclass
class ReceiptFacts:
    merchant: Optional[str]
    date: Optional[str]
    total_amount: Optional[float]
    subtotal: Optional[float]
    tax: Optional[float]
    tax_rate: Optional[float]
    items: List[ReceiptItem]
    payment_method: Optional[str]
    extraction_confidence: float


def normalize_ocr_text(raw_text: str) -> str:
    """
    Fix common OCR artifacts before extraction.
    """
    # Fix merged quantity: "3xGreek" → "3x Greek"
    raw_text = re.sub(r'(\d)x([A-Za-z])', r'\1x \2', raw_text)
    
    # Fix broken decimals: "39 12" → "39.12" (when followed by end of amount)
    raw_text = re.sub(r'(\d)\s(\d{2})(?=\s|$|\n)', r'\1.\2', raw_text)
    
    return raw_text.strip()


class ReceiptExtractor:
    def __init__(self):
        self.patterns = {
            'amount': r'\$?(\d{1,3}(?:,\d{3})*\.\d{2})',
            'date_slash': r'(\d{1,2})/(\d{1,2})/(\d{2,4})',
            'date_dash': r'(\d{1,2})-(\d{1,2})-(\d{2,4})',
            'date_iso': r'(\d{4})-(\d{2})-(\d{2})',
        }
        
        self.strong_indicators = ['total', 'subtotal', 'tax', 'date', 'trans', 'store']
        self.medium_indicators = ['thank', 'paid', 'payment', 'cash', 'credit', 'debit']
    
    def extract(self, raw_text: str) -> ReceiptFacts:
        # Normalize OCR text first
        raw_text = normalize_ocr_text(raw_text)

        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
        
        merchant = self._extract_merchant(lines)
        date = self._extract_date(lines, raw_text)
        total_amount = self._extract_total(raw_text)
        subtotal = self._extract_subtotal(raw_text)
        tax, tax_rate = self._extract_tax(raw_text)
        items = self._extract_items(raw_text)
        payment_method = self._extract_payment_method(raw_text)
        
        confidence = self._calculate_confidence(
            merchant, date, total_amount, subtotal, tax, items, raw_text
        )
        
        return ReceiptFacts(
            merchant=merchant,
            date=date,
            total_amount=total_amount,
            subtotal=subtotal,
            tax=tax,
            tax_rate=tax_rate,
            items=items,
            payment_method=payment_method,
            extraction_confidence=confidence
        )
    
    def _extract_merchant(self, lines: List[str]) -> Optional[str]:
        skip_words = [
            'receipt', 'invoice', 'statement', 'date', 'time', 'trans',
            'welcome', 'thank', 'customer', 'copy', 'store'
        ]
        
        for line in lines[:5]:
            line_clean = line.strip()
            
            if not line_clean:
                continue
            
            lower_line = line_clean.lower()
            
            if any(skip in lower_line for skip in skip_words):
                continue
            
            # Remove store numbers like "#8839"
            merchant = re.sub(r'#\d+', '', line_clean).strip()
            
            # Skip if too short or just numbers
            if len(merchant) < 3 or merchant.isdigit():
                continue
            
            # Prefer lines that contain mostly letters (business names)
            letter_ratio = sum(c.isalpha() for c in merchant) / max(len(merchant), 1)
            
            if letter_ratio > 0.6:
                return merchant.title().replace("'S", "'s")
        
        return None
    
    def _extract_date(self, lines: List[str], raw_text: str) -> Optional[str]:
        patterns = [
            (self.patterns['date_slash'], lambda m: (m.group(3), m.group(1), m.group(2))),
            (self.patterns['date_dash'], lambda m: (m.group(3), m.group(1), m.group(2))),
            (self.patterns['date_iso'], lambda m: (m.group(1), m.group(2), m.group(3))),
        ]
        
        for pattern, extractor in patterns:
            match = re.search(pattern, raw_text)
            if match:
                year, month, day = extractor(match)
                
                if len(year) == 2:
                    year_int = int(year)
                    if year_int >= 50:
                        year = '19' + year
                    else:
                        year = '20' + year
                
                try:
                    dt = datetime(int(year), int(month), int(day))
                    return dt.strftime('%Y-%m-%d')
                except ValueError:
                    continue
        
        return None
    
    def _extract_total(self, raw_text: str) -> Optional[float]:
        patterns = [
            r'\bTOTAL\b[:\s]*\$?([\d,]+\.\d{2})',
            r'GRAND\s+TOTAL[:\s]*\$?([\d,]+\.\d{2})',
            r'AMOUNT\s+DUE[:\s]*\$?([\d,]+\.\d{2})',
            r'BALANCE\s+DUE[:\s]*\$?([\d,]+\.\d{2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, raw_text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                return float(amount_str)
        
        # fallback: largest amount
        amounts = re.findall(self.patterns['amount'], raw_text)
        if amounts:
            clean_amounts = [float(a.replace(',', '')) for a in amounts]
            return max(clean_amounts)
        
        return None
    
    def _extract_subtotal(self, raw_text: str) -> Optional[float]:
        match = re.search(r'SUBTOTAL[:\s]*\$?([\d,]+\.\d{2})', raw_text, re.IGNORECASE)
        if match:
            return float(match.group(1).replace(',', ''))
        return None
    
    def _extract_tax(self, raw_text: str) -> Tuple[Optional[float], Optional[float]]:
        tax_match = re.search(r'TAX[\s\d\.%]*[:\s]*\$?([\d,]+\.\d{2})', raw_text, re.IGNORECASE)
        tax_amount = None
        if tax_match:
            tax_amount = float(tax_match.group(1).replace(',', ''))
        
        rate_match = re.search(r'(\d+(?:\.\d+)?)%', raw_text)
        tax_rate = None
        if rate_match:
            tax_rate = float(rate_match.group(1))
        
        return tax_amount, tax_rate
    
    def _clean_item_name(self, name: str) -> str:
        """Clean item name by removing artifacts and normalizing."""
        # Remove accidental quantity prefixes like "3x " or "2X "
        name = re.sub(r'^\d+\s*x\s*', '', name, flags=re.IGNORECASE)
        # Remove @ symbols and other OCR artifacts
        name = name.replace('@', '')
        # Normalize whitespace
        name = re.sub(r'\s+', ' ', name).strip()
        # Remove receipt numbers like #123
        name = re.sub(r'#\d+', '', name).strip()
        return name
    
    def _extract_items(self, raw_text: str) -> List[ReceiptItem]:
        """
        Extract line items with multiple format support.
        """
        items = []
        seen = set()  # Track (name.lower(), price) to avoid duplicates
        
        # Multiple patterns for different receipt formats
        patterns = [
            # Format: 3x Greek Yogurt $14.97
            (r'(\d+)\s*x\s*([^\n$]+?)\s*\$?(\d+\.\d{2})', 
             lambda m: (int(m.group(1)), m.group(2).strip(), float(m.group(3)))),
            
            # Format: Greek Yogurt x3 $14.97
            (r'([^\n$]+?)\s*x\s*(\d+)\s*\$?(\d+\.\d{2})', 
             lambda m: (int(m.group(2)), m.group(1).strip(), float(m.group(3)))),
            
            # Format: Greek Yogurt 3 $14.97
            (r'([^\n$]+?)\s+(\d+)\s*\$?(\d+\.\d{2})', 
             lambda m: (int(m.group(2)), m.group(1).strip(), float(m.group(3)))),
            
            # Format: Greek Yogurt $4.99 (quantity = 1) - MUST start with letter
            (r'([A-Za-z][^\n$]*?)\s*\$?(\d+\.\d{2})', 
             lambda m: (1, m.group(1).strip(), float(m.group(2)))),
        ]
        
        lines = raw_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Try each pattern
            for pattern, extractor in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    try:
                        qty, name, price = extractor(match)
                        
                        # Clean item name
                        name = self._clean_item_name(name)
                        
                        # Skip if name is empty after cleaning
                        if not name:
                            continue
                        
                        # Skip if looks like a total/summary line
                        if any(skip in name.upper() for skip in ['SUBTOTAL', 'TOTAL', 'TAX', 'BALANCE', 'AMOUNT DUE']):
                            continue
                        
                        # Skip if price is unreasonable for single item (likely total)
                        if price > 500 and qty == 1:
                            continue
                        
                        # Deduplicate: skip if we've seen this (name, price) combo
                        key = (name.lower(), price)
                        if key in seen:
                            continue
                        seen.add(key)
                        
                        items.append(ReceiptItem(quantity=qty, name=name, price=price))
                        break  # Stop trying patterns for this line
                        
                    except (ValueError, IndexError):
                        continue
        
        return items
    
    def _extract_payment_method(self, raw_text: str) -> Optional[str]:
        methods = ['CASH', 'CREDIT', 'DEBIT', 'MOBILE PAY', 'CHECK', 'GIFT CARD']
        
        for method in methods:
            if method in raw_text.upper():
                return method
        
        match = re.search(r'Paid[:\s]*(\w+)', raw_text, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        
        return None
    
    def _calculate_confidence(
        self,
        merchant: Optional[str],
        date: Optional[str],
        total: Optional[float],
        subtotal: Optional[float],
        tax: Optional[float],
        items: List[ReceiptItem],
        raw_text: str
    ) -> float:
        score = 0.0
        
        if merchant:
            score += 0.15
        
        if date:
            score += 0.15
        
        if total:
            score += 0.2
        
        if subtotal:
            score += 0.1
        
        if tax:
            score += 0.1
        
        if items:
            score += min(len(items) * 0.05, 0.1)
        
        text_upper = raw_text.upper()
        
        strong_hits = sum(1 for ind in self.strong_indicators if ind in text_upper)
        score += min(strong_hits * 0.05, 0.2)
        
        medium_hits = sum(1 for ind in self.medium_indicators if ind in text_upper)
        score += min(medium_hits * 0.025, 0.1)
        
        confidence = min(score, 1.0)
        return round(confidence, 4)
    
    def to_dict(self, facts: ReceiptFacts) -> Dict:
        return {
            'merchant': facts.merchant,
            'date': facts.date,
            'total_amount': facts.total_amount,
            'subtotal': facts.subtotal,
            'tax': facts.tax,
            'tax_rate': facts.tax_rate,
            'items': [
                {
                    'quantity': item.quantity,
                    'name': item.name,
                    'price': item.price
                }
                for item in facts.items
            ],
            'payment_method': facts.payment_method,
            'extraction_confidence': facts.extraction_confidence
        }


if __name__ == "__main__":
    sample_receipt = """
    TRADER JOE'S #8839
    
    Date: 02/07/2026
    Time: 21:30
    
    Trans: 170864
    Store: 890 Reg: 2
    
    Items: 4
    3x Greek Yogurt $14.97
    1x Avocados 4pk $5.99
    2x Almond Milk $6.98
    3x Organic Bananas $8.97
    
    Subtotal: $36.91
    Tax 6.00%: $2.21
    TOTAL: $39.12
    
    Paid: DEBIT ****6887
    THANK YOU!
    Save this receipt for returns
    """
    
    extractor = ReceiptExtractor()
    facts = extractor.extract(sample_receipt)
    
    print("Extracted Receipt Facts:")
    print(f"  Merchant: {facts.merchant}")
    print(f"  Date: {facts.date}")
    print(f"  Total: ${facts.total_amount}")
    print(f"  Subtotal: ${facts.subtotal}")
    print(f"  Tax: ${facts.tax} ({facts.tax_rate}%)")
    print(f"  Items: {len(facts.items)}")
    for item in facts.items:
        print(f"    - {item.quantity}x {item.name} @ ${item.price}")
    print(f"  Payment: {facts.payment_method}")
    print(f"  Confidence: {facts.extraction_confidence}")
    
    print("\nJSON Output:")
    import json
    print(json.dumps(extractor.to_dict(facts), indent=2))