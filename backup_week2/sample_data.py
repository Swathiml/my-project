from faker import Faker
import pandas as pd
import random

fake = Faker()

merchants = [
    ("SQ * STARBUCKS #{} {}", "food"),
    ("TST* WHOLE FOODS MKT #{}", "groceries"),
    ("AMAZON.COM*{} SEATTLE", "shopping"),
    ("UBER EATS HELP.UBER.COM", "food"),
    ("NETFLIX.COM {} CA", "entertainment"),
    ("SHELL OIL {}57420389", "transportation"),
    ("CVS/PHARMACY #{} MIAMI", "healthcare"),
    ("SPOTIFY USA", "entertainment"),
    ("MTA*NYCT PAYGO NEW YORK NY", "transportation"),
    ("TARGET {} MINNEAPOLIS", "shopping"),
    ("WAL-MART #{} SUPER CENTER", "shopping"),
    ("MCDONALD'S #{} CHICAGO", "food"),
    ("PAYPAL *NETFLIX NETFLIX.COM", "entertainment"),
    ("SQ *SQ *COFFEE SHOP SAN FRANCISCO", "food"),
    ("ONLINE PAYMENT - THANK YOU", "transfer"),
    ("ATT MOBILE PAYMENT {}", "utilities"),
]

def generate_transaction(transaction_id):
    merchant_template, category = random.choice(merchants)
    
    store_number = random.randint(1000, 9999)
    city = fake.city().upper()
    
    try:
        merchant_raw = merchant_template.format(store_number, city)
    except:
        try:
            merchant_raw = merchant_template.format(store_number)
        except:
            merchant_raw = merchant_template
    
    date = fake.date_between(start_date='-90d', end_date='today')
    amount = round(random.uniform(-200, -5), 2)
    
    if random.random() < 0.1:
        amount = round(random.uniform(1000, 5000), 2)
        merchant_raw = "DIRECT DEPOSIT PAYROLL"
        category = "income"
    
    # Varied descriptions for expenses
    expense_descriptions = ['Purchase', 'Subscription', 'Bill Payment', 'Debit Card', 'Recurring Payment']
    
    return {
        'transaction_id': f'txn_{transaction_id:03d}',
        'date': date.strftime('%Y-%m-%d'),
        'amount': amount,
        'merchant_raw': merchant_raw,
        'description': random.choice(expense_descriptions) if amount < 0 else 'Deposit',
        'category_hint': category
    }

transactions = [generate_transaction(i) for i in range(1, 31)]
df = pd.DataFrame(transactions)
df.to_csv('sample_transactions.csv', index=False)

print(f"Created {len(transactions)} sample transactions")
print(df.head(10))