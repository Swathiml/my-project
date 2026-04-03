import re
import pandas as pd

def clean_merchant(raw_name):
    if pd.isna(raw_name):
        return ""

    name = raw_name.strip()

    # SMART PREFIX NORMALIZATION 

    replacements = {
        r'^AMAZON\.COM\*': 'AMAZON ',
        r'^PAYPAL \*': 'PAYPAL ',
        r'^(SQ \*)+': '',     # remove multiple SQ * but keep merchant
        r'^TST\*': '',        # remove TST*
    }

    for pattern, repl in replacements.items():
        name = re.sub(pattern, repl, name, flags=re.IGNORECASE)

    #  REMOVE NOISE (NUMBERS, IDS, STATES)

    noise_patterns = [
        r'#\d+',                  # remove #1234 store numbers
        r'\d{5,}',                # remove long transaction numbers
        r'\b(NY|CA|MI|TX|FL)\b',  # remove US state codes
    ]

    for pattern in noise_patterns:
        name = re.sub(pattern, '', name, flags=re.IGNORECASE)

    # CLEAN EXTRA SPACES

    name = re.sub(r'\s+', ' ', name).strip()

    return name


# TEST SCRIPT 

df = pd.read_csv('sample_transactions.csv')
df['merchant_clean'] = df['merchant_raw'].apply(clean_merchant)

print("=== BEFORE vs AFTER ===")
for _, row in df.head(10).iterrows():
    print(f"RAW:   {row['merchant_raw']}")
    print(f"CLEAN: {row['merchant_clean']}")
    print("-" * 50)

df.to_csv('transactions_cleaned.csv', index=False)
print(f"\nSaved to transactions_cleaned.csv")
