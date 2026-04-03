import pandas as pd
import re
import spacy
from transformers import pipeline
from rapidfuzz import fuzz, process

class TransactionPipeline:

    def __init__(self):
        print("Loading models...")
        self.nlp = spacy.load("en_core_web_sm")
        self.classifier = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli"
        )

        # Better category labels (descriptions implicit in names)
        self.categories = [
            "food and dining",
            "groceries", 
            "shopping",
            "entertainment",
            "transportation", 
            "healthcare",
            "utilities",
            "income",
            "transfer"
        ]

    def clean(self, raw):
        if pd.isna(raw):
            return ""

        name = str(raw).strip().upper()

        replacements = [
            (r'^SQ \*\s*', ''),
            (r'^TST\*\s*', ''),
            (r'^AMAZON\.COM\*', 'AMAZON '),
            (r'^PAYPAL \*', ''),
        ]

        for pattern, repl in replacements:
            name = re.sub(pattern, repl, name, flags=re.IGNORECASE)

        noise_patterns = [r'#\d+', r'\d{8,}', r'\b(NY|CA|TX|FL|MI)\b']

        for pattern in noise_patterns:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)

        name = re.sub(r'\s+', ' ', name).strip()

        return name.title()

    def extract(self, text):
        if not text or pd.isna(text):
            return text

        doc = self.nlp(text)

        for ent in doc.ents:
            if ent.label_ == "ORG":
                start = max(0, ent.start - 1)
                end = min(len(doc), ent.end + 1)
                expanded = doc[start:end].text
                expanded = re.sub(r'[^a-zA-Z0-9\s]', ' ', expanded)
                expanded = re.sub(r'\s+', ' ', expanded).strip()
                if len(expanded) > 2:
                    return expanded

        chunks = [c.text for c in doc.noun_chunks if len(c.text) > 2]
        if chunks:
            cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', chunks[0])
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            return cleaned

        proper = [t.text for t in doc if t.pos_ == "PROPN" and len(t.text) > 2]
        if proper:
            return " ".join(proper[:2])

        return text

    def cluster(self, names, threshold=80):
        unique = list(set(names))
        assigned = set()
        clusters = []

        for name in unique:
            if name in assigned:
                continue

            matches = process.extract(name, unique, scorer=fuzz.WRatio, limit=None)

            group = [m for m, score, _ in matches 
                    if score >= threshold and m not in assigned]

            for g in group:
                assigned.add(g)

            if group:
                canonical = min(group, key=len)
                clusters.append({'canonical': canonical, 'members': group})

        mapping = {}
        for c in clusters:
            cid = re.sub(r'[^a-z0-9]', '', c['canonical'].lower())
            for member in c['members']:
                mapping[member] = {'name': c['canonical'], 'id': cid}

        return mapping

    def categorize(self, merchant, desc, amount):
        """Categorize with better labels and context"""
        amount_type = "income" if amount > 0 else "expense"
        text = f"{merchant}. {desc}. This is an {amount_type}."
        
        result = self.classifier(
            text, 
            self.categories,
            hypothesis_template="This is a {} transaction."
        )
        
        cat = result['labels'][0]
        score = result['scores'][0]
        
        if score >= 0.75:
            level = "high"
        elif score >= 0.5:
            level = "medium"
        else:
            level = "low"
        
        return cat, round(score, 3), level

    def fingerprint(self, amount, date, merchant_id):
        amt = f"{abs(float(amount)):.2f}"
        dt = pd.to_datetime(date).strftime('%Y%m%d')
        mid = re.sub(r'[^a-z0-9]', '', str(merchant_id).lower())
        return f"{amt}_{dt}_{mid}"

    def detect_recurring(self, df):
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'])

        results = []

        for merchant_id, group in df.groupby('canonical_id'):
            if len(group) < 2:
                results.extend(['one-time'] * len(group))
                continue

            dates = sorted(group['date'].tolist())
            intervals = [(dates[i+1] - dates[i]).days 
                        for i in range(len(dates)-1)]

            is_monthly = all(25 <= i <= 35 for i in intervals)

            if is_monthly and len(group) >= 3:
                t = 'recurring'
            elif len(group) > 1:
                t = 'repeat'
            else:
                t = 'one-time'

            results.extend([t] * len(group))

        return results

    def process(self, input_file='sample_transactions.csv', 
                output_file='week2_deliverable.csv'):
        
        print(f"\nProcessing {input_file}...")
        df = pd.read_csv(input_file)

        print("1. Cleaning...")
        df['merchant_clean'] = df['merchant_raw'].apply(self.clean)

        print("2. Extracting...")
        df['merchant_extracted'] = df['merchant_clean'].apply(self.extract)

        print("3. Normalizing...")
        def normalize_row(row):
            extracted = row['merchant_extracted']
            clean = row['merchant_clean']
            
            if extracted and len(str(extracted)) > 3:
                norm = re.sub(r'[^a-zA-Z0-9\s]', ' ', str(extracted))
                norm = re.sub(r'\s+', ' ', norm).strip().title()
                return norm if len(norm) > 2 else clean
            return clean
        
        df['merchant_normalized'] = df.apply(normalize_row, axis=1)
        df['normalized_id'] = df['merchant_normalized'].str.lower().str.replace(
            r'[^a-z0-9]', '', regex=True
        )

        print("4. Clustering...")
        cluster_map = self.cluster(df['merchant_normalized'].tolist())
        
        df['merchant_canonical'] = df['merchant_normalized'].map(
            lambda x: cluster_map.get(x, {}).get('name', x)
        )
        df['canonical_id'] = df['merchant_normalized'].map(
            lambda x: cluster_map.get(x, {}).get('id', 
                re.sub(r'[^a-z0-9]', '', x.lower()))
        )

        print("5. Categorizing...")
        cats = df.apply(
            lambda x: self.categorize(
                x['merchant_canonical'],
                x['description'],
                x['amount']
            ),
            axis=1
        )
        df['category'] = [c[0] for c in cats]
        df['category_confidence'] = [c[1] for c in cats]
        df['confidence_level'] = [c[2] for c in cats]

        print("6. Fingerprinting...")
        df['fingerprint'] = df.apply(
            lambda x: self.fingerprint(
                x['amount'],
                x['date'],
                x['canonical_id']
            ),
            axis=1
        )

        print("7. Detecting recurring...")
        df['transaction_type'] = self.detect_recurring(df)

        df.to_csv(output_file, index=False)

        print(f"\n{'='*50}")
        print("WEEK 2 COMPLETE")
        print(f"{'='*50}")
        print(f"Total: {len(df)} transactions")
        print(f"\nCategories:\n{df['category'].value_counts()}")
        print(f"\nTypes:\n{df['transaction_type'].value_counts()}")
        print(f"\nConfidence:\n{df['confidence_level'].value_counts()}")
        
        return df


if __name__ == "__main__":
    pipeline = TransactionPipeline()
    result = pipeline.process()