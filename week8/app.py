"""
ExplainYourMoney - Demo UI
Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# ── Path setup ──────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR / "week8"))
sys.path.insert(0, str(BASE_DIR / "week7_reconciliation"))

# ── Page config ─────────────────────────────────────────────
st.set_page_config(
    page_title="ExplainYourMoney",
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ───────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0f1117;
    border-right: 1px solid #1e2130;
}
[data-testid="stSidebar"] * {
    color: #c9d1d9 !important;
}
[data-testid="stSidebar"] .stRadio label {
    font-size: 14px;
    padding: 6px 0;
}

/* ── Main background ── */
.main { background: #0d1117; }
.block-container { padding: 2rem 2.5rem 2rem 2.5rem; }

/* ── Typography ── */
h1, h2, h3, h4 { color: #e6edf3 !important; font-weight: 500; }
p, li, span, label { color: #8b949e; }

/* ── Metric cards ── */
.metric-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 20px 24px;
    text-align: center;
    transition: border-color 0.2s;
}
.metric-card:hover { border-color: #388bfd; }
.metric-value {
    font-size: 2.2rem;
    font-weight: 600;
    color: #e6edf3;
    font-family: 'DM Mono', monospace;
    line-height: 1;
}
.metric-label {
    font-size: 12px;
    color: #8b949e;
    margin-top: 6px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
.metric-delta-up { color: #f85149; font-size: 12px; }
.metric-delta-down { color: #3fb950; font-size: 12px; }

/* ── Event cards ── */
.event-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-left: 3px solid #388bfd;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 12px;
}
.event-card.high { border-left-color: #f85149; }
.event-card.medium { border-left-color: #d29922; }
.event-card.good { border-left-color: #3fb950; }
.event-headline {
    font-size: 15px;
    font-weight: 500;
    color: #e6edf3;
    margin-bottom: 6px;
}
.event-body {
    font-size: 13px;
    color: #8b949e;
    line-height: 1.6;
    margin-bottom: 8px;
}
.event-evidence {
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    color: #6e7681;
    background: #0d1117;
    padding: 6px 10px;
    border-radius: 4px;
    margin-bottom: 8px;
}
.event-action {
    font-size: 12px;
    color: #388bfd;
    font-weight: 500;
}
.confidence-pill {
    display: inline-block;
    background: #1c2128;
    border: 1px solid #30363d;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 11px;
    color: #8b949e;
    font-family: 'DM Mono', monospace;
    float: right;
}

/* ── Match cards ── */
.match-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 12px;
}
.match-type-badge {
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 600;
    font-family: 'DM Mono', monospace;
    text-transform: uppercase;
    white-space: nowrap;
}
.badge-exact { background: #1a4a2e; color: #3fb950; }
.badge-fuzzy { background: #2d2208; color: #d29922; }
.badge-semantic { background: #1c2e4a; color: #388bfd; }

/* ── Category badges ── */
.cat-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 500;
    margin: 1px;
}

/* ── Pipeline flow ── */
.pipeline-step {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 14px;
    text-align: center;
    position: relative;
}
.pipeline-step-num {
    font-size: 11px;
    color: #388bfd;
    font-family: 'DM Mono', monospace;
    margin-bottom: 4px;
}
.pipeline-step-name {
    font-size: 13px;
    font-weight: 500;
    color: #e6edf3;
}
.pipeline-step-detail {
    font-size: 11px;
    color: #6e7681;
    margin-top: 4px;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #161b22;
    border-radius: 8px;
    padding: 4px;
    gap: 2px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 6px;
    color: #8b949e;
    font-size: 13px;
}
.stTabs [aria-selected="true"] {
    background: #21262d !important;
    color: #e6edf3 !important;
}

/* ── Dataframe ── */
.stDataFrame { border-radius: 8px; overflow: hidden; }

/* ── Divider ── */
hr { border-color: #21262d; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0d1117; }
::-webkit-scrollbar-thumb { background: #21262d; border-radius: 3px; }

/* ── Logo ── */
.logo-text {
    font-size: 22px;
    font-weight: 600;
    color: #e6edf3;
    letter-spacing: -0.5px;
}
.logo-dot { color: #388bfd; }

/* ── Section header ── */
.section-header {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #6e7681;
    margin-bottom: 12px;
    margin-top: 8px;
    font-family: 'DM Mono', monospace;
}
</style>
""", unsafe_allow_html=True)


# ── Data loaders ────────────────────────────────────────────

@st.cache_data
def load_transactions():
    paths = [
        BASE_DIR / "week8" / "output" / "synthetic_transactions_6mo.csv",
        BASE_DIR / "week2" / "week2_deliverable.csv",
        Path("output/synthetic_transactions_6mo.csv"),
    ]
    for p in paths:
        if p.exists():
            df = pd.read_csv(p)
            df['date'] = pd.to_datetime(df['date'])
            return df
    return pd.DataFrame()


@st.cache_data
def load_events():
    paths = [
        BASE_DIR / "week8" / "output" / "detected_events.json",
        Path("output/detected_events.json"),
    ]
    for p in paths:
        if p.exists():
            with open(p) as f:
                return json.load(f)
    return {}


@st.cache_data
def load_reconciliation():
    paths = [
        BASE_DIR / "data" / "week7_reconciliation_report.json",
        Path("../data/week7_reconciliation_report.json"),
        Path("data/week7_reconciliation_report.json"),
    ]
    for p in paths:
        if p.exists():
            with open(p) as f:
                return json.load(f)
    return {}


def get_explainer():
    try:
        from explainer import FinancialExplainer
        return FinancialExplainer()
    except ImportError:
        return None


# ── Color helpers ────────────────────────────────────────────

CATEGORY_COLORS = {
    'dining': '#f85149',
    'groceries': '#3fb950',
    'transportation': '#388bfd',
    'entertainment': '#d2a8ff',
    'healthcare': '#56d364',
    'shopping': '#d29922',
    'utilities': '#79c0ff',
    'income': '#3fb950',
    'subscriptions': '#bc8cff',
    'transfer': '#8b949e',
    'fees': '#f0883e',
    'other': '#6e7681',
}

def cat_color(cat):
    return CATEGORY_COLORS.get(str(cat).lower(), '#6e7681')

def severity_class(sev):
    if sev in ['high', 'warning']:
        return 'high'
    elif sev in ['medium', 'caution']:
        return 'medium'
    return 'good'


# ── Sidebar ─────────────────────────────────────────────────

with st.sidebar:
    st.markdown('<div class="logo-text">Explain<span class="logo-dot">.</span>YourMoney</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:11px;color:#6e7681;margin-bottom:20px;">FinTech Intelligence System</div>', unsafe_allow_html=True)
    st.divider()

    page = st.radio(
        "Navigation",
        ["🏠  Overview", "📊  Transactions", "🔗  Reconciliation", "🧠  Behavioral Detection", "🔍  Evidence Chain"],
        label_visibility="collapsed"
    )

    st.divider()
    st.markdown('<div style="font-size:11px;color:#6e7681;">Pipeline Status</div>', unsafe_allow_html=True)

    status_items = [
        ("Week 2", "NLP Pipeline", "✓"),
        ("Week 3", "Classification", "✓"),
        ("Week 4", "Document OCR", "✓"),
        ("Week 5", "Extraction", "✓"),
        ("Week 6", "Trust Scoring", "✓"),
        ("Week 7", "Reconciliation", "✓"),
        ("Week 8", "Behavioral AI", "✓"),
    ]
    for week, name, status in status_items:
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;padding:3px 0;font-size:12px;">'
            f'<span style="color:#6e7681;">{week} · {name}</span>'
            f'<span style="color:#3fb950;">{status}</span></div>',
            unsafe_allow_html=True
        )


# ── Load data ────────────────────────────────────────────────

df = load_transactions()
events_data = load_events()
recon_data = load_reconciliation()
explainer = get_explainer()

all_events = events_data.get('all_events', {})
top_priorities = events_data.get('top_priorities', [])

page_name = page.split("  ")[1] if "  " in page else page


# ════════════════════════════════════════════════════════════
# PAGE: OVERVIEW
# ════════════════════════════════════════════════════════════

if "Overview" in page:
    st.markdown("## Financial Intelligence Dashboard")
    st.markdown('<div style="color:#8b949e;margin-bottom:24px;">End-to-end pipeline: OCR → Extraction → Trust Scoring → Reconciliation → Behavioral Detection</div>', unsafe_allow_html=True)

    # ── Top metrics ──
    if not df.empty:
        total_txns = len(df)
        total_income = df[df['amount'] > 0]['amount'].sum()
        total_expense = df[df['amount'] < 0]['amount'].abs().sum()
        net_savings = total_income - total_expense
        savings_rate = (net_savings / total_income * 100) if total_income > 0 else 0

        c1, c2, c3, c4, c5 = st.columns(5)
        metrics = [
            (c1, str(total_txns), "Transactions", None),
            (c2, f"${total_income:,.0f}", "Total Income", None),
            (c3, f"${total_expense:,.0f}", "Total Expenses", "up"),
            (c4, f"${net_savings:,.0f}", "Net Savings", "down" if net_savings < 0 else None),
            (c5, f"{savings_rate:.1f}%", "Avg Savings Rate", None),
        ]
        for col, val, label, delta in metrics:
            with col:
                delta_html = ""
                if delta == "up":
                    delta_html = '<div class="metric-delta-up">↑ tracked</div>'
                elif delta == "down":
                    delta_html = '<div class="metric-delta-down">↓ monitored</div>'
                st.markdown(
                    f'<div class="metric-card">'
                    f'<div class="metric-value">{val}</div>'
                    f'<div class="metric-label">{label}</div>'
                    f'{delta_html}</div>',
                    unsafe_allow_html=True
                )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Pipeline architecture ──
    st.markdown('<div class="section-header">System Architecture</div>', unsafe_allow_html=True)

    steps = [
        ("01", "Transaction NLP", "spaCy + BART-MNLI"),
        ("02", "Document OCR", "Tesseract + OpenCV"),
        ("03", "Trust Scoring", "Quality × OCR × Completeness"),
        ("04", "Reconciliation", "3-Tier Exact/Fuzzy/Semantic"),
        ("05", "Behavioral AI", "Z-Score + IQR + Rolling Avg"),
        ("06", "Evidence Chain", "Full Provenance Tracking"),
    ]
    cols = st.columns(len(steps))
    for i, (col, (num, name, detail)) in enumerate(zip(cols, steps)):
        with col:
            arrow = "→" if i < len(steps) - 1 else ""
            st.markdown(
                f'<div class="pipeline-step">'
                f'<div class="pipeline-step-num">{num}</div>'
                f'<div class="pipeline-step-name">{name}</div>'
                f'<div class="pipeline-step-detail">{detail}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Spending by category chart ──
    if not df.empty:
        col1, col2 = st.columns([3, 2])

        with col1:
            st.markdown('<div class="section-header">Monthly Spending Trend</div>', unsafe_allow_html=True)
            expenses = df[df['amount'] < 0].copy()
            expenses['month'] = expenses['date'].dt.to_period('M').astype(str)
            monthly = expenses.groupby(['month', 'category'])['amount'].sum().abs().unstack(fill_value=0)
            if not monthly.empty:
                st.area_chart(monthly, height=250, use_container_width=True)

        with col2:
            st.markdown('<div class="section-header">Spending by Category</div>', unsafe_allow_html=True)
            cat_totals = df[df['amount'] < 0].groupby('category')['amount'].sum().abs().sort_values(ascending=False)
            total_exp = cat_totals.sum()
            for cat, amt in cat_totals.head(6).items():
                pct = amt / total_exp * 100 if total_exp > 0 else 0
                color = cat_color(cat)
                st.markdown(
                    f'<div style="margin-bottom:8px;">'
                    f'<div style="display:flex;justify-content:space-between;margin-bottom:3px;">'
                    f'<span style="font-size:12px;color:#c9d1d9;">{cat.title()}</span>'
                    f'<span style="font-size:12px;color:#6e7681;font-family:DM Mono,monospace;">${amt:,.0f} · {pct:.0f}%</span>'
                    f'</div>'
                    f'<div style="background:#21262d;border-radius:3px;height:4px;">'
                    f'<div style="background:{color};width:{pct:.0f}%;height:4px;border-radius:3px;"></div>'
                    f'</div></div>',
                    unsafe_allow_html=True
                )

    # ── Alerts summary ──
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-header">Active Alerts</div>', unsafe_allow_html=True)

    spikes = all_events.get('spikes', [])
    drifts = all_events.get('drifts', [])
    anomalies = all_events.get('anomalies', [])
    savings_drops = all_events.get('savings_drops', [])

    a1, a2, a3, a4 = st.columns(4)
    alert_metrics = [
        (a1, len(spikes), "Spending Spikes", "#f85149"),
        (a2, len(drifts), "Category Drifts", "#d29922"),
        (a3, len(anomalies), "Anomalies", "#f0883e"),
        (a4, len(savings_drops), "Savings Alerts", "#388bfd"),
    ]
    for col, count, label, color in alert_metrics:
        with col:
            st.markdown(
                f'<div class="metric-card" style="border-left:3px solid {color};">'
                f'<div class="metric-value" style="color:{color};font-size:2rem;">{count}</div>'
                f'<div class="metric-label">{label}</div>'
                f'</div>',
                unsafe_allow_html=True
            )


# ════════════════════════════════════════════════════════════
# PAGE: TRANSACTIONS
# ════════════════════════════════════════════════════════════

elif "Transactions" in page:
    st.markdown("## Transaction Explorer")
    st.markdown('<div style="color:#8b949e;margin-bottom:20px;">Normalized, categorized, and fingerprinted transaction data from Week 2 NLP pipeline</div>', unsafe_allow_html=True)

    if df.empty:
        st.warning("No transaction data found. Run data_generator.py first.")
    else:
        # ── Filters ──
        c1, c2, c3 = st.columns(3)
        with c1:
            cats = ['All'] + sorted(df['category'].unique().tolist())
            sel_cat = st.selectbox("Category", cats)
        with c2:
            months = ['All'] + sorted(df['date'].dt.to_period('M').astype(str).unique().tolist())
            sel_month = st.selectbox("Month", months)
        with c3:
            search = st.text_input("Search merchant", placeholder="e.g. Starbucks")

        # Filter
        filtered = df.copy()
        if sel_cat != 'All':
            filtered = filtered[filtered['category'] == sel_cat]
        if sel_month != 'All':
            filtered = filtered[filtered['date'].dt.to_period('M').astype(str) == sel_month]
        if search:
            col_name = 'merchant_raw' if 'merchant_raw' in filtered.columns else 'merchant_key'
            filtered = filtered[filtered[col_name].str.contains(search, case=False, na=False)]

        st.markdown(f'<div style="font-size:12px;color:#6e7681;margin-bottom:8px;">{len(filtered)} transactions</div>', unsafe_allow_html=True)

        # ── Display columns ──
        display_cols = ['transaction_id', 'date', 'amount', 'category']
        if 'merchant_raw' in filtered.columns:
            display_cols.insert(2, 'merchant_raw')
        elif 'merchant_key' in filtered.columns:
            display_cols.insert(2, 'merchant_key')
        if 'pattern_tag' in filtered.columns:
            display_cols.append('pattern_tag')

        show_df = filtered[display_cols].copy()
        show_df['date'] = show_df['date'].dt.strftime('%Y-%m-%d')
        show_df['amount'] = show_df['amount'].apply(lambda x: f"${x:+,.2f}")

        st.dataframe(
            show_df,
            use_container_width=True,
            height=400,
            hide_index=True,
            column_config={
                "transaction_id": st.column_config.TextColumn("ID", width="small"),
                "date": st.column_config.TextColumn("Date", width="small"),
                "amount": st.column_config.TextColumn("Amount", width="small"),
                "category": st.column_config.TextColumn("Category", width="medium"),
            }
        )

        # ── Monthly breakdown ──
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-header">Monthly Breakdown</div>', unsafe_allow_html=True)

        monthly_cat = df[df['amount'] < 0].copy()
        monthly_cat['month'] = monthly_cat['date'].dt.to_period('M').astype(str)
        pivot = monthly_cat.groupby(['month', 'category'])['amount'].sum().abs().unstack(fill_value=0)

        if not pivot.empty:
            st.bar_chart(pivot, height=300, use_container_width=True)


# ════════════════════════════════════════════════════════════
# PAGE: RECONCILIATION
# ════════════════════════════════════════════════════════════

elif "Reconciliation" in page:
    st.markdown("## Transaction ↔ Document Reconciliation")
    st.markdown('<div style="color:#8b949e;margin-bottom:20px;">3-tier matching: Exact → Fuzzy → Semantic with full evidence chains</div>', unsafe_allow_html=True)

    if not recon_data:
        st.warning("No reconciliation data found. Run reconciliation_engine.py first.")
    else:
        stats = recon_data.get('statistics', {})
        pipeline_stats = stats.get('pipeline', stats)

        # ── Metrics ──
        matches = recon_data.get('matches', [])
        unsupported = recon_data.get('unsupported', recon_data.get('unsupported_transaction_ids', []))
        unreconciled = recon_data.get('unreconciled', recon_data.get('unreconciled_document_ids', []))

        c1, c2, c3, c4, c5 = st.columns(5)
        r_metrics = [
            (c1, len(matches), "Matched Pairs", "#3fb950"),
            (c2, pipeline_stats.get('exact_matches', 0), "Exact Matches", "#3fb950"),
            (c3, pipeline_stats.get('fuzzy_matches', 0), "Fuzzy Matches", "#d29922"),
            (c4, pipeline_stats.get('semantic_matches', 0), "Semantic Matches", "#388bfd"),
            (c5, len(unsupported), "Unsupported", "#f85149"),
        ]
        for col, val, label, color in r_metrics:
            with col:
                st.markdown(
                    f'<div class="metric-card" style="border-top:2px solid {color};">'
                    f'<div class="metric-value">{val}</div>'
                    f'<div class="metric-label">{label}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

        st.markdown("<br>", unsafe_allow_html=True)

        tab1, tab2, tab3 = st.tabs(["✅  Matched Pairs", "⚠️  Unsupported", "📄  Unreconciled"])

        with tab1:
            st.markdown('<div class="section-header">Successfully Matched Transactions</div>', unsafe_allow_html=True)
            if matches:
                for match in matches:
                    match_type = match.get('match_type', 'UNKNOWN')
                    badge_class = {
                        'EXACT': 'badge-exact',
                        'FUZZY': 'badge-fuzzy',
                        'SEMANTIC': 'badge-semantic'
                    }.get(match_type, 'badge-exact')

                    conf = match.get('confidence', 0)
                    tx_id = match.get('transaction_id', '')
                    doc_id = match.get('document_id', '')
                    reasoning = match.get('reasoning', '')

                    if explainer:
                        explanation = explainer.explain_reconciliation_match(match)
                    else:
                        explanation = reasoning

                    st.markdown(
                        f'<div class="event-card">'
                        f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
                        f'<span class="match-type-badge {badge_class}">{match_type}</span>'
                        f'<span style="color:#e6edf3;font-size:13px;font-weight:500;">'
                        f'{tx_id} → {doc_id}</span>'
                        f'<span class="confidence-pill">conf: {conf:.3f}</span>'
                        f'</div>'
                        f'<div class="event-body">{explanation}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

                    # Component breakdown
                    components = match.get('components', {})
                    if components:
                        cols = st.columns(4)
                        comp_labels = [
                            ("Merchant Similarity", components.get('string_similarity', 0)),
                            ("Amount Match", components.get('amount_match', 0)),
                            ("Date Proximity", components.get('date_proximity', 0)),
                            ("Document Trust", components.get('document_trust', 0)),
                        ]
                        for col, (label, val) in zip(cols, comp_labels):
                            with col:
                                color = "#3fb950" if val > 0.8 else "#d29922" if val > 0.5 else "#f85149"
                                st.markdown(
                                    f'<div style="text-align:center;padding:8px;background:#0d1117;border-radius:6px;margin-bottom:12px;">'
                                    f'<div style="font-size:18px;font-weight:600;color:{color};font-family:DM Mono,monospace;">{val:.2f}</div>'
                                    f'<div style="font-size:10px;color:#6e7681;">{label}</div>'
                                    f'</div>',
                                    unsafe_allow_html=True
                                )
            else:
                st.info("No matches found in reconciliation data.")

        with tab2:
            if unsupported:
                for item in unsupported:
                    if isinstance(item, dict):
                        st.markdown(
                            f'<div class="event-card high">'
                            f'<div class="event-headline">🔴 {item.get("transaction_id", item)} — {item.get("label", "Unsupported")}</div>'
                            f'<div class="event-body">Reason: {item.get("reason", "No document found")} · '
                            f'Amount: ${item.get("amount", 0):,.2f} · Merchant: {item.get("merchant", "N/A")}</div>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(f'<div class="event-card high"><div class="event-headline">🔴 {item}</div></div>', unsafe_allow_html=True)
            else:
                st.success("No unsupported transactions.")

        with tab3:
            if unreconciled:
                for item in unreconciled:
                    if isinstance(item, dict):
                        st.markdown(
                            f'<div class="event-card medium">'
                            f'<div class="event-headline">📄 {item.get("document_id", item)} — {item.get("label", "Unreconciled")}</div>'
                            f'<div class="event-body">Reason: {item.get("reason", "No transaction found")} · '
                            f'Trust score: {item.get("trust_score", 0):.2f}</div>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(f'<div class="event-card medium"><div class="event-headline">📄 {item}</div></div>', unsafe_allow_html=True)
            else:
                st.success("All documents reconciled.")


# ════════════════════════════════════════════════════════════
# PAGE: BEHAVIORAL DETECTION
# ════════════════════════════════════════════════════════════

elif "Behavioral" in page:
    st.markdown("## Behavioral & Change Detection")
    st.markdown('<div style="color:#8b949e;margin-bottom:20px;">Statistical analysis detecting spending spikes, category drift, anomalies, and savings changes</div>', unsafe_allow_html=True)

    if not all_events:
        st.warning("No behavioral data found. Run pipeline.py in week8/ first.")
    else:
        # ── Top priority events ──
        st.markdown('<div class="section-header">Priority Events</div>', unsafe_allow_html=True)

        if top_priorities:
            for i, event in enumerate(top_priorities[:8]):
                ev_type = event.get('type', '')
                severity = event.get('severity', 'medium')
                sev_class = severity_class(severity)

                if explainer:
                    exp = explainer.explain_event(event)
                    headline = exp['headline']
                    body = exp['body']
                    evidence = exp['evidence']
                    action = exp['action']
                    confidence = exp['confidence']
                else:
                    headline = f"{ev_type.replace('_', ' ').title()} — {event.get('category', event.get('goal_name', ''))}"
                    body = str(event)
                    evidence = "See raw event data"
                    action = "Review manually"
                    confidence = str(event.get('confidence', 'N/A'))

                score = event.get('priority_score', 0)
                month = event.get('month', '')

                st.markdown(
                    f'<div class="event-card {sev_class}">'
                    f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
                    f'<div class="event-headline">{headline}</div>'
                    f'<span class="confidence-pill">conf: {confidence} · score: {score:.2f}</span>'
                    f'</div>'
                    f'<div class="event-body">{body}</div>'
                    f'<div class="event-evidence">{evidence}</div>'
                    f'<div class="event-action">→ {action}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Tabs by detection type ──
        tab1, tab2, tab3, tab4 = st.tabs(["📈  Spikes", "📊  Drift", "⚠️  Anomalies", "💰  Savings"])

        with tab1:
            spikes = all_events.get('spikes', [])
            if spikes:
                for s in spikes:
                    if explainer:
                        exp = explainer.explain_spike(s)
                        st.markdown(
                            f'<div class="event-card high">'
                            f'<div class="event-headline">{exp["headline"]}</div>'
                            f'<div class="event-body">{exp["body"]}</div>'
                            f'<div class="event-evidence">{exp["evidence"]}</div>'
                            f'<div class="event-action">→ {exp["action"]}</div>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.json(s)
            else:
                st.info("No spending spikes detected. If you expected spikes, apply the .shift(1) fix to detect_spikes() in analyzer.py.")

        with tab2:
            drifts = all_events.get('drifts', [])
            if drifts:
                for d in drifts:
                    if explainer:
                        exp = explainer.explain_drift(d)
                        st.markdown(
                            f'<div class="event-card medium">'
                            f'<div class="event-headline">{exp["headline"]}</div>'
                            f'<div class="event-body">{exp["body"]}</div>'
                            f'<div class="event-evidence">{exp["evidence"]}</div>'
                            f'<div class="event-action">→ {exp["action"]}</div>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.json(d)
            else:
                st.info("No category drift detected.")

        with tab3:
            anomalies = all_events.get('anomalies', [])
            if anomalies:
                for a in anomalies:
                    if explainer:
                        exp = explainer.explain_anomaly(a)
                        sev = severity_class(a.get('severity', 'medium'))
                        st.markdown(
                            f'<div class="event-card {sev}">'
                            f'<div class="event-headline">{exp["headline"]}</div>'
                            f'<div class="event-body">{exp["body"]}</div>'
                            f'<div class="event-evidence">{exp["evidence"]}</div>'
                            f'<div class="event-action">→ {exp["action"]}</div>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.json(a)
            else:
                st.info("No anomalies detected.")

        with tab4:
            drops = all_events.get('savings_drops', [])
            if drops:
                for s in drops:
                    if explainer:
                        exp = explainer.explain_savings_drop(s)
                        st.markdown(
                            f'<div class="event-card high">'
                            f'<div class="event-headline">{exp["headline"]}</div>'
                            f'<div class="event-body">{exp["body"]}</div>'
                            f'<div class="event-evidence">{exp["evidence"]}</div>'
                            f'<div class="event-action">→ {exp["action"]}</div>'
                            f'</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.json(s)

            # ── Savings rate chart ──
            if not df.empty:
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<div class="section-header">Savings Rate Over Time</div>', unsafe_allow_html=True)
                df_copy = df.copy()
                df_copy['month'] = df_copy['date'].dt.to_period('M').astype(str)
                monthly = df_copy.groupby('month')['amount'].sum()
                income_m = df_copy[df_copy['amount'] > 0].groupby('month')['amount'].sum()
                expense_m = df_copy[df_copy['amount'] < 0].groupby('month')['amount'].sum().abs()
                savings_rate = ((income_m - expense_m) / income_m * 100).fillna(0)
                st.line_chart(savings_rate, height=200, use_container_width=True)


# ════════════════════════════════════════════════════════════
# PAGE: EVIDENCE CHAIN
# ════════════════════════════════════════════════════════════

elif "Evidence" in page:
    st.markdown("## Evidence Chain Explorer")
    st.markdown('<div style="color:#8b949e;margin-bottom:20px;">Full provenance: every claim linked to source data with confidence scores</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">How Evidence Chains Work</div>', unsafe_allow_html=True)

    steps = [
        ("📄", "Source Document", "Receipt image uploaded"),
        ("🔍", "OCR Extraction", "Tesseract extracts text"),
        ("📊", "Quality Scoring", "Sharpness × Noise × Contrast"),
        ("🏷️", "Type Classification", "Receipt / Statement / Invoice"),
        ("✂️", "Field Extraction", "Merchant, date, amount, items"),
        ("🔗", "Reconciliation", "Match to bank transaction"),
        ("🎯", "Confidence Score", "Composite: OCR × Extraction × Quality"),
    ]

    cols = st.columns(len(steps))
    for col, (icon, name, detail) in zip(cols, steps):
        with col:
            st.markdown(
                f'<div class="pipeline-step">'
                f'<div style="font-size:20px;margin-bottom:6px;">{icon}</div>'
                f'<div class="pipeline-step-name" style="font-size:12px;">{name}</div>'
                f'<div class="pipeline-step-detail">{detail}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Sample evidence chain ──
    st.markdown('<div class="section-header">Sample Evidence Chain</div>', unsafe_allow_html=True)

    sample_chain = {
        "claim": 'You spent $39.12 at Trader Joe\'s on February 7, 2026',
        "source_document": "receipt_001.jpg",
        "evidence_links": [
            {"stage": "week4_ocr", "result": "Text extracted, OCR confidence: 0.95"},
            {"stage": "week4_quality", "result": "Quality score: 0.89 (sharp, low noise)"},
            {"stage": "week5_receipt_extractor", "result": "Merchant: Trader Joe's, Total: $39.12, Date: 2026-02-07"},
            {"stage": "week6_trust_scorer", "result": "Trust score: 0.87 → status: verified"},
            {"stage": "week7_exact_matcher", "result": "Matched to txn_042 with confidence: 0.96"},
        ],
        "composite_confidence": 0.96,
        "status": "verified"
    }

    st.markdown(
        f'<div class="event-card good">'
        f'<div style="font-size:11px;color:#6e7681;margin-bottom:6px;font-family:DM Mono,monospace;">CLAIM</div>'
        f'<div class="event-headline">"{sample_chain["claim"]}"</div>'
        f'<div style="margin-top:12px;font-size:11px;color:#6e7681;font-family:DM Mono,monospace;">EVIDENCE CHAIN ({len(sample_chain["evidence_links"])} stages)</div>'
        f'</div>',
        unsafe_allow_html=True
    )

    for i, link in enumerate(sample_chain['evidence_links']):
        st.markdown(
            f'<div style="display:flex;gap:12px;margin-bottom:6px;padding-left:12px;">'
            f'<div style="width:1px;background:#21262d;margin:0 11px;"></div>'
            f'<div style="background:#161b22;border:1px solid #21262d;border-radius:6px;padding:10px 14px;flex:1;">'
            f'<span style="font-family:DM Mono,monospace;font-size:11px;color:#388bfd;">{link["stage"]}</span>'
            f'<span style="font-size:12px;color:#8b949e;margin-left:12px;">{link["result"]}</span>'
            f'</div></div>',
            unsafe_allow_html=True
        )

    st.markdown(
        f'<div style="background:#1a4a2e;border:1px solid #2ea043;border-radius:6px;padding:10px 16px;margin-top:6px;">'
        f'<span style="color:#3fb950;font-weight:500;">✓ Verified</span>'
        f'<span style="color:#8b949e;font-size:13px;margin-left:12px;">Composite confidence: {sample_chain["composite_confidence"]:.2f} · Source: {sample_chain["source_document"]}</span>'
        f'</div>',
        unsafe_allow_html=True
    )

    # ── Real reconciliation evidence ──
    if recon_data and recon_data.get('matches'):
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-header">Live Evidence from Reconciliation</div>', unsafe_allow_html=True)

        matches = recon_data.get('matches', [])
        sel_match = st.selectbox(
            "Select a match to inspect",
            options=range(len(matches)),
            format_func=lambda i: f"{matches[i].get('transaction_id')} ↔ {matches[i].get('document_id')} [{matches[i].get('match_type')}]"
        )

        if matches:
            m = matches[sel_match]
            st.markdown(
                f'<div class="event-card">'
                f'<div class="event-headline">{m.get("transaction_id")} ↔ {m.get("document_id")}</div>'
                f'<div class="event-body">{m.get("reasoning", "")}</div>'
                f'<div class="event-evidence">'
                f'Match type: {m.get("match_type")} · '
                f'Confidence: {m.get("confidence", 0):.4f} · '
                f'Date offset: {m.get("date_offset_days", 0)} days · '
                f'Amount discrepancy: {m.get("amount_discrepancy", "None")}'
                f'</div></div>',
                unsafe_allow_html=True
            )

            components = m.get('components', {})
            if components:
                c1, c2, c3, c4 = st.columns(4)
                comp_items = [
                    (c1, "Merchant Similarity", components.get('string_similarity', 0), 0.4),
                    (c2, "Amount Match", components.get('amount_match', 0), 0.3),
                    (c3, "Date Proximity", components.get('date_proximity', 0), 0.2),
                    (c4, "Document Trust", components.get('document_trust', 0), 0.1),
                ]
                for col, label, val, weight in comp_items:
                    with col:
                        color = "#3fb950" if val > 0.8 else "#d29922" if val > 0.5 else "#f85149"
                        st.markdown(
                            f'<div style="background:#161b22;border:1px solid #21262d;border-radius:8px;padding:14px;text-align:center;">'
                            f'<div style="font-size:24px;font-weight:600;color:{color};font-family:DM Mono,monospace;">{val:.2f}</div>'
                            f'<div style="font-size:11px;color:#8b949e;margin-top:4px;">{label}</div>'
                            f'<div style="font-size:10px;color:#6e7681;margin-top:2px;">weight: {weight}</div>'
                            f'</div>',
                            unsafe_allow_html=True
                        )