import pandas as pd

def inspect_errors():
    df = pd.read_csv('week2/week2_deliverable.csv')
    
    print("=" * 60)
    print("DETAILED ERROR INSPECTION")
    print("=" * 60)
    
    # High confidence transactions
    high_conf = df[df['confidence_level'] == 'high']
    print(f"\n1. HIGH CONFIDENCE ({len(high_conf)})")
    print(high_conf[['merchant_raw', 'category', 'category_confidence']].head())
    
    # Low confidence - these need fixing
    low_conf = df[df['confidence_level'] == 'low']
    print(f"\n2. LOW CONFIDENCE ({len(low_conf)}) - NEED FALLBACK RULES")
    print(low_conf[['merchant_raw', 'category', 'category_confidence']].head(10))
    
    # Check transfer category
    transfer_only = df[df['category'] == 'transfer']
    print(f"\n3. TRANSFER CATEGORY ({len(transfer_only)}) - CHECK IF CORRECT")
    print(transfer_only[['merchant_raw', 'description']].head(10))
    
    # Save problematic cases
    problematic = df[df['confidence_level'] == 'low']
    problematic.to_csv('week3/baseline/fix_these.csv', index=False)
    print(f"\nSaved {len(problematic)} cases to fix_these.csv")

if __name__ == "__main__":
    inspect_errors()