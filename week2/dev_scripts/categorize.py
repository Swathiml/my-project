import pandas as pd
from transformers import pipeline

classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

categories = [
    "food", "groceries", "shopping", "entertainment",
    "transportation", "healthcare", "utilities", 
    "income", "transfer", "uncategorized"
]

def categorize(merchant, description, amount):
    # Rich context: merchant + description + amount type + amount
    amount_abs = abs(amount)
    amount_type = "income" if amount > 0 else "expense"
    text = f"{merchant} {description} {amount_type} ${amount_abs}"
    
    result = classifier(text, categories)
    cat = result['labels'][0]
    score = result['scores'][0]
    
    # Confidence levels
    if score < 0.5:
        level = "low"
    elif score < 0.7:
        level = "medium"
    else:
        level = "high"
    
    return cat, round(score, 3), level

# Load data
df = pd.read_csv('transactions_normalized.csv')

print(f"Categorizing {len(df)} transactions...")

# Pass amount to categorize function
results = []
for _, row in df.iterrows():
    cat, score, level = categorize(
        row['merchant_normalized'], 
        row['description'],
        row['amount']  # Added this
    )
    results.append({
        'category': cat,
        'category_confidence': score,
        'confidence_level': level
    })

# Save results
results_df = pd.DataFrame(results)
df = pd.concat([df, results_df], axis=1)

print("\n=== SAMPLE ===")
print(df[['merchant_normalized', 'amount', 'category', 'category_confidence']].head(10))

df.to_csv('transactions_categorized.csv', index=False)
print(f"\nSaved to transactions_categorized.csv")