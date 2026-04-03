import pandas as pd
from rapidfuzz import fuzz

df = pd.read_csv('transactions_categorized.csv')

# Create fingerprint
def create_fingerprint(row):
    amount = abs(row['amount'])
    date = row['date'].replace('-', '')
    merchant = row['normalized_id']
    return f"{amount}_{date}_{merchant}"

df['fingerprint'] = df.apply(create_fingerprint, axis=1)

# Find duplicates
print("=== EXACT DUPLICATES ===")
dups = df[df.duplicated(subset=['fingerprint'], keep=False)]
print(f"Found: {len(dups)}")

# Find similar merchants
print("\n=== RECURRING MERCHANTS ===")
counts = df['normalized_id'].value_counts()
recurring = counts[counts > 1]
print(f"Merchants appearing multiple times: {len(recurring)}")
for merch, count in recurring.head(5).items():
    print(f"  {merch}: {count} times")

# Flag transaction type
def flag_type(merchant_id):
    count = counts.get(merchant_id, 0)
    if count > 3:
        return "recurring"
    elif count > 1:
        return "repeat"
    return "one-time"

df['transaction_type'] = df['normalized_id'].apply(flag_type)

print(f"\n=== TYPES ===")
print(df['transaction_type'].value_counts())

df.to_csv('transactions_final.csv', index=False)
print(f"\nSaved to transactions_final.csv")