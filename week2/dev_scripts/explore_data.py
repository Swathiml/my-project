import pandas as pd

df = pd.read_csv('sample_transactions.csv')

print("=== DATA OVERVIEW ===")
print(f"Total rows: {len(df)}")
print(f"\nColumns: {list(df.columns)}")
print(f"\nFirst 5 rows:")
print(df.head())

print("\n=== SAMPLE MERCHANT NAMES ===")
for i, row in df.head(10).iterrows():
    print(f"{row['transaction_id']}: {row['merchant_raw']}")

print("\n=== COMMON PATTERNS ===")
patterns = ['SQ *', 'TST*', 'AMAZON', 'UBER', 'PAYPAL', 'ONLINE PAYMENT']
for p in patterns:
    count = df['merchant_raw'].str.contains(p, case=False, na=False).sum()
    print(f"{p}: {count} transactions")