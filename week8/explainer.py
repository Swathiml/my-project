"""
ExplainYourMoney - Local LLM Explanation Engine
Uses Ollama (free, offline, no API key needed)
Model: llama3.2:3b (fits in 8GB RAM)

Setup:
1. Install Ollama: https://ollama.com/download
2. Run: ollama pull llama3.2:3b
3. pip install ollama
"""

from typing import Dict, Any, Optional
import json


def _get_ollama_client():
    try:
        import ollama
        return ollama
    except ImportError:
        return None


def _call_llm(prompt: str, system: str = "") -> str:
    """
    Call local Ollama LLM. Falls back to template if Ollama not running.
    """
    client = _get_ollama_client()
    if client is None:
        return "Install ollama: pip install ollama, then: ollama pull llama3.2:3b"

    try:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = client.chat(
            model="llama3.2:3b",
            messages=messages,
            options={
                "temperature": 0.3,
                "num_predict": 200,
                "num_ctx": 1024,
            }
        )
        return response["message"]["content"].strip()

    except Exception:
        return _template_fallback(prompt)


def _template_fallback(prompt: str) -> str:
    """Simple fallback if Ollama is not running."""
    return "Ollama not running. Start the Ollama app and ensure llama3.2:3b is pulled."


SYSTEM_PROMPT = """You are a personal finance assistant.
Explain financial events clearly and concisely in 2-3 sentences.
Be factual, neutral, and helpful. No alarmist language.
Always end with one actionable suggestion."""


class FinancialExplainer:
    """
    Generates explanations using local Ollama LLM.
    Falls back to message if Ollama is not running.
    """

    def __init__(self, model: str = "llama3.2:3b"):
        self.model = model
        self.ollama_available = False
        self._check_ollama()

    def _check_ollama(self):
        """Check if Ollama is available and model is loaded."""
        client = _get_ollama_client()
        if client is None:
            print("[ExplainYourMoney] ollama not installed. Run: pip install ollama")
            return

        try:
            models = client.list()
            model_names = [m["name"] for m in models.get("models", [])]
            available = any(self.model in m for m in model_names)
            if available:
                print(f"[ExplainYourMoney] Ollama ready — model: {self.model}")
                self.ollama_available = True
            else:
                print(f"[ExplainYourMoney] Model not found. Run: ollama pull {self.model}")
        except Exception:
            print("[ExplainYourMoney] Ollama not running. Start Ollama app first.")

    def explain_spike(self, event: Dict) -> Dict[str, str]:
        category = event.get('category', 'spending')
        current = event.get('current_amount', 0)
        baseline = event.get('baseline_amount', 0)
        change_pct = event.get('change_pct', 0)
        month = event.get('month', '')
        z_score = event.get('z_score', 0)

        prompt = (
            f"A user's {category} spending in {month} was ${current:.2f}, "
            f"which is {change_pct:.0f}% above their usual ${baseline:.2f}. "
            f"The Z-score is {z_score:.1f}. "
            f"Explain what this means and suggest one action."
        )

        return {
            "headline": f"🔺 {category.title()} spending up {abs(change_pct):.0f}% in {month}",
            "body": _call_llm(prompt, SYSTEM_PROMPT),
            "evidence": (
                f"Z-score: {z_score:.2f} | "
                f"Baseline: ${baseline:,.2f} | "
                f"Current: ${current:,.2f} | "
                f"Method: Z-score vs 3-month rolling average"
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
            f"A user's {category} spending 3-month rolling average "
            f"increased by {change_pct:.0f}% from ${prev_avg:.2f} to ${current_avg:.2f} "
            f"as of {month}. This is a gradual upward trend, not a one-time spike. "
            f"Explain the significance and suggest one action."
        )

        return {
            "headline": f"📊 {category.title()} spending trending upward",
            "body": _call_llm(prompt, SYSTEM_PROMPT),
            "evidence": (
                f"Method: 3-month rolling average | "
                f"Previous avg: ${prev_avg:,.2f} | "
                f"Current avg: ${current_avg:,.2f} | "
                f"Change: +{change_pct:.0f}%"
            ),
            "confidence": f"{event.get('confidence', 0.80) * 100:.0f}%",
            "action": f"Set a budget alert for {category}"
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
            f"detected using IQR outlier analysis. "
            f"Explain what this means and suggest one action."
        )

        return {
            "headline": f"⚠️ Unusual {category} transaction — ${amount:,.2f} at {merchant}",
            "body": _call_llm(prompt, SYSTEM_PROMPT),
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
            f"A user's savings rate dropped from {prev_rate:.1f}% to {curr_rate:.1f}% "
            f"in {month} — a {drop_pct:.0f}% decrease. "
            f"Income was ${income:,.2f} and expenses were ${expenses:,.2f}. "
            f"Explain what this means and suggest one concrete action."
        )

        return {
            "headline": f"💰 Savings rate dropped {drop_pct:.0f}% in {month}",
            "body": _call_llm(prompt, SYSTEM_PROMPT),
            "evidence": (
                f"Previous rate: {prev_rate:.1f}% | "
                f"Current rate: {curr_rate:.1f}% | "
                f"Income: ${income:,.2f} | "
                f"Expenses: ${expenses:,.2f}"
            ),
            "confidence": f"{event.get('confidence', 0.90) * 100:.0f}%",
            "action": "Review your largest expense categories this month"
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
                headline = f"✅ Savings goal met in {month}"
                body = f"Savings rate of {actual:.1f}% meets the {target:.0f}% target. Keep it up."
                action = "Keep up the good work"
            else:
                prompt = (
                    f"A user's savings rate is {actual:.1f}% in {month}, "
                    f"falling short of their {target:.0f}% goal by {gap:.1f} percentage points. "
                    f"Give one specific suggestion to close this gap."
                )
                body = _call_llm(prompt, SYSTEM_PROMPT)
                headline = f"🎯 Savings goal not met in {month}"
                action = "Identify which categories to cut back"

        else:
            category = event.get('category', goal_name.replace('_budget', ''))
            limit = event.get('budget_limit', 0)
            spent = event.get('amount_spent', 0)
            pct_used = event.get('pct_used', 0)
            remaining = event.get('remaining', 0)

            if status == 'exceeded':
                prompt = (
                    f"A user spent ${spent:.2f} on {category} in {month}, "
                    f"exceeding their ${limit:.2f} budget by ${abs(remaining):.2f} "
                    f"({pct_used:.0f}% used). "
                    f"Suggest one way to prevent this next month."
                )
                body = _call_llm(prompt, SYSTEM_PROMPT)
                headline = f"🚨 {category.title()} budget exceeded in {month}"
                action = f"Set a stricter {category} limit next month"
            elif pct_used > 80:
                headline = f"⚡ {category.title()} budget almost full in {month}"
                body = f"${spent:.2f} of ${limit:.2f} used ({pct_used:.0f}%). ${remaining:.2f} remaining — slow down spending."
                action = f"Reduce {category} spending this month"
            else:
                headline = f"✅ {category.title()} budget on track in {month}"
                body = f"${spent:.2f} of ${limit:.2f} used ({pct_used:.0f}%). ${remaining:.2f} remaining."
                action = "No action needed"

        return {
            "headline": headline,
            "body": body,
            "evidence": f"Goal: {goal_name} | Period: {month} | Status: {status}",
            "confidence": f"{event.get('confidence', 0.90) * 100:.0f}%",
            "action": action
        }

    def explain_event(self, event: Dict) -> Dict[str, str]:
        """Route to correct explainer based on event type."""
        event_type = event.get('type', '')

        routers = {
            'spending_spike': self.explain_spike,
            'category_drift': self.explain_drift,
            'anomaly': self.explain_anomaly,
            'savings_drop': self.explain_savings_drop,
            'goal_status': self.explain_goal_status,
        }

        handler = routers.get(event_type)
        if handler:
            return handler(event)

        prompt = (
            f"Explain this financial event in 2 sentences: "
            f"{json.dumps(event, default=str)[:300]}"
        )
        return {
            "headline": f"Event: {event_type.replace('_', ' ').title()}",
            "body": _call_llm(prompt, SYSTEM_PROMPT),
            "evidence": "See raw event data",
            "confidence": str(event.get('confidence', 'N/A')),
            "action": "Review this event manually"
        }

    def explain_reconciliation_match(self, match: Dict) -> str:
        """Explain a reconciliation match in plain English."""
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
            f"A bank transaction ({tx_id}) matched a receipt ({doc_id}) "
            f"using {match_type} matching with {confidence:.0%} confidence. "
            f"Scores: merchant {ss:.0%}, amount {am:.0%}, date {dp:.0%}, trust {dt:.0%}. "
            f"Explain in one sentence a non-technical user would understand."
        )

        return _call_llm(prompt, SYSTEM_PROMPT)