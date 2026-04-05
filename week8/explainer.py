"""
ExplainYourMoney - GPT-4o-mini Explanation Engine
Place this file in: ExplainYourMoney/week8/explainer.py
Add your key to:   ExplainYourMoney/week8/.env

.env file contents:
OPENAI_API_KEY=sk-...your key here...
Optional: OPENROUTER_BASE_URL, OPENROUTER_MODEL (OpenRouter keys sk-or-v1-* use OpenRouter automatically)
"""

import os
import json
from typing import Dict
from dotenv import load_dotenv

# Load .env from same directory as this file
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini").strip()
SYSTEM_PROMPT = """You are a personal finance assistant for the ExplainYourMoney app.
Explain financial events clearly in 2-3 sentences. Be factual, neutral, and helpful.
Never use alarmist language. Always end with one short, specific, actionable suggestion.
Keep total response under 80 words."""


def _openai_client_and_model():
    from openai import OpenAI
    key = OPENAI_API_KEY
    if not key:
        return None, ""
    base = OPENROUTER_BASE_URL or (
        "https://openrouter.ai/api/v1" if key.startswith("sk-or-v1") else ""
    )
    if base:
        return OpenAI(api_key=key, base_url=base), OPENROUTER_MODEL
    return OpenAI(api_key=key), "gpt-4o-mini"


def _call_gpt(prompt: str) -> str:
    if not OPENAI_API_KEY:
        return "⚠️ Add OPENAI_API_KEY to your week8/.env file to enable AI explanations."
    try:
        client, model = _openai_client_and_model()
        if client is None:
            return "⚠️ Add OPENAI_API_KEY to your week8/.env file to enable AI explanations."
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=120,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Could not generate explanation: {str(e)}"


class FinancialExplainer:
    """Generates plain-English financial explanations using GPT-4o-mini."""

    def explain_spike(self, event: Dict) -> Dict[str, str]:
        category = event.get('category', 'spending')
        current = event.get('current_amount', 0)
        baseline = event.get('baseline_amount', 0)
        change_pct = event.get('change_pct', 0)
        month = event.get('month', '')
        z_score = event.get('z_score', 0)
        prompt = (
            f"The user's {category} spending in {month} was ${current:.2f}, "
            f"{abs(change_pct):.0f}% above their usual ${baseline:.2f} "
            f"(Z-score: {z_score:.1f}). Explain and suggest one action."
        )
        return {
            "headline": f"🔺 {category.title()} spending up {abs(change_pct):.0f}% in {month}",
            "body": _call_gpt(prompt),
            "evidence": (
                f"Method: Z-score vs 3-month rolling average | "
                f"Z-score: {z_score:.2f} | "
                f"Baseline: ${baseline:,.2f} | "
                f"Current: ${current:,.2f}"
            ),
            "confidence": f"{event.get('confidence', 0.85) * 100:.0f}%",
            "action": f"Review {category} transactions for {month}"
        }

    def explain_drift(self, event: Dict) -> Dict[str, str]:
        category = event.get('category', 'spending')
        change_pct = event.get('change_pct', 0)
        month = event.get('month', '')
        current_avg = event.get('rolling_avg_current', 0)
        prev_avg = event.get('rolling_avg_previous', 0)
        prompt = (
            f"The user's {category} 3-month rolling average rose {change_pct:.0f}% "
            f"from ${prev_avg:.2f} to ${current_avg:.2f} as of {month}. "
            f"This is a gradual upward trend. Explain and suggest one action."
        )
        return {
            "headline": f"📊 {category.title()} spending gradually increasing",
            "body": _call_gpt(prompt),
            "evidence": (
                f"Method: 3-month rolling average | "
                f"Previous avg: ${prev_avg:,.2f} | "
                f"Current avg: ${current_avg:,.2f} | "
                f"Change: +{change_pct:.0f}%"
            ),
            "confidence": f"{event.get('confidence', 0.80) * 100:.0f}%",
            "action": f"Set a monthly budget for {category}"
        }

    def explain_anomaly(self, event: Dict) -> Dict[str, str]:
        category = event.get('category', 'spending')
        amount = event.get('amount', 0)
        merchant = event.get('merchant', 'Unknown')
        date = event.get('date', '')
        upper_bound = event.get('upper_bound', 0)
        exceeds_pct = event.get('exceeds_by_pct', 0)
        prompt = (
            f"A {category} transaction of ${amount:.2f} at {merchant} on {date} "
            f"is {exceeds_pct:.0f}% above the normal upper limit of ${upper_bound:.2f} "
            f"(IQR outlier detection). Explain and suggest one action."
        )
        return {
            "headline": f"⚠️ Unusual {category} transaction — ${amount:,.2f} at {merchant}",
            "body": _call_gpt(prompt),
            "evidence": (
                f"Method: IQR outlier detection | "
                f"Amount: ${amount:,.2f} | "
                f"Normal upper bound: ${upper_bound:,.2f} | "
                f"Exceeds by: {exceeds_pct:.0f}%"
            ),
            "confidence": f"{event.get('confidence', 0.85) * 100:.0f}%",
            "action": "Verify this transaction in your bank statement"
        }

    def explain_savings_drop(self, event: Dict) -> Dict[str, str]:
        prev_rate = event.get('savings_rate_previous', 0)
        curr_rate = event.get('savings_rate_current', 0)
        drop_pct = event.get('drop_pct', 0)
        month = event.get('month', '')
        income = event.get('income', 0)
        expenses = event.get('expenses', 0)
        prompt = (
            f"The user's savings rate dropped from {prev_rate:.1f}% to {curr_rate:.1f}% "
            f"in {month} (a {drop_pct:.0f}% drop). "
            f"Income: ${income:,.2f}, Expenses: ${expenses:,.2f}. "
            f"Explain what happened and suggest one concrete action."
        )
        return {
            "headline": f"💰 Savings rate dropped {drop_pct:.0f}% in {month}",
            "body": _call_gpt(prompt),
            "evidence": (
                f"Previous rate: {prev_rate:.1f}% | "
                f"Current rate: {curr_rate:.1f}% | "
                f"Income: ${income:,.2f} | "
                f"Expenses: ${expenses:,.2f}"
            ),
            "confidence": f"{event.get('confidence', 0.90) * 100:.0f}%",
            "action": "Review your highest expense categories this month"
        }

    def explain_goal_status(self, event: Dict) -> Dict[str, str]:
        goal_name = event.get('goal_name', 'goal')
        month = event.get('month', '')
        status = event.get('status', 'unknown')

        if 'savings_rate' in goal_name:
            target = event.get('target_rate_pct', 20)
            actual = event.get('actual_rate_pct', 0)
            gap = event.get('gap_pct', 0)
            if status == 'on_track':
                return {
                    "headline": f"✅ Savings goal met in {month}",
                    "body": f"Savings rate of {actual:.1f}% meets the {target:.0f}% target. Well done!",
                    "evidence": f"Goal: {goal_name} | Period: {month} | Status: {status}",
                    "confidence": f"{event.get('confidence', 0.90) * 100:.0f}%",
                    "action": "Keep it up"
                }
            else:
                prompt = (
                    f"The user's savings rate is {actual:.1f}% in {month}, "
                    f"short of their {target:.0f}% goal by {gap:.1f} points. "
                    f"Give one specific suggestion."
                )
                return {
                    "headline": f"🎯 Savings goal missed in {month}",
                    "body": _call_gpt(prompt),
                    "evidence": f"Goal: {goal_name} | Period: {month} | Status: {status}",
                    "confidence": f"{event.get('confidence', 0.90) * 100:.0f}%",
                    "action": "Cut one discretionary category this month"
                }
        else:
            category = event.get('category', goal_name.replace('_budget', ''))
            limit = event.get('budget_limit', 0)
            spent = event.get('amount_spent', 0)
            pct_used = event.get('pct_used', 0)
            remaining = event.get('remaining', 0)
            if status == 'exceeded':
                prompt = (
                    f"The user spent ${spent:.2f} on {category} in {month}, "
                    f"exceeding their ${limit:.2f} budget by ${abs(remaining):.2f}. "
                    f"Suggest one way to prevent this next month."
                )
                return {
                    "headline": f"🚨 {category.title()} budget exceeded in {month}",
                    "body": _call_gpt(prompt),
                    "evidence": f"Goal: {goal_name} | Period: {month} | Status: {status}",
                    "confidence": f"{event.get('confidence', 0.90) * 100:.0f}%",
                    "action": f"Lower {category} spending next month"
                }
            elif pct_used > 80:
                return {
                    "headline": f"⚡ {category.title()} budget almost full in {month}",
                    "body": (f"${spent:.2f} of ${limit:.2f} used ({pct_used:.0f}%). "
                             f"Only ${remaining:.2f} remaining."),
                    "evidence": f"Goal: {goal_name} | Period: {month} | Status: {status}",
                    "confidence": f"{event.get('confidence', 0.90) * 100:.0f}%",
                    "action": f"Slow down {category} spending"
                }
            else:
                return {
                    "headline": f"✅ {category.title()} budget on track in {month}",
                    "body": f"${spent:.2f} of ${limit:.2f} used ({pct_used:.0f}%). ${remaining:.2f} remaining.",
                    "evidence": f"Goal: {goal_name} | Period: {month} | Status: {status}",
                    "confidence": f"{event.get('confidence', 0.90) * 100:.0f}%",
                    "action": "No action needed"
                }

    def explain_event(self, event: Dict) -> Dict[str, str]:
        routers = {
            'spending_spike': self.explain_spike,
            'category_drift': self.explain_drift,
            'anomaly': self.explain_anomaly,
            'savings_drop': self.explain_savings_drop,
            'goal_status': self.explain_goal_status,
        }
        handler = routers.get(event.get('type', ''))
        if handler:
            return handler(event)
        prompt = f"Explain this financial event in 2 sentences: {json.dumps(event, default=str)[:300]}"
        return {
            "headline": event.get('type', 'Event').replace('_', ' ').title(),
            "body": _call_gpt(prompt),
            "evidence": "See raw data",
            "confidence": str(event.get('confidence', 'N/A')),
            "action": "Review manually"
        }

    def explain_reconciliation_match(self, match: Dict) -> str:
        match_type = match.get('match_type', 'UNKNOWN')
        tx_id = match.get('transaction_id', '')
        doc_id = match.get('document_id', '')
        confidence = match.get('confidence', 0)
        components = match.get('components', {})
        ss = components.get('string_similarity', 0)
        am = components.get('amount_match', 0)
        dp = components.get('date_proximity', 0)
        dt = components.get('document_trust', 0)
        prompt = (
            f"Bank transaction {tx_id} matched document {doc_id} "
            f"using {match_type} matching ({confidence:.0%} confidence). "
            f"Scores: merchant {ss:.0%}, amount {am:.0%}, "
            f"date {dp:.0%}, document trust {dt:.0%}. "
            f"Explain in one sentence for a non-technical user."
        )
        return _call_gpt(prompt)