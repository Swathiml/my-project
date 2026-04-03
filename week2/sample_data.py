from faker import Faker
import pandas as pd
import random
from datetime import datetime, timedelta

# ===== STABLE DATASET MODE =====
random.seed(42)
Faker.seed(42)

fake = Faker()

MERCHANTS = {
    'starbucks': {
        'templates': [
            "SQ * STARBUCKS #{} {}",
            "STARBUCKS COFFEE #{}",
            "SQ *SQ *STARBUCKS SAN FRANCISCO",
        ],
        'category': 'food and dining',
        'amount_range': (4.50, 12.00),
        'recurring': False
    },
    'mcdonalds': {
        'templates': ["MCDONALD'S #{} CHICAGO"],
        'category': 'food and dining',
        'amount_range': (6.00, 18.00),
        'recurring': False
    },
    'uber_eats': {
        'templates': ["UBER EATS HELP.UBER.COM"],
        'category': 'food and dining',
        'amount_range': (18.00, 45.00),
        'recurring': False
    },
    'coffee_shop': {
        'templates': [
            "SQ *SQ *COFFEE SHOP SAN FRANCISCO",
            "SQ * COFFEE SHOP #{} SF"
        ],
        'category': 'food and dining',
        'amount_range': (4.00, 8.00),
        'recurring': False
    },
    'whole_foods': {
        'templates': ["TST* WHOLE FOODS MKT #{}"],
        'category': 'groceries',
        'amount_range': (45.00, 180.00),
        'recurring': False
    },
    'amazon': {
        'templates': [
            "AMAZON.COM*{} SEATTLE",
            "AMAZON MARKETPLACE SEATTLE",
        ],
        'category': 'shopping',
        'amount_range': (15.00, 120.00),
        'recurring': False
    },
    'target': {
        'templates': [
            "TARGET {} MINNEAPOLIS",
            "TARGET STORE #{} CHICAGO"
        ],
        'category': 'shopping',
        'amount_range': (25.00, 150.00),
        'recurring': False
    },
    'walmart': {
        'templates': [
            "WAL-MART #{} SUPER CENTER",
            "WALMART.COM - {} AR"
        ],
        'category': 'shopping',
        'amount_range': (30.00, 200.00),
        'recurring': False
    },
    'netflix': {
        'templates': [
            "NETFLIX.COM {} CA",
            "PAYPAL *NETFLIX NETFLIX.COM"
        ],
        'category': 'entertainment',
        'amount_range': (15.49, 15.49),
        'recurring': True,
        'interval_days': 30
    },
    'spotify': {
        'templates': ["SPOTIFY USA"],
        'category': 'entertainment',
        'amount_range': (9.99, 9.99),
        'recurring': True,
        'interval_days': 30
    },
    'shell_oil': {
        'templates': ["SHELL OIL {}57420389"],
        'category': 'transportation',
        'amount_range': (35.00, 65.00),
        'recurring': False
    },
    'mta': {
        'templates': ["MTA*NYCT PAYGO NEW YORK NY"],
        'category': 'transportation',
        'amount_range': (2.90, 2.90),
        'recurring': False
    },
    'cvs': {
        'templates': [
            "CVS/PHARMACY #{} MIAMI",
            "CVS PHARMACY #{} ORLANDO"
        ],
        'category': 'healthcare',
        'amount_range': (12.00, 45.00),
        'recurring': False
    },
    'att': {
        'templates': ["ATT MOBILE PAYMENT {}"],
        'category': 'utilities',
        'amount_range': (65.00, 85.00),
        'recurring': True,
        'interval_days': 30
    },
    'payroll': {
        'templates': ["DIRECT DEPOSIT PAYROLL"],
        'category': 'income',
        'amount_range': (2500.00, 4500.00),
        'recurring': True,
        'interval_days': 14
    },
    'online_payment': {
        'templates': ["ONLINE PAYMENT - THANK YOU"],
        'category': 'transfer',
        'amount_range': (100.00, 500.00),
        'recurring': False
    },
    'hotel': {
        'templates': [
            "HILTON HOTELS #{} {}",
            "MARRIOTT {} RESERVATION",
            "BOOKING.COM *HOTEL {}"
        ],
        'category': 'travel',
        'amount_range': (120.00, 350.00),
        'recurring': False
    },
    'airline': {
        'templates': [
            "DELTA AIR {} FLIGHT",
            "UNITED AIRLINES {}"
        ],
        'category': 'travel',
        'amount_range': (200.00, 800.00),
        'recurring': False
    },
    'adobe': {
        'templates': [
            "ADOBE *CREATIVE CLOUD",
            "ADOBE SYSTEMS INC"
        ],
        'category': 'subscriptions',
        'amount_range': (52.99, 52.99),
        'recurring': True,
        'interval_days': 30
    },
    'github': {
        'templates': ["GITHUB.COM *PRO PLAN"],
        'category': 'subscriptions',
        'amount_range': (4.00, 21.00),
        'recurring': True,
        'interval_days': 30
    },
    'bank_fee': {
        'templates': [
            "LATE FEE",
            "OVERDRAFT FEE",
            "MONTHLY SERVICE FEE",
            "ATM FEE"
        ],
        'category': 'fees',
        'amount_range': (15.00, 35.00),
        'recurring': False
    }
}

def generate_recurring_dates(start_date, num_occurrences, interval_days):
    dates = []
    current = start_date
    for _ in range(num_occurrences):
        dates.append(current)
        current = current + timedelta(days=interval_days)
    return dates

def generate_dataset():
    transactions = []
    txn_id = 1
    start_date = datetime(2026, 2, 17) - timedelta(days=90)
    
    print("Generating recurring transactions...")
    recurring_configs = [
        ('netflix', 4),
        ('spotify', 4),
        ('att', 3),
        ('adobe', 3),
        ('github', 3),
        ('payroll', 6),
    ]
    
    for merchant_key, num_occurrences in recurring_configs:
        merchant_info = MERCHANTS[merchant_key]
        interval = merchant_info.get('interval_days', 30)
        base_dates = generate_recurring_dates(start_date, num_occurrences, interval)
        
        for i, base_date in enumerate(base_dates):
            variation = random.randint(-2, 2)
            actual_date = base_date + timedelta(days=variation)
            amount = merchant_info['amount_range'][0] + random.uniform(-0.01, 0.01)
            
            template = random.choice(merchant_info['templates'])
            store_num = random.randint(1000, 9999)
            city = fake.city().upper()
            try:
                merchant_raw = template.format(store_num, city)
            except:
                try:
                    merchant_raw = template.format(store_num)
                except:
                    merchant_raw = template
            
            transactions.append({
                'transaction_id': f'txn_{txn_id:03d}',
                'date': actual_date.strftime('%Y-%m-%d'),
                'amount': -amount if merchant_info['category'] != 'income' else amount,
                'merchant_raw': merchant_raw,
                'description': 'Recurring Payment' if merchant_info['category'] != 'income' else 'Deposit',
                'category_hint': merchant_info['category']
            })
            txn_id += 1
    
    print("Generating merchant variations...")
    starbucks_variations = [
        ("SQ * STARBUCKS #1234 NEW YORK", "food and dining"),
        ("STARBUCKS COFFEE #5678", "food and dining"),
        ("SQ *SQ *STARBUCKS SAN FRANCISCO", "food and dining"),
    ]
    for raw_name, cat in starbucks_variations:
        transactions.append({
            'transaction_id': f'txn_{txn_id:03d}',
            'date': fake.date_between(start_date='-30d', end_date='today').strftime('%Y-%m-%d'),
            'amount': round(random.uniform(4.50, 8.50), 2) * -1,
            'merchant_raw': raw_name,
            'description': 'Purchase',
            'category_hint': cat
        })
        txn_id += 1
    
    print(f"Generating random transactions...")
    all_keys = list(MERCHANTS.keys())
    
    category_merchants = {}
    for key, info in MERCHANTS.items():
        cat = info['category']
        if cat not in category_merchants:
            category_merchants[cat] = []
        category_merchants[cat].append(key)
    
    for cat, merchant_keys in category_merchants.items():
        existing = len([t for t in transactions if t['category_hint'] == cat])
        needed = max(0, 2 - existing)
        
        for _ in range(needed):
            if len(transactions) >= 50:
                break
            
            key = random.choice(merchant_keys)
            info = MERCHANTS[key]
            
            if info.get('recurring', False):
                continue
            
            template = random.choice(info['templates'])
            store_num = random.randint(1000, 9999)
            city = fake.city().upper()
            
            try:
                merchant_raw = template.format(store_num, city)
            except:
                try:
                    merchant_raw = template.format(store_num)
                except:
                    merchant_raw = template
            
            amount = round(random.uniform(info['amount_range'][0], info['amount_range'][1]), 2)
            
            transactions.append({
                'transaction_id': f'txn_{txn_id:03d}',
                'date': fake.date_between(start_date='-90d', end_date='today').strftime('%Y-%m-%d'),
                'amount': -amount,
                'merchant_raw': merchant_raw,
                'description': random.choice(['Purchase', 'Bill Payment', 'Debit Card']),
                'category_hint': info['category']
            })
            txn_id += 1
    
    while len(transactions) < 50:
        key = random.choice(all_keys)
        info = MERCHANTS[key]
        
        if info.get('recurring', False):
            continue
        
        template = random.choice(info['templates'])
        store_num = random.randint(1000, 9999)
        city = fake.city().upper()
        
        try:
            merchant_raw = template.format(store_num, city)
        except:
            try:
                merchant_raw = template.format(store_num)
            except:
                merchant_raw = template
        
        amount = round(random.uniform(info['amount_range'][0], info['amount_range'][1]), 2)
        
        transactions.append({
            'transaction_id': f'txn_{txn_id:03d}',
            'date': fake.date_between(start_date='-90d', end_date='today').strftime('%Y-%m-%d'),
            'amount': -amount,
            'merchant_raw': merchant_raw,
            'description': random.choice(['Purchase', 'Bill Payment', 'Debit Card']),
            'category_hint': info['category']
        })
        txn_id += 1
    
    df = pd.DataFrame(transactions)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    df['transaction_id'] = [f'txn_{i+1:03d}' for i in range(len(df))]
    
    return df

if __name__ == "__main__":
    df = generate_dataset()
    df.to_csv('sample_transactions.csv', index=False)
    
    print(f"\n{'='*60}")
    print(f"DATASET GENERATION COMPLETE")
    print(f"{'='*60}")
    print(f"Total transactions: {len(df)}")
    print(f"Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"\nCategory distribution (ground truth):")
    print(df['category_hint'].value_counts().sort_index())
    print(f"\nSaved to: sample_transactions.csv")