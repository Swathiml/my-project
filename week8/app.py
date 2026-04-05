"""
ExplainYourMoney - Demo UI
Place in: ExplainYourMoney/week8/app.py
Run with: cd week8 && streamlit run app.py

Requirements:
    pip install streamlit pandas numpy openai python-dotenv pillow
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import sys
from pathlib import Path
from PIL import Image
import io

# ── Path setup ───────────────────────────────────────────────────────────────
WEEK8_DIR  = Path(__file__).parent
ROOT_DIR   = WEEK8_DIR.parent
OUTPUT_DIR = WEEK8_DIR / "output"
DATA_DIR   = ROOT_DIR / "data"

sys.path.insert(0, str(WEEK8_DIR))
sys.path.insert(0, str(ROOT_DIR / "week7_reconciliation"))

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ExplainYourMoney",
    page_icon="💡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Sora', sans-serif; }

/* Background */
.main { background: #0a0e1a; }
.block-container { padding: 1.8rem 2.5rem; max-width: 1400px; }

/* Sidebar */
[data-testid="stSidebar"] { background: #0d1223; border-right: 1px solid #1a2040; }
[data-testid="stSidebar"] * { color: #8899bb !important; }
[data-testid="stSidebar"] .stRadio label { font-size: 13px; padding: 5px 0; }

/* Headings */
h1,h2,h3 { color: #e2e8f8 !important; font-weight: 500; }
p, span, label { color: #6b80a8; }

/* ── Cards ── */
.kpi-card {
    background: linear-gradient(135deg, #111827 0%, #0f172a 100%);
    border: 1px solid #1e2d4a;
    border-radius: 12px;
    padding: 20px 22px;
    text-align: center;
}
.kpi-val {
    font-size: 2rem; font-weight: 600;
    color: #e2e8f8; font-family: 'JetBrains Mono', monospace;
    line-height: 1.1;
}
.kpi-label { font-size: 11px; color: #4a6080; margin-top: 5px;
             text-transform: uppercase; letter-spacing: .08em; }

/* ── Event cards ── */
.ecard {
    background: #0f172a;
    border: 1px solid #1e2d4a;
    border-left: 3px solid #3b82f6;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 10px;
}
.ecard.red  { border-left-color: #ef4444; }
.ecard.amber{ border-left-color: #f59e0b; }
.ecard.green{ border-left-color: #22c55e; }
.ecard.blue { border-left-color: #3b82f6; }

.ecard-headline { font-size: 14px; font-weight: 500; color: #e2e8f8; margin-bottom: 6px; }
.ecard-body     { font-size: 13px; color: #7a90b8; line-height: 1.65; margin-bottom: 8px; }
.ecard-evidence {
    font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #4a5e80;
    background: #070c18; padding: 6px 10px; border-radius: 6px; margin-bottom: 8px;
}
.ecard-action { font-size: 12px; color: #3b82f6; font-weight: 500; }
.conf-pill {
    float: right; background: #111827; border: 1px solid #1e2d4a;
    border-radius: 20px; padding: 2px 9px;
    font-size: 10px; color: #6b80a8; font-family: 'JetBrains Mono', monospace;
}

/* ── Match badges ── */
.badge {
    border-radius: 5px; padding: 3px 9px;
    font-size: 10px; font-weight: 600;
    font-family: 'JetBrains Mono', monospace; text-transform: uppercase;
}
.badge-exact    { background:#14532d; color:#4ade80; }
.badge-fuzzy    { background:#431407; color:#fb923c; }
.badge-semantic { background:#1e1b4b; color:#818cf8; }

/* ── Progress bars ── */
.pbar-wrap { margin-bottom: 9px; }
.pbar-label { display:flex; justify-content:space-between; margin-bottom:3px; }
.pbar-label span { font-size:12px; color:#8899bb; }
.pbar-track { background:#111827; border-radius:4px; height:5px; }
.pbar-fill  { height:5px; border-radius:4px; }

/* ── Upload area ── */
.upload-box {
    background: #0f172a; border: 2px dashed #1e2d4a;
    border-radius: 12px; padding: 24px 20px; text-align: center;
    margin-bottom: 12px;
}
.upload-box:hover { border-color: #3b82f6; }
.upload-title { font-size: 14px; font-weight: 500; color: #e2e8f8; margin-bottom: 4px; }
.upload-sub   { font-size: 12px; color: #4a6080; }

/* ── Section header ── */
.sec-header {
    font-size: 10px; text-transform: uppercase; letter-spacing: .12em;
    color: #3b5080; margin: 18px 0 10px;
    font-family: 'JetBrains Mono', monospace;
}

/* ── Component score box ── */
.score-box {
    background: #0f172a; border: 1px solid #1e2d4a;
    border-radius: 8px; padding: 12px; text-align: center;
    margin-bottom: 10px;
}
.score-val { font-size: 22px; font-weight: 600; font-family: 'JetBrains Mono', monospace; }
.score-lbl { font-size: 10px; color: #4a6080; margin-top: 3px; }
.score-wt  { font-size: 9px; color: #2a3a56; margin-top: 1px; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #0f172a; border-radius: 8px; padding: 3px; gap: 2px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent; border-radius: 6px;
    color: #6b80a8; font-size: 13px;
}
.stTabs [aria-selected="true"] {
    background: #1e2d4a !important; color: #e2e8f8 !important;
}

/* ── Dataframe ── */
.stDataFrame { border-radius: 8px; overflow: hidden; }

/* ── Logo ── */
.logo { font-size: 20px; font-weight: 600; color: #e2e8f8; letter-spacing: -.3px; }
.logo-dot { color: #3b82f6; }

/* scrollbar */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: #0a0e1a; }
::-webkit-scrollbar-thumb { background: #1e2d4a; border-radius: 3px; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ──────────────────────────────────────────────────────────────────

CATEGORY_COLORS = {
    'dining':'#ef4444','groceries':'#22c55e','transportation':'#3b82f6',
    'entertainment':'#a855f7','healthcare':'#06b6d4','shopping':'#f59e0b',
    'utilities':'#64748b','income':'#22c55e','subscriptions':'#8b5cf6',
    'transfer':'#94a3b8','fees':'#f97316','other':'#475569',
}

def cat_color(c): return CATEGORY_COLORS.get(str(c).lower(),'#475569')

def sev_class(s):
    if s in ('high','warning'): return 'red'
    if s in ('medium','caution'): return 'amber'
    if s == 'good': return 'green'
    return 'blue'

def kpi(col, val, label, color=None):
    style = f'border-top:2px solid {color};' if color else ''
    col.markdown(
        f'<div class="kpi-card" style="{style}">'
        f'<div class="kpi-val">{val}</div>'
        f'<div class="kpi-label">{label}</div></div>',
        unsafe_allow_html=True
    )

def ecard(headline, body, evidence, action, confidence, severity='blue'):
    st.markdown(
        f'<div class="ecard {sev_class(severity)}">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
        f'<div class="ecard-headline">{headline}</div>'
        f'<span class="conf-pill">conf {confidence}</span></div>'
        f'<div class="ecard-body">{body}</div>'
        f'<div class="ecard-evidence">{evidence}</div>'
        f'<div class="ecard-action">→ {action}</div>'
        f'</div>', unsafe_allow_html=True
    )

def pbar(label, amount, total, color):
    pct = min(amount / total * 100, 100) if total > 0 else 0
    st.markdown(
        f'<div class="pbar-wrap">'
        f'<div class="pbar-label"><span>{label}</span>'
        f'<span>${amount:,.0f} · {pct:.0f}%</span></div>'
        f'<div class="pbar-track"><div class="pbar-fill" style="width:{pct:.0f}%;background:{color};"></div></div>'
        f'</div>', unsafe_allow_html=True
    )

def score_box(col, label, val, weight):
    color = '#22c55e' if val > .8 else '#f59e0b' if val > .5 else '#ef4444'
    col.markdown(
        f'<div class="score-box">'
        f'<div class="score-val" style="color:{color};">{val:.2f}</div>'
        f'<div class="score-lbl">{label}</div>'
        f'<div class="score-wt">weight {weight}</div></div>',
        unsafe_allow_html=True
    )


# ── Data loaders ─────────────────────────────────────────────────────────────

@st.cache_data
def load_demo_transactions():
    p = OUTPUT_DIR / "synthetic_transactions_6mo.csv"
    if p.exists():
        df = pd.read_csv(p)
        df['date'] = pd.to_datetime(df['date'])
        return df
    return pd.DataFrame()

@st.cache_data
def load_demo_events():
    p = OUTPUT_DIR / "detected_events.json"
    if p.exists():
        with open(p) as f: return json.load(f)
    return {}

@st.cache_data
def load_demo_reconciliation():
    p = DATA_DIR / "week7_reconciliation_report.json"
    if p.exists():
        with open(p) as f: return json.load(f)
    return {}

@st.cache_resource
def get_explainer():
    try:
        from explainer import FinancialExplainer
        return FinancialExplainer()
    except Exception:
        return None

def run_behavioral_pipeline_ui():
    from pipeline import BehavioralAnalysisPipeline
    goals_path = OUTPUT_DIR / "ground_truth_events.json"
    csv_path = OUTPUT_DIR / "synthetic_transactions_6mo.csv"
    if st.session_state.get("use_uploaded") and st.session_state.get("uploaded_df") is not None:
        csv_path = OUTPUT_DIR / "_session_active.csv"
        st.session_state.uploaded_df.to_csv(csv_path, index=False)
    if not csv_path.exists():
        return False, "No transaction CSV found. Use demo data or upload a CSV."
    try:
        p = BehavioralAnalysisPipeline(
            str(csv_path),
            str(goals_path) if goals_path.exists() else None,
        )
        p.run_analysis()
        p.export_results(str(OUTPUT_DIR / "final_report.json"))
        load_demo_transactions.clear()
        load_demo_events.clear()
        return True, None
    except Exception as e:
        return False, str(e)


def parse_uploaded_csv(uploaded_file) -> pd.DataFrame:
    """Parse any uploaded bank CSV into standard format."""
    df = pd.read_csv(uploaded_file)
    df.columns = df.columns.str.lower().str.strip()
    # Try to map common column names
    rename_map = {}
    for c in df.columns:
        if 'date' in c: rename_map[c] = 'date'
        elif 'amount' in c or 'debit' in c or 'credit' in c: rename_map[c] = 'amount'
        elif 'merchant' in c or 'description' in c or 'narration' in c: rename_map[c] = 'merchant_raw'
        elif 'category' in c: rename_map[c] = 'category'
    df = df.rename(columns=rename_map)
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
    if 'transaction_id' not in df.columns:
        df['transaction_id'] = [f'txn_{i+1:04d}' for i in range(len(df))]
    if 'category' not in df.columns:
        df['category'] = 'uncategorized'
    return df


# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown('<div class="logo">Explain<span class="logo-dot">.</span>YourMoney</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:11px;color:#2a3a56;margin-bottom:18px;">Personal Finance Intelligence</div>', unsafe_allow_html=True)
    st.divider()

    page = st.radio("", [
        "📊  Dashboard",
        "📁  Upload & Process",
        "💳  Transactions",
        "🔗  Reconciliation",
        "🧠  Behavioral Insights",
        "🔍  Evidence Chain",
    ], label_visibility="collapsed")


# ── Load demo data ────────────────────────────────────────────────────────────

demo_df      = load_demo_transactions()
demo_events  = load_demo_events()
demo_recon   = load_demo_reconciliation()
explainer    = get_explainer()

# Session state for uploaded data
if 'uploaded_df' not in st.session_state:
    st.session_state.uploaded_df = None
if 'uploaded_docs' not in st.session_state:
    st.session_state.uploaded_docs = []
if 'use_uploaded' not in st.session_state:
    st.session_state.use_uploaded = False

# Active dataset
active_df = st.session_state.uploaded_df if st.session_state.use_uploaded and st.session_state.uploaded_df is not None else demo_df
all_events = demo_events.get('all_events', {})
top_events = demo_events.get('top_priorities', [])


# ════════════════════════════════════════════════════════════════════════════
# PAGE 1 — DASHBOARD
# ════════════════════════════════════════════════════════════════════════════

if "Dashboard" in page:
    st.markdown("## Financial Dashboard")

    # Data source toggle
    col_l, col_r = st.columns([3, 1])
    with col_r:
        if st.session_state.uploaded_df is not None:
            use_up = st.toggle("Use uploaded data", value=st.session_state.use_uploaded)
            st.session_state.use_uploaded = use_up
        else:
            st.markdown('<div style="font-size:12px;color:#2a3a56;text-align:right;">Using demo data</div>', unsafe_allow_html=True)

    if active_df.empty:
        st.warning("No data loaded. Go to Upload & Process or check that output/synthetic_transactions_6mo.csv exists.")
        st.stop()

    # ── KPI row ──
    income   = active_df[active_df['amount'] > 0]['amount'].sum()
    expenses = active_df[active_df['amount'] < 0]['amount'].abs().sum()
    savings  = income - expenses
    sav_rate = savings / income * 100 if income > 0 else 0

    c1,c2,c3,c4,c5 = st.columns(5)
    kpi(c1, str(len(active_df)),          "Transactions",    None)
    kpi(c2, f"${income:,.0f}",            "Total Income",    "#22c55e")
    kpi(c3, f"${expenses:,.0f}",          "Total Expenses",  "#ef4444")
    kpi(c4, f"${savings:,.0f}",           "Net Savings",     "#3b82f6")
    kpi(c5, f"{sav_rate:.1f}%",           "Avg Savings Rate",None)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Charts ──
    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown('<div class="sec-header">Monthly Spending Trend</div>', unsafe_allow_html=True)
        exp_df = active_df[active_df['amount'] < 0].copy()
        exp_df['month'] = exp_df['date'].dt.to_period('M').astype(str)
        col_name = 'category' if 'category' in exp_df.columns else None
        if col_name:
            monthly = exp_df.groupby(['month', col_name])['amount'].sum().abs().unstack(fill_value=0)
            st.area_chart(monthly, height=220, use_container_width=True)
        else:
            monthly = exp_df.groupby('month')['amount'].sum().abs()
            st.area_chart(monthly, height=220, use_container_width=True)

    with col2:
        st.markdown('<div class="sec-header">Spending by Category</div>', unsafe_allow_html=True)
        if 'category' in active_df.columns:
            cat_totals = active_df[active_df['amount'] < 0].groupby('category')['amount'].sum().abs().sort_values(ascending=False)
            total_exp = cat_totals.sum()
            for cat, amt in cat_totals.head(7).items():
                pbar(cat.title(), amt, total_exp, cat_color(cat))

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Alerts ──
    st.markdown('<div class="sec-header">Active Alerts</div>', unsafe_allow_html=True)
    a1,a2,a3,a4 = st.columns(4)
    kpi(a1, len(all_events.get('spikes',[])),        "Spending Spikes", "#ef4444")
    kpi(a2, len(all_events.get('drifts',[])),         "Category Drifts", "#f59e0b")
    kpi(a3, len(all_events.get('anomalies',[])),      "Anomalies",       "#f97316")
    kpi(a4, len(all_events.get('savings_drops',[])),  "Savings Alerts",  "#3b82f6")

    # ── Top 3 priority events ──
    if top_events:
        st.markdown('<div class="sec-header">Top Priority Events</div>', unsafe_allow_html=True)
        for ev in top_events[:3]:
            if explainer:
                exp = explainer.explain_event(ev)
                ecard(exp['headline'], exp['body'], exp['evidence'],
                      exp['action'], exp['confidence'], ev.get('severity','blue'))
            else:
                st.info(f"{ev.get('type','event')} — {ev.get('category','')}")


# ════════════════════════════════════════════════════════════════════════════
# PAGE 2 — UPLOAD & PROCESS
# ════════════════════════════════════════════════════════════════════════════

elif "Upload" in page:
    st.markdown("## Upload & Process Documents")
    st.markdown('<div style="color:#4a6080;margin-bottom:20px;">Upload your bank data and financial documents to analyze</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="sec-header">Bank Transactions (CSV)</div>', unsafe_allow_html=True)
        st.markdown('<div class="upload-box"><div class="upload-title">📄 Bank Statement CSV</div><div class="upload-sub">Columns: date, amount, description/merchant</div></div>', unsafe_allow_html=True)
        csv_file = st.file_uploader("Upload CSV", type=['csv'], label_visibility='collapsed', key='csv_upload')

        if csv_file:
            try:
                df_up = parse_uploaded_csv(csv_file)
                st.session_state.uploaded_df = df_up
                st.session_state.use_uploaded = True
                st.success(f"✅ Loaded {len(df_up)} transactions")
                st.dataframe(df_up.head(5), use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"Could not parse CSV: {e}")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="sec-header">Bank Statements (Images)</div>', unsafe_allow_html=True)
        st.markdown('<div class="upload-box"><div class="upload-title">🏦 Bank Statement Images</div><div class="upload-sub">PNG, JPG — OCR will extract transactions</div></div>', unsafe_allow_html=True)
        stmt_files = st.file_uploader("Upload statements", type=['png','jpg','jpeg'], accept_multiple_files=True, label_visibility='collapsed', key='stmt_upload')
        if stmt_files:
            st.success(f"✅ {len(stmt_files)} statement(s) uploaded")
            for f in stmt_files:
                img = Image.open(f)
                st.image(img, caption=f.name, width=300)

    with col2:
        st.markdown('<div class="sec-header">Receipt Images</div>', unsafe_allow_html=True)
        st.markdown('<div class="upload-box"><div class="upload-title">🧾 Receipt Images</div><div class="upload-sub">PNG, JPG — OCR extracts merchant, amount, date</div></div>', unsafe_allow_html=True)
        receipt_files = st.file_uploader("Upload receipts", type=['png','jpg','jpeg'], accept_multiple_files=True, label_visibility='collapsed', key='receipt_upload')

        if receipt_files:
            st.success(f"✅ {len(receipt_files)} receipt(s) uploaded")
            cols = st.columns(min(len(receipt_files), 3))
            for i, f in enumerate(receipt_files[:3]):
                with cols[i]:
                    img = Image.open(f)
                    st.image(img, caption=f.name, use_container_width=True)
            st.session_state.uploaded_docs.extend(receipt_files)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="sec-header">Invoice Images</div>', unsafe_allow_html=True)
        st.markdown('<div class="upload-box"><div class="upload-title">📋 Invoice Images</div><div class="upload-sub">PNG, JPG — extracts vendor, amount, line items</div></div>', unsafe_allow_html=True)
        invoice_files = st.file_uploader("Upload invoices", type=['png','jpg','jpeg'], accept_multiple_files=True, label_visibility='collapsed', key='invoice_upload')

        if invoice_files:
            st.success(f"✅ {len(invoice_files)} invoice(s) uploaded")
            cols = st.columns(min(len(invoice_files), 3))
            for i, f in enumerate(invoice_files[:3]):
                with cols[i]:
                    img = Image.open(f)
                    st.image(img, caption=f.name, use_container_width=True)
            st.session_state.uploaded_docs.extend(invoice_files)

    st.divider()

    # ── Process button ──
    total_uploaded = sum([
        1 if csv_file else 0,
        len(stmt_files) if stmt_files else 0,
        len(receipt_files) if receipt_files else 0,
        len(invoice_files) if invoice_files else 0,
    ])

    demo_csv_ok = (OUTPUT_DIR / "synthetic_transactions_6mo.csv").exists()
    if total_uploaded > 0 or demo_csv_ok:
        if st.button("🚀 Run Full Pipeline", type="primary", use_container_width=True):
            with st.spinner("Running behavioral detection (Week 8) on your transactions..."):
                ok, err = run_behavioral_pipeline_ui()
            if ok:
                st.success("✅ Behavioral analysis finished. Dashboard and Behavioral Insights use fresh results.")
                st.info(
                    "Reconciliation page still loads data/week7_reconciliation_report.json. "
                    "Regenerate that file separately (week 7 script) if you need updated matches."
                )
                st.rerun()
            else:
                st.error(err or "Pipeline failed.")
    else:
        st.markdown('<div style="text-align:center;color:#2a3a56;padding:20px;">Upload files above to process them</div>', unsafe_allow_html=True)

    st.divider()
    st.markdown('<div class="sec-header">Or use pre-loaded demo data</div>', unsafe_allow_html=True)
    if st.button("Load Demo Data (6 months synthetic transactions)", use_container_width=True):
        st.session_state.use_uploaded = False
        st.success(f"✅ Demo data loaded — {len(demo_df)} transactions from Jan–Jun 2026")


# ════════════════════════════════════════════════════════════════════════════
# PAGE 3 — TRANSACTIONS
# ════════════════════════════════════════════════════════════════════════════

elif "Transactions" in page:
    st.markdown("## Transactions")

    if active_df.empty:
        st.warning("No transaction data. Upload a CSV or load demo data.")
        st.stop()

    # ── Filters ──
    c1, c2, c3 = st.columns(3)
    with c1:
        cats = ['All']
        if 'category' in active_df.columns:
            cats += sorted(active_df['category'].dropna().unique().tolist())
        sel_cat = st.selectbox("Category", cats)
    with c2:
        months = ['All'] + sorted(active_df['date'].dt.to_period('M').astype(str).unique().tolist())
        sel_month = st.selectbox("Month", months)
    with c3:
        merchant_col = next((c for c in ['merchant_raw','merchant_canonical','merchant_key'] if c in active_df.columns), None)
        search = st.text_input("Search merchant", placeholder="e.g. Starbucks")

    filtered = active_df.copy()
    if sel_cat != 'All' and 'category' in filtered.columns:
        filtered = filtered[filtered['category'] == sel_cat]
    if sel_month != 'All':
        filtered = filtered[filtered['date'].dt.to_period('M').astype(str) == sel_month]
    if search and merchant_col:
        filtered = filtered[filtered[merchant_col].astype(str).str.contains(search, case=False, na=False)]

    # ── Summary row ──
    col1,col2,col3 = st.columns(3)
    kpi(col1, str(len(filtered)),                       "Transactions",   None)
    kpi(col2, f"${filtered[filtered['amount']<0]['amount'].abs().sum():,.0f}", "Total Spent", "#ef4444")
    kpi(col3, f"${filtered[filtered['amount']>0]['amount'].sum():,.0f}",       "Total Income","#22c55e")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Table ──
    display_cols = ['transaction_id','date','amount']
    if merchant_col: display_cols.append(merchant_col)
    if 'category' in filtered.columns: display_cols.append('category')
    if 'pattern_tag' in filtered.columns: display_cols.append('pattern_tag')

    show = filtered[display_cols].copy()
    show['date'] = show['date'].dt.strftime('%Y-%m-%d')
    show['amount'] = show['amount'].apply(lambda x: f"${x:+,.2f}")

    st.dataframe(show, use_container_width=True, height=420, hide_index=True)

    # ── Category breakdown chart ──
    if 'category' in active_df.columns:
        st.markdown('<div class="sec-header">Monthly Category Breakdown</div>', unsafe_allow_html=True)
        plot_df = active_df[active_df['amount'] < 0].copy()
        plot_df['month'] = plot_df['date'].dt.to_period('M').astype(str)
        pivot = plot_df.groupby(['month','category'])['amount'].sum().abs().unstack(fill_value=0)
        if not pivot.empty:
            st.bar_chart(pivot, height=260, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE 4 — RECONCILIATION
# ════════════════════════════════════════════════════════════════════════════

elif "Reconciliation" in page:
    st.markdown("## Transaction ↔ Document Reconciliation")
    st.markdown('<div style="color:#4a6080;margin-bottom:20px;">3-tier matching: Exact → Fuzzy → Semantic with confidence scores and AI explanations</div>', unsafe_allow_html=True)

    if not demo_recon:
        st.warning("No reconciliation data found. Make sure data/week7_reconciliation_report.json exists.")
        st.info("Run: cd week7_reconciliation && python reconciliation_engine.py")
        st.stop()

    stats = demo_recon.get('statistics', {})
    pipeline_stats = stats.get('pipeline', stats)
    matches      = demo_recon.get('matches', [])
    unsupported  = demo_recon.get('unsupported', demo_recon.get('unsupported_transaction_ids', []))
    unreconciled = demo_recon.get('unreconciled', demo_recon.get('unreconciled_document_ids', []))

    # ── KPIs ──
    c1,c2,c3,c4,c5 = st.columns(5)
    kpi(c1, len(matches),                              "Matched",          "#22c55e")
    kpi(c2, pipeline_stats.get('exact_matches',0),     "Exact",            "#22c55e")
    kpi(c3, pipeline_stats.get('fuzzy_matches',0),     "Fuzzy",            "#f59e0b")
    kpi(c4, pipeline_stats.get('semantic_matches',0),  "Semantic",         "#3b82f6")
    kpi(c5, len(unsupported),                          "Unsupported",      "#ef4444")

    match_rate = stats.get('match_rate', len(matches)/(len(matches)+len(unsupported)) if (len(matches)+len(unsupported))>0 else 0)
    st.progress(match_rate, text=f"Match rate: {match_rate:.0%}")

    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["✅  Matched Pairs", "⚠️  Unsupported Transactions", "📄  Unreconciled Documents"])

    with tab1:
        if not matches:
            st.info("No matches in reconciliation data.")
        else:
            for match in matches:
                mt = match.get('match_type','UNKNOWN')
                badge_cls = {'EXACT':'badge-exact','FUZZY':'badge-fuzzy','SEMANTIC':'badge-semantic'}.get(mt,'badge-exact')
                conf  = match.get('confidence', 0)
                tx_id = match.get('transaction_id','')
                doc_id= match.get('document_id','')

                if explainer:
                    explanation = explainer.explain_reconciliation_match(match)
                else:
                    explanation = match.get('reasoning','')

                st.markdown(
                    f'<div class="ecard">'
                    f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
                    f'<span class="badge {badge_cls}">{mt}</span>'
                    f'<span style="color:#e2e8f8;font-size:13px;font-weight:500;">{tx_id} → {doc_id}</span>'
                    f'<span class="conf-pill">conf {conf:.3f}</span></div>'
                    f'<div class="ecard-body">{explanation}</div>'
                    f'</div>', unsafe_allow_html=True
                )

                components = match.get('components', {})
                if components:
                    sc1,sc2,sc3,sc4 = st.columns(4)
                    score_box(sc1, "Merchant Similarity", components.get('string_similarity',0), "×0.4")
                    score_box(sc2, "Amount Match",        components.get('amount_match',0),       "×0.3")
                    score_box(sc3, "Date Proximity",      components.get('date_proximity',0),      "×0.2")
                    score_box(sc4, "Document Trust",      components.get('document_trust',0),      "×0.1")

    with tab2:
        if not unsupported:
            st.success("All transactions have supporting documents.")
        else:
            for item in unsupported:
                if isinstance(item, dict):
                    reason = item.get('reason','No document found')
                    amount = item.get('amount', 0)
                    merchant = item.get('merchant','N/A')
                    label = item.get('label','Card transaction')
                    st.markdown(
                        f'<div class="ecard red">'
                        f'<div class="ecard-headline">🔴 {item.get("transaction_id",item)} — {label}</div>'
                        f'<div class="ecard-body">'
                        f'Merchant: <b style="color:#e2e8f8">{merchant}</b> · '
                        f'Amount: <b style="color:#e2e8f8">${amount:,.2f}</b> · '
                        f'Reason: {reason}</div>'
                        f'</div>', unsafe_allow_html=True
                    )
                else:
                    st.markdown(f'<div class="ecard red"><div class="ecard-headline">🔴 {item}</div></div>', unsafe_allow_html=True)

    with tab3:
        if not unreconciled:
            st.success("All documents matched to transactions.")
        else:
            for item in unreconciled:
                if isinstance(item, dict):
                    label = item.get('label','Possible cash purchase')
                    reason = item.get('reason','No transaction found')
                    amount = item.get('amount')
                    amt_str = f"${amount:,.2f}" if amount is not None else "unknown"
                    st.markdown(
                        f'<div class="ecard amber">'
                        f'<div class="ecard-headline">📄 {item.get("document_id",item)} — {label}</div>'
                        f'<div class="ecard-body">'
                        f'Merchant: <b style="color:#e2e8f8">{item.get("merchant","N/A")}</b> · '
                        f'Amount: <b style="color:#e2e8f8">{amt_str}</b> · '
                        f'Trust score: {item.get("trust_score",0):.2f} · '
                        f'Reason: {reason}</div>'
                        f'</div>', unsafe_allow_html=True
                    )
                else:
                    st.markdown(f'<div class="ecard amber"><div class="ecard-headline">📄 {item}</div></div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# PAGE 5 — BEHAVIORAL INSIGHTS
# ════════════════════════════════════════════════════════════════════════════

elif "Behavioral" in page:
    st.markdown("## Behavioral Insights")
    st.markdown('<div style="color:#4a6080;margin-bottom:20px;">Statistical detection: Z-score spikes, IQR anomalies, category drift, savings analysis</div>', unsafe_allow_html=True)

    if not all_events:
        st.warning("No behavioral data. Run: cd week8 && python pipeline.py")
        st.stop()

    # ── Priority events ──
    if top_events:
        st.markdown('<div class="sec-header">Priority Events — AI Explained</div>', unsafe_allow_html=True)
        for ev in top_events[:6]:
            if explainer:
                exp = explainer.explain_event(ev)
                ecard(exp['headline'], exp['body'], exp['evidence'],
                      exp['action'], exp['confidence'], ev.get('severity','blue'))
            else:
                st.json(ev)

    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔺 Spikes", "📊 Drift", "⚠️ Anomalies", "💰 Savings", "🎯 Goals"
    ])

    with tab1:
        spikes = all_events.get('spikes', [])
        if not spikes:
            st.info("No spending spikes detected in this dataset.")
            st.markdown('<div style="font-size:12px;color:#3b5080;">Tip: Apply the .shift(1) fix in analyzer.py detect_spikes() to improve detection.</div>', unsafe_allow_html=True)
        else:
            for s in spikes:
                if explainer:
                    exp = explainer.explain_spike(s)
                    ecard(exp['headline'], exp['body'], exp['evidence'], exp['action'], exp['confidence'], 'red')

    with tab2:
        drifts = all_events.get('drifts', [])
        if not drifts:
            st.info("No category drift detected.")
        else:
            for d in drifts:
                if explainer:
                    exp = explainer.explain_drift(d)
                    ecard(exp['headline'], exp['body'], exp['evidence'], exp['action'], exp['confidence'], 'amber')
                else:
                    st.json(d)

    with tab3:
        anomalies = all_events.get('anomalies', [])
        if not anomalies:
            st.info("No anomalies detected.")
        else:
            for a in anomalies:
                if explainer:
                    exp = explainer.explain_anomaly(a)
                    ecard(exp['headline'], exp['body'], exp['evidence'], exp['action'], exp['confidence'],
                          'red' if a.get('severity')=='high' else 'amber')
                else:
                    st.json(a)

    with tab4:
        drops = all_events.get('savings_drops', [])
        if drops:
            for s in drops:
                if explainer:
                    exp = explainer.explain_savings_drop(s)
                    ecard(exp['headline'], exp['body'], exp['evidence'], exp['action'], exp['confidence'], 'red')

        # ── Savings chart ──
        if not active_df.empty:
            st.markdown('<div class="sec-header">Savings Rate Over Time</div>', unsafe_allow_html=True)
            df_s = active_df.copy()
            df_s['month'] = df_s['date'].dt.to_period('M').astype(str)
            inc_m = df_s[df_s['amount']>0].groupby('month')['amount'].sum()
            exp_m = df_s[df_s['amount']<0].groupby('month')['amount'].sum().abs()
            sav_r = ((inc_m - exp_m) / inc_m * 100).fillna(0).clip(-100, 100)
            st.line_chart(sav_r, height=200, use_container_width=True)

    with tab5:
        goals = all_events.get('goals', [])
        if not goals:
            st.info("No goal tracking data.")
        else:
            # Show only exceeded or below target — filter noise
            important_goals = [g for g in goals if g.get('status') in ('exceeded','below_target')]
            on_track = [g for g in goals if g.get('status') not in ('exceeded','below_target')]

            if important_goals:
                st.markdown('<div class="sec-header">Goals Needing Attention</div>', unsafe_allow_html=True)
                for g in important_goals:
                    if explainer:
                        exp = explainer.explain_goal_status(g)
                        ecard(exp['headline'], exp['body'], exp['evidence'], exp['action'], exp['confidence'], 'red')

            if on_track:
                st.markdown('<div class="sec-header">Goals on Track</div>', unsafe_allow_html=True)
                for g in on_track[:4]:
                    if explainer:
                        exp = explainer.explain_goal_status(g)
                        ecard(exp['headline'], exp['body'], exp['evidence'], exp['action'], exp['confidence'], 'green')


# ════════════════════════════════════════════════════════════════════════════
# PAGE 6 — EVIDENCE CHAIN
# ════════════════════════════════════════════════════════════════════════════

elif "Evidence" in page:
    st.markdown("## Evidence Chain")
    st.markdown('<div style="color:#4a6080;margin-bottom:20px;">Every financial claim is traceable — from source document to final confidence score</div>', unsafe_allow_html=True)

    # ── How it works ──
    st.markdown('<div class="sec-header">How Evidence Chains Work</div>', unsafe_allow_html=True)

    stages = [
        ("📷","Document Uploaded","Receipt / invoice / statement image"),
        ("🔍","OCR Extraction","Tesseract extracts raw text"),
        ("📊","Quality Scoring","Sharpness × Noise × Contrast → 0–1"),
        ("🏷️","Type Detection","Receipt / Statement / Invoice"),
        ("✂️","Field Extraction","Merchant, date, amount, items"),
        ("✅","Trust Scoring","image×0.3 + ocr×0.3 + completeness×0.2 + consistency×0.2"),
        ("🔗","Reconciliation","Match to bank transaction (3-tier)"),
    ]
    cols = st.columns(len(stages))
    for col, (icon, name, detail) in zip(cols, stages):
        with col:
            st.markdown(
                f'<div class="score-box">'
                f'<div style="font-size:18px;">{icon}</div>'
                f'<div class="score-lbl" style="color:#8899bb;font-size:11px;margin-top:5px;">{name}</div>'
                f'<div class="score-wt">{detail}</div></div>',
                unsafe_allow_html=True
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Sample chain ──
    st.markdown('<div class="sec-header">Sample Evidence Chain — Interactive</div>', unsafe_allow_html=True)

    sample = {
        "claim": "You spent $39.12 at Trader Joe's on February 7, 2026",
        "links": [
            "Quality score: 0.89 — image is sharp and clear",
            "OCR confidence: 0.95 — text extracted successfully",
            "Merchant: Trader Joe's | Total: $39.12 | Date: 2026-02-07 | Items: 4",
            "Trust score: 0.87 → status: verified",
            "Matched to bank transaction — confidence: 0.96 (exact amount, date, merchant)",
        ],
        "composite_confidence": 0.96,
        "status": "verified"
    }

    st.markdown(
        f'<div class="ecard green">'
        f'<div style="font-size:10px;color:#2a4a30;font-family:JetBrains Mono,monospace;margin-bottom:5px;">CLAIM</div>'
        f'<div class="ecard-headline">"{sample["claim"]}"</div>'
        f'<div style="font-size:11px;color:#2a4a30;margin-top:10px;">'
        f'Source: uploaded receipt image</div></div>',
        unsafe_allow_html=True
    )

    for i, result in enumerate(sample['links']):
        connector_color = "#22c55e" if i == len(sample['links'])-1 else "#1e2d4a"
        st.markdown(
            f'<div style="display:flex;gap:14px;margin-bottom:6px;padding-left:16px;">'
            f'<div style="width:1px;background:{connector_color};margin:0 11px;min-height:40px;"></div>'
            f'<div style="background:#0f172a;border:1px solid #1e2d4a;border-radius:7px;padding:10px 14px;flex:1;">'
            f'<div style="font-size:12px;color:#7a90b8;">{result}</div>'
            f'</div></div>',
            unsafe_allow_html=True
        )

    st.markdown(
        f'<div style="background:#14532d;border:1px solid #22c55e;border-radius:7px;padding:10px 16px;margin-top:4px;">'
        f'<span style="color:#4ade80;font-weight:500;">✓ Verified</span>'
        f'<span style="color:#6b80a8;font-size:12px;margin-left:12px;">'
        f'Composite confidence: {sample["composite_confidence"]}</span>'
        f'</div>',
        unsafe_allow_html=True
    )

    # ── Live match inspector ──
    if demo_recon and demo_recon.get('matches'):
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="sec-header">Inspect Live Match from Reconciliation</div>', unsafe_allow_html=True)

        matches = demo_recon['matches']
        sel = st.selectbox(
            "Select a match",
            range(len(matches)),
            format_func=lambda i: f"{matches[i].get('transaction_id')} ↔ {matches[i].get('document_id')} [{matches[i].get('match_type')}] conf={matches[i].get('confidence',0):.3f}"
        )
        m = matches[sel]

        if explainer:
            explanation = explainer.explain_reconciliation_match(m)
        else:
            explanation = m.get('reasoning', '')

        mt = m.get('match_type','UNKNOWN')
        badge_cls = {'EXACT':'badge-exact','FUZZY':'badge-fuzzy','SEMANTIC':'badge-semantic'}.get(mt,'badge-exact')

        st.markdown(
            f'<div class="ecard">'
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
            f'<span class="badge {badge_cls}">{mt}</span>'
            f'<span style="color:#e2e8f8;font-weight:500;">{m.get("transaction_id")} ↔ {m.get("document_id")}</span>'
            f'<span class="conf-pill">conf {m.get("confidence",0):.4f}</span></div>'
            f'<div class="ecard-body">{explanation}</div>'
            f'<div class="ecard-evidence">'
            f'Date offset: {m.get("date_offset_days",0)} days · '
            f'Amount discrepancy: {m.get("amount_discrepancy","None")} · '
            f'Reasoning: {m.get("reasoning","")}'
            f'</div></div>',
            unsafe_allow_html=True
        )

        components = m.get('components', {})
        if components:
            sc1,sc2,sc3,sc4 = st.columns(4)
            score_box(sc1, "Merchant Similarity", components.get('string_similarity',0), "×0.4")
            score_box(sc2, "Amount Match",        components.get('amount_match',0),       "×0.3")
            score_box(sc3, "Date Proximity",      components.get('date_proximity',0),      "×0.2")
            score_box(sc4, "Document Trust",      components.get('document_trust',0),      "×0.1")

            # Confidence formula
            conf = m.get('confidence', 0)
            ss = components.get('string_similarity',0)
            am = components.get('amount_match',0)
            dp = components.get('date_proximity',0)
            dt = components.get('document_trust',0)
            st.markdown(
                f'<div class="ecard-evidence" style="margin-top:10px;">'
                f'Confidence formula: ({ss:.2f}×0.4) + ({am:.2f}×0.3) + ({dp:.2f}×0.2) + ({dt:.2f}×0.1) = <b style="color:#e2e8f8">{conf:.4f}</b>'
                f'</div>',
                unsafe_allow_html=True
            )