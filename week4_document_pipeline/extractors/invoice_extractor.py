import re
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class InvoiceLineItem:
    description: str
    quantity: int
    unit_price: float
    amount: float


@dataclass
class InvoiceFacts:
    invoice_number: Optional[str]
    vendor: Optional[str]
    client: Optional[str]
    invoice_date: Optional[str]
    due_date: Optional[str]
    line_items: List[InvoiceLineItem]
    subtotal: Optional[float]
    tax: Optional[float]
    tax_rate: Optional[float]
    total_due: Optional[float]
    payment_terms: Optional[str]
    extraction_confidence: float


class InvoiceExtractor:

    def extract(self, raw_text: str) -> InvoiceFacts:

        lines = [l.strip() for l in raw_text.split("\n") if l.strip()]

        invoice_number = self._extract_invoice_number(raw_text)
        vendor = self._extract_vendor(lines)
        client = self._extract_client(raw_text)
        invoice_date = self._extract_invoice_date(raw_text)
        due_date = self._extract_due_date(raw_text)
        line_items = self._extract_line_items(raw_text)
        subtotal = self._extract_subtotal(raw_text)
        tax, tax_rate = self._extract_tax(raw_text)
        total_due = self._extract_total_due(raw_text)
        payment_terms = self._extract_payment_terms(raw_text)

        confidence = self._calculate_confidence(
            invoice_number,
            vendor,
            invoice_date,
            due_date,
            line_items,
            subtotal,
            total_due,
            raw_text
        )

        return InvoiceFacts(
            invoice_number,
            vendor,
            client,
            invoice_date,
            due_date,
            line_items,
            subtotal,
            tax,
            tax_rate,
            total_due,
            payment_terms,
            confidence
        )

    def _extract_invoice_number(self, raw_text: str) -> Optional[str]:

        patterns = [
            r'Invoice\s*(?:#|No|Number)\s*[:\s]*([A-Z0-9\-]{5,30})',
            r'(INV[-\d]{5,30})'
        ]

        for pattern in patterns:

            match = re.search(pattern, raw_text, re.IGNORECASE)

            if match:

                value = match.group(1) if match.groups() else match.group(0)

                if value.upper() != "INVOICE":
                    return value.upper()

        return None

    def _extract_vendor(self, lines: List[str]) -> Optional[str]:

        for line in lines[:5]:

            if "invoice" in line.lower():
                continue

            if len(line) > 5 and re.search(r'[A-Za-z]', line):
                return line.title()

        return None

    def _extract_client(self, raw_text: str) -> Optional[str]:

        match = re.search(
            r'(?:Bill To|Billed To|Client|Customer|To)[:\s]*\n?([^\n]+)',
            raw_text,
            re.IGNORECASE
        )

        if match:
            return match.group(1).strip().title()

        return None

    def _extract_invoice_date(self, raw_text: str) -> Optional[str]:

        match = re.search(
            r'(?:Invoice\s+)?Date[:\s]+(\d{1,2}/\d{1,2}/\d{2,4})',
            raw_text,
            re.IGNORECASE
        )

        if match:
            return self._normalize_date(match.group(1))

        return None

    def _extract_due_date(self, raw_text: str) -> Optional[str]:

        match = re.search(
            r'Due\s+Date[:\s]+(\d{1,2}/\d{1,2}/\d{2,4})',
            raw_text,
            re.IGNORECASE
        )

        if match:
            return self._normalize_date(match.group(1))

        return None

    def _normalize_date(self, date_str: str) -> Optional[str]:

        try:
            month, day, year = date_str.split("/")

            if len(year) == 2:
                year = "20" + year

            dt = datetime(int(year), int(month), int(day))

            return dt.strftime("%Y-%m-%d")

        except:
            return None

    def _extract_line_items(self, raw_text: str) -> List[InvoiceLineItem]:

        items = []

        lines = raw_text.split("\n")

        for line in lines:

            parts = [p.strip() for p in line.split("|")]

            if len(parts) == 4:

                desc = parts[0]

                try:

                    qty = int(parts[1])

                    unit_price = float(
                        parts[2].replace("$", "").replace(",", "")
                    )

                    amount = float(
                        parts[3].replace("$", "").replace(",", "")
                    )

                    items.append(
                        InvoiceLineItem(
                            description=desc,
                            quantity=qty,
                            unit_price=unit_price,
                            amount=amount
                        )
                    )

                except:
                    continue

        return items

    def _extract_subtotal(self, raw_text: str) -> Optional[float]:

        match = re.search(
            r'Subtotal[:\s]*\$?([\d,]+\.\d{2})',
            raw_text,
            re.IGNORECASE
        )

        if match:
            return float(match.group(1).replace(",", ""))

        return None

    def _extract_tax(self, raw_text: str) -> tuple:

        tax_match = re.search(
            r'Tax.*?\$([\d,]+\.\d{2})',
            raw_text,
            re.IGNORECASE
        )

        tax_amount = (
            float(tax_match.group(1).replace(",", ""))
            if tax_match
            else None
        )

        rate_match = re.search(r'(\d+(?:\.\d+)?)\s*%', raw_text)

        tax_rate = float(rate_match.group(1)) if rate_match else None

        return tax_amount, tax_rate

    def _extract_total_due(self, raw_text: str) -> Optional[float]:

        match = re.search(
            r'Total\s+Due[:\s]*\$?([\d,]+\.\d{2})',
            raw_text,
            re.IGNORECASE
        )

        if match:
            return float(match.group(1).replace(",", ""))

        return None

    def _extract_payment_terms(self, raw_text: str) -> Optional[str]:

        match = re.search(
            r'(?:Payment\s+Terms|Terms)[:\s]+([^\n]+)',
            raw_text,
            re.IGNORECASE
        )

        if match:
            return match.group(1).strip()

        return None

    def _calculate_confidence(
        self,
        invoice_num,
        vendor,
        inv_date,
        due_date,
        items,
        subtotal,
        total,
        raw_text
    ) -> float:

        score = 0

        if invoice_num:
            score += 0.15

        if vendor:
            score += 0.15

        if inv_date:
            score += 0.15

        if due_date:
            score += 0.1

        if items:
            score += min(len(items) * 0.05, 0.15)

        if subtotal:
            score += 0.1

        if total:
            score += 0.1

        indicators = [
            "invoice",
            "total",
            "payment",
            "subtotal"
        ]

        hits = sum(1 for ind in indicators if ind in raw_text.lower())

        score += min(hits * 0.02, 0.1)

        return round(min(score, 1.0), 4)


if __name__ == "__main__":

    sample_invoice = """
    Tech Solutions LLC
    123 Business Ave

    INVOICE

    Invoice #: INV-2026-001234
    Date: 02/15/2026
    Due Date: 03/17/2026

    Bill To:
    Client Corp
    456 Enterprise Blvd

    Payment Terms: Net 30

    Description | Qty | Unit Price | Amount
    Consulting Services | 10 | $150.00 | $1,500.00
    Software License | 5 | $200.00 | $1,000.00
    Support Package | 1 | $500.00 | $500.00

    Subtotal: $3,000.00
    Tax (8%): $240.00
    Total Due: $3,240.00
    """

    extractor = InvoiceExtractor()

    facts = extractor.extract(sample_invoice)

    print("Extracted Invoice Facts:")
    print("Invoice #:", facts.invoice_number)
    print("Vendor:", facts.vendor)
    print("Client:", facts.client)
    print("Invoice Date:", facts.invoice_date)
    print("Due Date:", facts.due_date)
    print("Payment Terms:", facts.payment_terms)
    print("Line Items:", len(facts.line_items))

    for item in facts.line_items:
        print("-", item.description, item.quantity, item.unit_price, item.amount)

    print("Subtotal:", facts.subtotal)
    print("Tax:", facts.tax)
    print("Tax Rate:", facts.tax_rate)
    print("Total Due:", facts.total_due)
    print("Confidence:", facts.extraction_confidence)