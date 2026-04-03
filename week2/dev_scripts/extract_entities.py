import spacy
import pandas as pd
import re

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

def extract_merchant_spacy(text):
    """
    Use spaCy to extract organization names from text
    """
    if pd.isna(text) or text == "":
        return None
    
    doc = nlp(text)
    
    # Look for ORG (organization) entities
    orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
    
    if orgs:
        # Return longest match (most specific)
        return max(orgs, key=len)
    
    # Fallback: look for proper nouns
    proper_nouns = [token.text for token in doc if token.pos_ == "PROPN" and len(token.text) > 2]
    if proper_nouns:
        return " ".join(proper_nouns[:2])  # First 2 proper nouns
    
    # Final fallback: return first 2 words
    words = text.split()
    return " ".join(words[:2]) if len(words) > 1 else text

# Load cleaned data
df = pd.read_csv('transactions_cleaned.csv')

print("Extracting merchant names with spaCy...")
df['merchant_extracted'] = df['merchant_clean'].apply(extract_merchant_spacy)

# Create final normalized name
def normalize_final(row):
    clean = row['merchant_clean']
    extracted = row['merchant_extracted']
    
    # If extracted is meaningful and different, use it
    if extracted and len(extracted.split()) >= 2 and extracted.lower() != clean.lower():
        normalized = extracted.title()
    else:
        normalized = clean
    
    # Clean up special characters
    normalized = re.sub(r'[^a-zA-Z0-9\s]', '', normalized)
    
    return normalized

df['merchant_normalized'] = df.apply(normalize_final, axis=1)

# Create normalized_id (lowercase, no spaces)
df['normalized_id'] = df['merchant_normalized'].str.lower().str.replace(r'[^a-z0-9]', '', regex=True)

print("\n=== EXTRACTION RESULTS ===")
comparison = df[['merchant_raw', 'merchant_clean', 'merchant_extracted', 'merchant_normalized', 'normalized_id']].head(10)
for _, row in comparison.iterrows():
    print(f"Raw:       {row['merchant_raw']}")
    print(f"Clean:     {row['merchant_clean']}")
    print(f"Extracted: {row['merchant_extracted']}")
    print(f"Final:     {row['merchant_normalized']}")
    print(f"ID:        {row['normalized_id']}")
    print("-" * 60)

# Save
df.to_csv('transactions_normalized.csv', index=False)
print(f"\nSaved to transactions_normalized.csv")