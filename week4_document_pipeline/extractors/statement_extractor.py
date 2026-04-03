import re
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class Transaction:
    date: str
    description: str
    amount: float
    transaction_type: str
    balance: Optional[float]


@dataclass
class StatementFacts:
    account_holder: Optional[str]
    statement_period: Dict[str, str]
    beginning_balance: Optional[float]
    ending_balance: Optional[float]
    transactions: List[Transaction]
    extraction_confidence: float


def normalize_ocr_text(raw_text: str) -> str:
    """Fix common OCR artifacts in statements"""

    # Fix broken dates
    raw_text = re.sub(r'(\d{2})\s+(\d{2})\s+(\d{4})', r'\1/\2/\3', raw_text)

    # Fix amount spacing
    raw_text = re.sub(r'(\d)\s(\d{3}\.\d{2})', r'\1\2', raw_text)

    # Normalize spaces BUT keep line breaks
    raw_text = re.sub(r'[ \t]+', ' ', raw_text)

    return raw_text.strip()


class StatementExtractor:

    def extract(self, raw_text: str) -> StatementFacts:

        raw_text = normalize_ocr_text(raw_text)
        lines = [l.strip() for l in raw_text.split("\n") if l.strip()]

        account_holder = self._extract_account_holder(lines)
        period = self._extract_statement_period(raw_text)
        beginning_balance = self._extract_beginning_balance(raw_text)
        ending_balance = self._extract_ending_balance(raw_text)
        transactions = self._extract_transactions(lines)

        confidence = self._calculate_confidence(
            account_holder,
            period,
            beginning_balance,
            ending_balance,
            transactions,
            raw_text
        )

        return StatementFacts(
            account_holder,
            period,
            beginning_balance,
            ending_balance,
            transactions,
            confidence
        )

    def _extract_account_holder(self, lines: List[str]) -> Optional[str]:

        for line in lines[:5]:

            if re.match(r'^[A-Z]{2,20}\s+[A-Z]{2,20}$', line):

                skip_words = [
                    "STATEMENT",
                    "ACCOUNT",
                    "BALANCE",
                    "PERIOD"
                ]

                if not any(word in line for word in skip_words):

                    return line.title()

        return None

    def _extract_statement_period(self, raw_text: str) -> Dict[str, str]:

        period_match = re.search(
            r'(?:Statement\s+)?Period[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+(?:to|through|-)\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            raw_text,
            re.IGNORECASE
        )

        if period_match:

            start = self._normalize_date(period_match.group(1))
            end = self._normalize_date(period_match.group(2))

            if start and end:

                return {
                    "start": start,
                    "end": end
                }

        return {}

    def _normalize_date(self, date_str: str) -> Optional[str]:

        try:

            if "/" in date_str:

                month, day, year = date_str.split("/")

                dt = datetime(int(year), int(month), int(day))

                return dt.strftime("%Y-%m-%d")

        except:

            return None

        return None

    def _extract_beginning_balance(self, raw_text: str) -> Optional[float]:

        match = re.search(
            r'Beginning\s+Balance[:\s]*\$?([\d,]+\.\d{2})',
            raw_text,
            re.IGNORECASE
        )

        if match:

            return float(match.group(1).replace(",", ""))

        return None

    def _extract_ending_balance(self, raw_text: str) -> Optional[float]:

        match = re.search(
            r'Ending\s+Balance[:\s]*\$?([\d,]+\.\d{2})',
            raw_text,
            re.IGNORECASE
        )

        if match:

            return float(match.group(1).replace(",", ""))

        return None

    def _extract_transactions(self, lines: List[str]) -> List[Transaction]:

        transactions = []

        for line in lines:

            if re.match(r'\d{1,2}/\d{1,2}/\d{4}', line):

                transaction = self._parse_transaction_line(line)

                if transaction:

                    transactions.append(transaction)

        return transactions

    def _parse_transaction_line(self, line: str) -> Optional[Transaction]:

        date_match = re.match(r'(\d{1,2}/\d{1,2}/\d{4})\s+', line)

        if not date_match:

            return None

        date = self._normalize_date(date_match.group(1))

        remaining = line[date_match.end():].strip()

        amounts = re.findall(r'([\-\d,]+\.\d{2})', remaining)

        if len(amounts) < 2:

            return None

        transaction_amount = float(amounts[-2].replace(",", "").replace("-", ""))
        balance = float(amounts[-1].replace(",", ""))

        transaction_type = "debit"

        if any(word in remaining.upper() for word in ["DEPOSIT", "TRANSFER"]):

            transaction_type = "credit"

        description = remaining

        for amt in amounts:

            description = description.replace(amt, "")

        description = re.sub(r'\s+', ' ', description).strip()

        return Transaction(
            date=date,
            description=description,
            amount=transaction_amount,
            transaction_type=transaction_type,
            balance=balance
        )

    def _calculate_confidence(
        self,
        account_holder,
        period,
        beginning_balance,
        ending_balance,
        transactions,
        raw_text
    ) -> float:

        score = 0

        if account_holder:
            score += 0.2

        if period:
            score += 0.2

        if beginning_balance:
            score += 0.15

        if ending_balance:
            score += 0.15

        if transactions:
            score += min(len(transactions) * 0.03, 0.3)

        return round(min(score, 1.0), 2)


if __name__ == "__main__":

    sample_statement = """
    JOHN DOE

    Account Statement
    Statement Period: 01/01/2026 to 01/31/2026

    Beginning Balance: $5,200.00

    Date Description Amount Balance

    01/02/2026 PAYROLL DEPOSIT 2,500.00 7,700.00
    01/05/2026 GROCERY STORE #1234 -45.67 7,654.33
    01/08/2026 ELECTRIC COMPANY -120.50 7,533.83
    01/12/2026 TRANSFER FROM SAVINGS 1,000.00 8,533.83
    01/15/2026 RESTAURANT XYZ -32.15 8,501.68
    01/20/2026 ONLINE RETAILER AMZN -156.78 8,344.90
    01/25/2026 GAS STATION -48.00 8,296.90
    01/28/2026 PHONE BILL -89.99 8,206.91

    Ending Balance: $8,206.91
    """

    extractor = StatementExtractor()

    facts = extractor.extract(sample_statement)

    print("Extracted Statement Facts:")

    print("Account Holder:", facts.account_holder)
    print("Statement Period:", facts.statement_period)
    print("Beginning Balance:", facts.beginning_balance)
    print("Ending Balance:", facts.ending_balance)
    print("Transactions:", len(facts.transactions))

    for t in facts.transactions[:3]:

        print("-", t.date, "|", t.description, "|", t.amount, "|", t.transaction_type)

    print("Confidence:", facts.extraction_confidence)