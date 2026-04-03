import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import json
import calendar

# Seed for reproducibility
random.seed(42)
np.random.seed(42)

# MERCHANT CONFIGURATION 
MERCHANTS = {
    'starbucks': {
        'templates': [
            "SQ * STARBUCKS #{} {}",
            "STARBUCKS COFFEE #{}",
            "SQ *SQ *STARBUCKS {}"
        ],
        'category': 'dining',
        'amount_range': (4.50, 8.50),
        'frequency': 'high'  # 2-3x per week
    },
    'mcdonalds': {
        'templates': ["MCDONALD'S #{} {}"],
        'category': 'dining',
        'amount_range': (8.00, 15.00),
        'frequency': 'medium'  # 1-2x per week
    },
    'uber_eats': {
        'templates': ["UBER EATS HELP.UBER.COM"],
        'category': 'dining',
        'amount_range': (25.00, 45.00),
        'frequency': 'medium'
    },
    'whole_foods': {
        'templates': ["TST* WHOLE FOODS MKT #{} {}"],
        'category': 'groceries',
        'amount_range': (60.00, 140.00),
        'frequency': 'weekly'
    },
    'walmart': {
        'templates': ["WAL-MART #{} SUPER CENTER", "WALMART.COM - {} AR"],
        'category': 'groceries',
        'amount_range': (40.00, 120.00),
        'frequency': 'weekly'
    },
    'shell_gas': {
        'templates': ["SHELL OIL {}57420389"],
        'category': 'transportation',
        'amount_range': (35.00, 55.00),
        'frequency': 'weekly'
    },
    'cvs': {
        'templates': ["CVS/PHARMACY #{} {}", "CVS PHARMACY #{} {}"],
        'category': 'healthcare',
        'amount_range': (15.00, 40.00),
        'frequency': 'low'
    },
    'amazon': {
        'templates': ["AMAZON.COM*{} {}", "AMAZON MARKETPLACE {}"],
        'category': 'shopping',
        'amount_range': (20.00, 80.00),
        'frequency': 'medium'
    },
    'netflix': {
        'templates': ["NETFLIX.COM {} CA"],
        'category': 'entertainment',
        'amount_range': (15.49, 15.49),
        'frequency': 'monthly_fixed'
    },
    'spotify': {
        'templates': ["SPOTIFY USA"],
        'category': 'entertainment',
        'amount_range': (9.99, 9.99),
        'frequency': 'monthly_fixed'
    },
    'att': {
        'templates': ["ATT MOBILE PAYMENT {}"],
        'category': 'utilities',
        'amount_range': (75.00, 75.00),
        'frequency': 'monthly_fixed'
    },
    'electric': {
        'templates': ["ELECTRIC COMPANY BILL {}"],
        'category': 'utilities',
        'amount_range': (85.00, 120.00),
        'frequency': 'monthly_variable'
    },
    'payroll': {
        'templates': ["DIRECT DEPOSIT PAYROLL {}"],
        'category': 'income',
        'amount_range': (3200.00, 3200.00),
        'frequency': 'biweekly_fixed'
    }
}

# PATTERN INJECTION CONFIGURATION

PATTERNS = {
    'dining_spike': {
        'month': 4,  # April
        'category': 'dining',
        'multiplier': 2.5,  # 150% increase
        'description': 'Dining spending increases 150% due to social events'
    },
    'grocery_drift': {
        'start_month': 4,  # April
        'category': 'groceries',
        'monthly_increase_pct': 0.10,  # 10% per month
        'description': 'Grocery spending increases 10% monthly for 3 months'
    },
    'anomaly_transaction': {
        'month': 5,  # May
        'day': 15,
        'category': 'shopping',
        'multiplier': 3.5,  # 3.5x normal amount
        'description': 'Single large purchase (electronics) - 3.5x normal'
    },
    'savings_drop': {
        'month': 5,  # May
        'income_reduction': 0.20,  # 20% less income
        'spending_increase': 0.15,  # 15% more spending
        'description': 'Savings rate drops from ~20% to ~12%'
    }
}

# User goals for tracking
USER_GOALS = {
    'dining_budget': {'limit': 400, 'period': 'monthly'},
    'grocery_budget': {'limit': 600, 'period': 'monthly'},
    'savings_rate': {'target': 0.20, 'period': 'monthly'}  # 20%
}


def generate_merchant_name(merchant_key, templates):
    """Generate realistic merchant name with variations"""
    store_num = random.randint(1000, 9999)
    city = random.choice(['NEW YORK', 'CHICAGO', 'SAN FRANCISCO', 'MIAMI', 'SEATTLE', 'AUSTIN'])
    template = random.choice(templates)
    try:
        return template.format(store_num, city)
    except:
        try:
            return template.format(store_num)
        except:
            return template.format(city)


def get_frequency_count(frequency_type):
    """Convert frequency type to transaction count per month"""
    freq_map = {
        'high': (8, 12),      # 2-3x per week
        'medium': (4, 8),     # 1-2x per week  
        'weekly': (3, 5),     # ~1x per week
        'low': (1, 3),        # occasional
        'monthly_fixed': (1, 1),
        'monthly_variable': (1, 1),
        'biweekly_fixed': (2, 2)
    }
    return random.randint(*freq_map.get(frequency_type, (1, 3)))


def generate_base_amount(merchant_info, month_num=None, is_anomaly=False):
    """Generate amount with optional pattern adjustments"""
    min_amt, max_amt = merchant_info['amount_range']
    base_amount = random.uniform(min_amt, max_amt)
    
    # Apply grocery drift (Months 4-6)
    if month_num and merchant_info['category'] == 'groceries' and month_num >= 4:
        drift_months = month_num - 3  # Months 4,5,6 -> 1,2,3
        increase_factor = 1 + (PATTERNS['grocery_drift']['monthly_increase_pct'] * drift_months)
        base_amount *= increase_factor
    
    # Apply dining spike (Month 4)
    if month_num == 4 and merchant_info['category'] == 'dining':
        base_amount *= PATTERNS['dining_spike']['multiplier']
    
    # Apply anomaly (Month 5, specific transaction)
    if is_anomaly:
        base_amount *= PATTERNS['anomaly_transaction']['multiplier']
    
    return round(base_amount, 2)


def generate_dataset():
    """Generate 6-month synthetic transaction dataset with controlled patterns"""
    transactions = []
    txn_id = 1
    
    print("=" * 60)
    print("GENERATING 6-MONTH SYNTHETIC DATASET WITH PATTERNS")
    print("=" * 60)
    
    # Generate month by month to control patterns
    for month in range(1, 7):  # Jan-Jun
        _, days_in_month = calendar.monthrange(2026, month)
        
        print(f"\nGenerating {calendar.month_name[month]} 2026...")
        
        for merchant_key, merchant_info in MERCHANTS.items():
            category = merchant_info['category']
            freq_type = merchant_info['frequency']
            
            # Determine count for this month
            count = get_frequency_count(freq_type)
            
            # Handle savings drop pattern (Month 5 - May)
            if month == 5:
                if category == 'income':
                    # Reduce income frequency (simulate missed paycheck)
                    count = max(1, count - 1)
                elif category in ['dining', 'shopping', 'entertainment']:
                    # Increase discretionary spending
                    count = int(count * 1.5)
            
            # Generate transactions for this merchant this month
            for i in range(count):
                # Determine date based on frequency type
                if freq_type in ['monthly_fixed', 'monthly_variable']:
                    day = random.choice([1, 2, 3, days_in_month-2, days_in_month-1, days_in_month])
                elif freq_type == 'biweekly_fixed':
                    day = random.choice([1, 2, 15, 16])
                else:
                    day = random.randint(1, days_in_month)
                
                day = min(day, days_in_month)
                date = datetime(2026, month, day)
                
                # Check for anomaly injection (May 15th shopping transaction)
                is_anomaly = False
                if (month == PATTERNS['anomaly_transaction']['month'] and 
                    day == PATTERNS['anomaly_transaction']['day'] and
                    category == PATTERNS['anomaly_transaction']['category'] and
                    i == 0):
                    is_anomaly = True
                    print(f"  [PATTERN] Injecting ANOMALY: {merchant_key} on {date.date()} (3.5x normal)")
                
                # Generate amount
                amount = generate_base_amount(merchant_info, month, is_anomaly)
                
                # Income is positive, expenses negative
                if category == 'income':
                    amount = abs(amount)
                else:
                    amount = -abs(amount)
                
                # Generate merchant name
                merchant_raw = generate_merchant_name(merchant_key, merchant_info['templates'])
                
                # Determine pattern tag
                if is_anomaly:
                    pattern_tag = 'anomaly'
                elif month == 4 and category == 'dining':
                    pattern_tag = 'dining_spike'
                elif month >= 4 and category == 'groceries':
                    pattern_tag = 'grocery_drift'
                elif month == 5:
                    pattern_tag = 'savings_drop'
                else:
                    pattern_tag = 'baseline'
                
                transactions.append({
                    'transaction_id': f'txn_{txn_id:04d}',
                    'date': date.strftime('%Y-%m-%d'),
                    'amount': amount,
                    'merchant_raw': merchant_raw,
                    'merchant_key': merchant_key,
                    'category': category,
                    'is_recurring': freq_type.endswith('_fixed') or freq_type.endswith('_variable'),
                    'is_anomaly': is_anomaly,
                    'pattern_tag': pattern_tag
                })
                
                txn_id += 1
    
    # Create DataFrame
    df = pd.DataFrame(transactions)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    
    # Recalculate transaction IDs after sorting
    df['transaction_id'] = [f'txn_{i+1:04d}' for i in range(len(df))]
    
    # Force inject anomaly if not found (safety check)
    if not df['is_anomaly'].any():
        print("[WARNING] No anomaly found! Injecting manually...")
        anomaly_row = {
            'transaction_id': f'txn_{len(df)+1:04d}',
            'date': pd.Timestamp('2026-05-15'),
            'amount': -280.00,
            'merchant_raw': 'AMAZON.COM*9999 SEATTLE',
            'merchant_key': 'amazon',
            'category': 'shopping',
            'is_recurring': False,
            'is_anomaly': True,
            'pattern_tag': 'anomaly'
        }
        df = pd.concat([df, pd.DataFrame([anomaly_row])], ignore_index=True)
        df = df.sort_values('date').reset_index(drop=True)
        df['transaction_id'] = [f'txn_{i+1:04d}' for i in range(len(df))]
    
    return df


def save_dataset(df, output_dir='.'):
    """Save dataset and ground truth to files"""
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    # Save transactions
    csv_path = f'{output_dir}/synthetic_transactions_6mo.csv'
    df.to_csv(csv_path, index=False)
    print(f"\nSaved to: {csv_path}")
    
    # Save ground truth
    ground_truth = {
        'patterns': PATTERNS,
        'user_goals': USER_GOALS,
        'expected_detections': [
            {'type': 'spike', 'month': 4, 'category': 'dining', 'expected_increase_pct': 150},
            {'type': 'drift', 'start_month': 4, 'category': 'groceries', 'months': [4,5,6], 'monthly_increase_pct': 10},
            {'type': 'anomaly', 'month': 5, 'day': 15, 'category': 'shopping', 'multiplier': 3.5},
            {'type': 'savings_drop', 'month': 5, 'expected_rate_before': 0.20, 'expected_rate_after': 0.12}
        ],
        'metadata': {
            'total_transactions': len(df),
            'date_range': {'start': '2026-01-01', 'end': '2026-06-30'},
            'generation_date': '2026-04-03'
        }
    }
    
    json_path = f'{output_dir}/ground_truth_events.json'
    with open(json_path, 'w') as f:
        json.dump(ground_truth, f, indent=2)
    print(f"Ground truth saved to: {json_path}")
    
    return csv_path, json_path


if __name__ == "__main__":
    df = generate_dataset()
    
    print(f"\n{'='*60}")
    print(f"DATASET GENERATION COMPLETE")
    print(f"{'='*60}")
    print(f"Total transactions: {len(df)}")
    print(f"Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"\nCategory distribution:")
    print(df['category'].value_counts().sort_index())
    print(f"\nPattern tags:")
    print(df['pattern_tag'].value_counts())
    
    # Save files
    save_dataset(df, output_dir='output')