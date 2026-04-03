import pandas as pd
import re
import spacy
from transformers import pipeline
from rapidfuzz import fuzz, process

class TransactionPipeline:
    def __init__(self, custom_categories=None):
        print("Loading models...")
        self.nlp = spacy.load("en_core_web_sm")
        self.classifier = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli"
        )
        
        self.category_descriptions = {
            "food and dining": "restaurants, cafes, coffee shops, meals, eating out, fast food",
            "groceries": "supermarkets, food stores, grocery shopping, produce, whole foods",
            "shopping": "retail stores, clothing, electronics, online purchases, amazon, target",
            "entertainment": "movies, streaming services, games, hobbies, netflix, spotify, fun",
            "transportation": "gas stations, fuel, public transit, rideshare, uber, shell, mta",
            "healthcare": "pharmacy, doctor, medical services, prescriptions, cvs, health",
            "utilities": "electricity, water, gas, phone bills, internet, mobile payment, att",
            "income": "salary, deposit, payroll, refunds, money received, direct deposit",
            "transfer": "bank transfers, moving money between accounts, online payment",
            "travel": "hotels, flights, car rental, vacation, tourism, booking, airline",
            "subscriptions": "monthly services, saas, memberships, software, adobe, github",
            "fees": "bank fees, late fees, overdraft, service charges, atm fee, penalties"
        }
        
        self.categories = custom_categories or list(self.category_descriptions.keys())
        self.AUTO_ACCEPT_THRESHOLD = 0.7
        self.SUGGESTED_THRESHOLD = 0.5
        
        print(f"Initialized with {len(self.categories)} categories")
    
    def add_category(self, name, description):
        if name not in self.categories:
            self.categories.append(name)
            self.category_descriptions[name] = description
            print(f"Added category: {name}")
    
    def clean(self, raw):
        if pd.isna(raw):
            return ""
        
        name = str(raw).strip().upper()
        
        replacements = [
            (r'^SQ \*\s*', ''),
            (r'^TST\*\s*', ''),
            (r'^AMAZON\.COM\*', 'AMAZON '),
            (r'^PAYPAL \*', ''),
            (r'^ONLINE PAYMENT\s*[-–]?\s*', ''),
        ]
        
        for pattern, repl in replacements:
            name = re.sub(pattern, repl, name, flags=re.IGNORECASE)
        
        noise_patterns = [r'#\d+', r'\d{8,}', r'\b(NY|CA|TX|FL|MI|WA)\b']
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
            canon_id = re.sub(r'[^a-z0-9]', '', c['canonical'].lower())
            for member in c['members']:
                mapping[member] = {'name': c['canonical'], 'id': canon_id}
        
        return mapping
    
    def fallback_classify(self, merchant_raw, merchant_clean, description=""):
        text = f"{merchant_raw} {merchant_clean} {description}".lower()
        
        rules = {
            'transportation': {
                'keywords': ['uber', 'lyft', 'taxi', 'gas', 'shell', 'bp', 'exxon', 
                           'fuel', 'parking', 'toll', 'mta', 'transit', 'subway'],
                'weight': 1
            },
            'healthcare': {
                'keywords': ['cvs', 'walgreens', 'pharmacy', 'prescription', 'doctor', 
                           'medical', 'health', 'hospital', 'clinic', 'dental'],
                'weight': 1
            },
            'food and dining': {
                'keywords': ['starbucks', 'mcdonalds', 'restaurant', 'cafe', 
                           'pizza', 'burger', 'sushi', 'grubhub', 'doordash', 'eats'],
                'weight': 1
            },
            'entertainment': {
                'keywords': ['netflix', 'spotify', 'hulu', 'disney', 'streaming',
                           'movie', 'game', 'steam', 'xbox', 'playstation', 'concert'],
                'weight': 1
            },
            'utilities': {
                'keywords': ['att', 'verizon', 't-mobile', 'comcast', 'electric',
                           'internet', 'phone bill', 'mobile', 'utility'],
                'weight': 1
            },
            'shopping': {
                'keywords': ['amazon', 'target', 'walmart', 'costco', 'best buy',
                           'shop', 'store', 'retail', 'mall'],
                'weight': 1
            },
            'groceries': {
                'keywords': ['whole foods', 'trader joes', 'kroger', 'safeway',
                           'grocery', 'supermarket', 'produce'],
                'weight': 1
            },
            'income': {
                'keywords': ['payroll', 'salary', 'deposit', 'direct deposit',
                           'paycheck', 'refund', 'reimbursement'],
                'weight': 1
            },
            'travel': {
                'keywords': ['hotel', 'motel', 'airbnb', 'booking', 'expedia',
                           'delta', 'united', 'flight', 'airline', 'vacation'],
                'weight': 1
            },
            'subscriptions': {
                'keywords': ['adobe', 'github', 'slack', 'notion', 'zoom',
                           'subscription', 'membership', 'saas', 'software'],
                'weight': 1
            },
            'fees': {
                'keywords': ['late fee', 'overdraft fee', 'service fee', 'atm fee',
                           'penalty', 'bank fee', 'monthly fee'],
                'weight': 1
            }
        }
        
        scores = {}
        for category, rule in rules.items():
            score = 0
            for keyword in rule['keywords']:
                if keyword in text:
                    score += rule['weight']
            
            if score > 0:
                scores[category] = score
        
        if not scores:
            return None, 0, None
        
        best_cat = max(scores, key=scores.get)
        confidence = min(0.6 + (scores[best_cat] * 0.1), 0.85)
        
        return best_cat, round(confidence, 3), f"keyword_match:{best_cat}"
    
    def categorize(self, merchant, description, amount):
        """
        Categorize with zero-shot + strict fallback trigger
        Fallback only runs when confidence < 0.3 (not < 0.5)
        """
        amount_type = "income" if amount > 0 else "expense"
        text = f"{merchant}. {description}. This is an {amount_type}."
        
        # Zero-shot classification
        result = self.classifier(
            text,
            self.categories,
            hypothesis_template="This bank transaction belongs to the {} spending category."
        )
        
        top_cat = result['labels'][0]
        top_score = result['scores'][0]
        
        # Determine status based on strict thresholds
        if top_score > self.AUTO_ACCEPT_THRESHOLD:  # > 0.7
            status = "auto-accepted"
            level = "high"
            method = "zero-shot"
            
        elif top_score >= self.SUGGESTED_THRESHOLD:  # 0.5 - 0.7
            status = "suggested"
            level = "medium"
            method = "zero-shot"
            
        elif top_score < 0.3:  # STRICT: Only fallback when truly lost
            # Try fallback rules
            fallback_cat, fallback_conf, fallback_rule = self.fallback_classify(
                merchant, merchant, description
            )
            
            if fallback_cat and fallback_cat in self.categories:
                top_cat = fallback_cat
                top_score = fallback_conf
                status = "fallback"
                level = "medium"
                method = "fallback-rules"
            else:
                # No fallback match - stay with zero-shot but mark failed
                status = "uncategorized"
                level = "low"
                method = "zero-shot-failed"
                
        else:  # 0.3 - 0.5: Keep zero-shot, mark as weak suggestion
            status = "suggested"
            level = "low"
            method = "zero-shot-weak"
        
        # Build evidence record
        evidence = {
            'input_text': text,
            'hypothesis_template': "This is a {} transaction.",
            'all_scores': dict(zip(result['labels'], [round(s, 4) for s in result['scores']])),
            'top_3': [
                {'category': result['labels'][i], 'score': round(result['scores'][i], 4)}
                for i in range(min(3, len(result['labels'])))
            ],
            'margin_to_second': round(result['scores'][0] - result['scores'][1], 4) if len(result['scores']) > 1 else 1.0

        }
        
        return {
            'category': top_cat,
            'confidence': round(top_score, 4),
            'confidence_level': level,
            'status': status,
            'method': method,
            'evidence': evidence
        }
    
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
            is_biweekly = all(13 <= i <= 15 for i in intervals)
            
            if (is_monthly or is_biweekly) and len(group) >= 3:
                t_type = 'recurring'
            elif len(group) > 1:
                t_type = 'repeat'
            else:
                t_type = 'one-time'
            
            results.extend([t_type] * len(group))
        
        return results
    
    def process(self, input_file='data/sample_transactions.csv', 
                output_file='week2/week2_deliverable.csv'):
        
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
        cat_results = df.apply(
            lambda x: self.categorize(
                x['merchant_canonical'],
                x['description'],
                x['amount']
            ),
            axis=1
        )
        
        df['category'] = [r['category'] for r in cat_results]
        df['category_confidence'] = [r['confidence'] for r in cat_results]
        df['confidence_level'] = [r['confidence_level'] for r in cat_results]
        df['status'] = [r['status'] for r in cat_results]
        df['method'] = [r['method'] for r in cat_results]
        df['evidence'] = [str(r['evidence']) for r in cat_results]
        
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
        
        print(f"\n{'='*60}")
        print("WEEK 2 PIPELINE COMPLETE")
        print(f"{'='*60}")
        print(f"Total: {len(df)} transactions")
        print(f"\nCategories:")
        print(df['category'].value_counts().sort_index())
        print(f"\nStatus:")
        print(df['status'].value_counts())
        print(f"\nConfidence:")
        print(df['confidence_level'].value_counts())
        print(f"\nTransaction Types:")
        print(df['transaction_type'].value_counts())
        
        if 'category_hint' in df.columns:
            correct = (df['category'] == df['category_hint']).sum()
            print(f"\nAccuracy: {correct}/{len(df)} = {correct/len(df):.1%}")
        
        return df


if __name__ == "__main__":
    pipeline = TransactionPipeline()
    result = pipeline.process()