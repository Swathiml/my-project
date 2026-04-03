import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random
import os
from datetime import datetime, timedelta


class SyntheticDocumentGenerator:
    def __init__(self, output_dir="synthetic_docs"):
        self.output_dir = output_dir
        self._setup_directories()
        self._load_fonts()
        
    def _setup_directories(self):
        """Create output folders"""
        for doc_type in ['receipts', 'statements', 'invoices']:
            os.makedirs(f"{self.output_dir}/{doc_type}", exist_ok=True)
    
    def _load_fonts(self):
        """Load fonts with fallbacks"""
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "C:/Windows/Fonts/arial.ttf",
        ]
        
        self.font = None
        self.font_bold = None
        self.font_small = None
        
        for path in font_paths:
            if os.path.exists(path):
                try:
                    self.font = ImageFont.truetype(path, 20)
                    self.font_bold = ImageFont.truetype(path, 24)
                    self.font_small = ImageFont.truetype(path, 16)
                    # print(f"Loaded font: {path}")
                    break
                except:
                    continue
        
        if self.font is None:
            print("Using default font")
            self.font = ImageFont.load_default()
            self.font_bold = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
    
    def _add_noise(self, img, intensity=0.02):
        """Add Gaussian noise"""
        arr = np.array(img).astype(np.float32)
        noise = np.random.normal(0, intensity * 255, arr.shape)
        noisy = np.clip(arr + noise, 0, 255).astype(np.uint8)
        return Image.fromarray(noisy)
    
    def _add_blur(self, img, radius=1):
        """Apply Gaussian blur"""
        return img.filter(ImageFilter.GaussianBlur(radius=radius))
    
    def _rotate(self, img, angle):
        """Rotate image"""
        if angle in [90, 180, 270]:
            return img.rotate(angle, expand=True, fillcolor='white')
        return img
    
    def _add_perspective(self, img):
        """Add perspective distortion"""
        w, h = img.size
        margin = random.randint(30, 80)
        dx1 = random.randint(-margin, margin)
        dy1 = random.randint(-margin, margin)
        
        coeffs = [1, 0.05, dx1, 0.05, 1, dy1, 0.0001, 0.0001]
        return img.transform((w, h), Image.Transform.PERSPECTIVE, 
                           coeffs, Image.Resampling.BICUBIC)
    
    def _apply_degradation(self, img, degradation):
        """Apply degradation pipeline"""
        if degradation is None:
            return img
        
        result = img.copy()
        
        if 'blur' in degradation:
            result = self._add_blur(result, degradation['blur'])
        if 'noise' in degradation:
            result = self._add_noise(result, degradation['noise'])
        if 'rotation' in degradation:
            result = self._rotate(result, degradation['rotation'])
        if 'perspective' in degradation and degradation.get('perspective'):
            result = self._add_perspective(result)
        
        return result
    
    def _random_date(self, days_back=30):
        """Generate random recent date"""
        return datetime.now() - timedelta(days=random.randint(1, days_back))
    
    def generate_receipt(self, idx, degradation=None):
        """
        Generate synthetic receipt with fully randomized content
        """
        width, height = 600, 800
        img = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(img)
        
        # RANDOM: Merchant
        merchants = [
            ("MCDONALD'S", "Fast Food"), ("STARBUCKS COFFEE", "Coffee Shop"),
            ("TARGET STORE #{}", "Retail"), ("SHELL OIL #{}", "Gas Station"),
            ("CVS PHARMACY #{}", "Pharmacy"), ("WHOLE FOODS MKT", "Grocery"),
            ("UBER EATS HELP.UBER.COM", "Delivery"), ("WALMART SUPERCENTER", "Retail"),
            ("TRADER JOE'S #{}", "Grocery"), ("COSTCO WHSE #{}", "Wholesale"),
            ("BEST BUY #{}", "Electronics"), ("HOME DEPOT #{}", "Home Improvement")
        ]
        merchant, category = random.choice(merchants)
        if "{}" in merchant:
            merchant = merchant.format(random.randint(1000, 9999))
        
        # RANDOM: Date and time
        date = self._random_date()
        time_hour = random.randint(6, 23)
        time_min = random.randint(0, 59)
        
        # RANDOM: Transaction details
        trans_num = random.randint(100000, 999999)
        store_num = random.randint(1, 999)
        register_num = random.randint(1, 20)
        
        # RANDOM: Items based on merchant type
        items_pool = {
            "Fast Food": [
                ("Big Mac Meal", 8.99, False), ("Quarter Pounder", 6.49, False),
                ("10pc Nuggets", 5.99, False), ("Large Fries", 3.49, False),
                ("Coke Large", 2.29, False), ("Happy Meal", 4.99, False),
            ],
            "Coffee Shop": [
                ("Caramel Latte", 4.50, False), ("Grande Americano", 3.25, False),
                ("Venti Mocha", 5.25, False), ("Croissant", 3.75, False),
                ("Breakfast Sandwich", 5.95, False), ("Cake Pop", 2.95, False),
            ],
            "Retail": [
                ("Paper Towels 6pk", 12.49, False), ("Laundry Detergent", 15.99, False),
                ("Toothpaste 3pk", 8.99, False), ("Shampoo", 6.49, False),
                ("Trash Bags", 9.99, False), ("Hand Soap", 4.29, False),
            ],
            "Gas Station": [
                ("Regular Unleaded", 3.89, True), ("Plus Gasoline", 4.19, True),
                ("Premium Fuel", 4.49, True), ("Car Wash", 10.00, False),
                ("Snickers Bar", 2.29, False), ("Red Bull", 3.99, False),
            ],
            "Pharmacy": [
                ("Prescription Copay", 22.30, False), ("Vitamins 100ct", 12.99, False),
                ("Allergy Medicine", 15.49, False), ("Band-Aids", 6.29, False),
                ("Hand Sanitizer", 4.99, False), ("Sunscreen", 8.99, False),
            ],
            "Grocery": [
                ("Organic Bananas", 2.99, False), ("Avocados 4pk", 5.99, False),
                ("Almond Milk", 3.49, False), ("Greek Yogurt", 4.99, False),
                ("Chicken Breast", 12.50, False), ("Sourdough Bread", 5.99, False),
            ],
            "Delivery": [
                ("Restaurant Delivery", 28.50, False), ("Delivery Fee", 3.99, False),
                ("Service Fee", 2.85, False), ("Driver Tip", 5.00, False),
                ("Small Order Fee", 2.50, False), ("Tax", 3.12, False),
            ],
            "Wholesale": [
                ("Rotisserie Chicken", 4.99, False), ("Toilet Paper 30pk", 24.99, False),
                ("Kirkland Water 40pk", 4.99, False), ("Ground Beef 5lb", 24.50, False),
                ("Milk Gallon 2pk", 7.99, False), ("Eggs 24ct", 6.99, False),
            ],
            "Electronics": [
                ("USB-C Cable", 15.99, False), ("Screen Protector", 12.99, False),
                ("Phone Case", 24.99, False), ("HDMI Cable 6ft", 19.99, False),
                ("Batteries AA 20pk", 14.99, False), ("Laptop Stand", 34.99, False),
            ],
            "Home Improvement": [
                ("Paint Roller Set", 18.99, False), ("Light Switch 3pk", 8.99, False),
                ("Extension Cord 25ft", 22.99, False), ("LED Bulb 4pk", 12.99, False),
                ("Power Drill", 89.99, False), ("Tape Measure", 9.99, False),
            ],
        }
        
        # Get items for this merchant type, fallback to generic
        available_items = items_pool.get(category, items_pool["Retail"])
        
        # RANDOM: Select 2-5 items
        num_items = random.randint(2, 5)
        selected_items = random.sample(available_items, k=min(num_items, len(available_items)))
        
        # Draw content
        y = 60
        
        # Header
        draw.text((width//2 - 150, y), merchant, font=self.font_bold, fill='black')
        y += 50
        
        # Transaction info
        draw.text((50, y), f"Date: {date.strftime('%m/%d/%Y')}", font=self.font, fill='black')
        y += 35
        draw.text((50, y), f"Time: {time_hour:02d}:{time_min:02d}", font=self.font, fill='black')
        y += 35
        draw.text((50, y), f"Trans #: {trans_num}", font=self.font_small, fill='black')
        y += 25
        draw.text((50, y), f"Store: {store_num}  Reg: {register_num}", font=self.font_small, fill='black')
        y += 50
        
        # Separator
        draw.line((50, y, width-50, y), fill='black', width=2)
        y += 25
        
        # Items
        subtotal = 0
        
        for item, price, is_fuel in selected_items:
            if is_fuel:
                # Fuel: price per gallon, random gallons
                gallons = random.uniform(8.0, 15.0)
                line_total = gallons * price
                draw.text((50, y), f"{item}", font=self.font, fill='black')
                draw.text((300, y), f"{gallons:.3f} gal @ ${price:.2f}", font=self.font_small, fill='black')
            else:
                qty = random.randint(1, 3)
                line_total = qty * price
                draw.text((50, y), f"{qty}x {item}", font=self.font, fill='black')
            
            draw.text((450, y), f"${line_total:.2f}", font=self.font, fill='black')
            subtotal += line_total
            y += 30
        
        y += 20
        draw.line((50, y, width-50, y), fill='black', width=2)
        y += 30
        
        # Totals with random tax rate
        tax_rate = random.choice([0.05, 0.06, 0.07, 0.08, 0.0825, 0.095])
        tax = subtotal * tax_rate
        final_total = subtotal + tax
        
        draw.text((50, y), f"Subtotal:", font=self.font, fill='black')
        draw.text((450, y), f"${subtotal:.2f}", font=self.font, fill='black')
        y += 30
        draw.text((50, y), f"Tax ({tax_rate:.2%}):", font=self.font, fill='black')
        draw.text((450, y), f"${tax:.2f}", font=self.font, fill='black')
        y += 40
        
        draw.text((50, y), f"TOTAL:", font=self.font_bold, fill='black')
        draw.text((450, y), f"${final_total:.2f}", font=self.font_bold, fill='black')
        y += 50
        
        # Random payment method
        payment = random.choice(["DEBIT ****{}", "CREDIT ****{}", "CASH", "MOBILE PAY"])
        if "{}" in payment:
            payment = payment.format(random.randint(1000, 9999))
        
        draw.text((50, y), f"Paid: {payment}", font=self.font, fill='black')
        y += 40
        
        # Footer
        draw.text((width//2 - 80, y), "THANK YOU!", font=self.font_bold, fill='black')
        y += 40
        draw.text((width//2 - 120, y), "Save this receipt for returns", font=self.font_small, fill='black')
        
        # Apply degradation
        img = self._apply_degradation(img, degradation)
        
        path = f"{self.output_dir}/receipts/receipt_{idx:03d}.png"
        img.save(path)
        return path
    
    def generate_statement(self, idx, degradation=None):
        """
        Generate synthetic bank statement with randomized content
        """
        width, height = 800, 1000
        img = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(img)
        
        # RANDOM: Bank and account details
        banks = [
            "FIRST NATIONAL BANK", "CHASE BANK", "BANK OF AMERICA",
            "WELLS FARGO", "CITIBANK", "US BANK", "PNC BANK", "REGIONS BANK"
        ]
        bank_name = random.choice(banks)
        
        account_holder = random.choice([
            "JOHN DOE", "JANE SMITH", "ROBERT JOHNSON", "MARIA GARCIA",
            "DAVID LEE", "SARAH WILSON", "MICHAEL BROWN", "LINDA DAVIS"
        ])
        
        account_suffix = random.randint(1000, 9999)
        
        # RANDOM: Statement period
        end_date = self._random_date(days_back=60)
        start_date = end_date - timedelta(days=30)
        
        # RANDOM: Starting balance
        start_balance = random.uniform(1000.00, 15000.00)
        
        # Generate randomized transactions
        transaction_types = [
            # (description, amount_range, is_credit)
            ("PAYROLL DEPOSIT", (2000.00, 5000.00), True),
            ("DIRECT DEPOSIT", (500.00, 3000.00), True),
            ("REFUND {}", (10.00, 200.00), True),
            ("AMAZON.COM*{}", (15.00, 300.00), False),
            ("SHELL OIL {}", (30.00, 80.00), False),
            ("TRADER JOES #{}", (40.00, 200.00), False),
            ("NETFLIX.COM {}", (15.49, 19.99), False),
            ("SPOTIFY USA", (10.99, 12.99), False),
            ("CITY GYM {}", (40.00, 100.00), False),
            ("ONLINE TRANSFER", (100.00, 1000.00), False),
            ("WHOLE FOODS MKT {}", (50.00, 350.00), False),
            ("UBER TRIP HELP.UBER.COM", (12.00, 45.00), False),
            ("LYFT RIDE {}", (8.00, 35.00), False),
            ("STARBUCKS STORE {}", (4.50, 12.00), False),
            ("MCDONALD'S {}", (6.00, 25.00), False),
            ("TARGET STORE {}", (25.00, 400.00), False),
            ("WALMART STORE {}", (15.00, 250.00), False),
            ("COSTCO WHSE {}", (75.00, 500.00), False),
            ("PHONE BILL AUTO PAY", (45.00, 95.00), False),
            ("INTERNET SERVICE", (50.00, 120.00), False),
            ("ELECTRIC BILL", (60.00, 200.00), False),
            ("RENT PAYMENT", (800.00, 2500.00), False),
            ("MORTGAGE PAYMENT", (1200.00, 3500.00), False),
            ("CAR INSURANCE", (80.00, 250.00), False),
            ("GROCERY DELIVERY", (40.00, 180.00), False),
        ]
        
        # Generate 8-15 random transactions
        num_transactions = random.randint(8, 15)
        transactions = []
        current_balance = start_balance
        current_date = start_date
        
        for _ in range(num_transactions):
            # Random date progression
            current_date += timedelta(days=random.randint(1, 5))
            if current_date > end_date:
                break
            
            tx_type = random.choice(transaction_types)
            desc_template, amount_range, is_credit = tx_type
            
            # Format description with random numbers
            if "{}" in desc_template:
                desc = desc_template.format(random.randint(100, 9999))
            else:
                desc = desc_template
            
            # Random amount
            amount = random.uniform(*amount_range)
            
            if is_credit:
                current_balance += amount
                amount_str = f"+{amount:.2f}"
            else:
                current_balance -= amount
                amount_str = f"-{amount:.2f}"
            
            balance_str = f"{current_balance:.2f}"
            date_str = current_date.strftime("%m/%d")
            
            transactions.append((date_str, desc[:25], amount_str, balance_str))
        
        # Calculate summary
        total_deposits = sum(float(tx[2]) for tx in transactions if tx[2].startswith('+'))
        total_withdrawals = sum(abs(float(tx[2])) for tx in transactions if tx[2].startswith('-'))
        end_balance = current_balance
        
        # Draw content
        y = 50
        
        # Bank header
        draw.text((50, y), bank_name, font=self.font_bold, fill='black')
        y += 40
        draw.text((50, y), "Account Statement", font=self.font, fill='black')
        y += 60
        
        # Account info box
        draw.rectangle([50, y, width-50, y+120], outline='black', width=2)
        draw.text((60, y+10), f"Account Holder: {account_holder}", font=self.font, fill='black')
        y += 45
        draw.text((60, y), f"Account Number: ****{account_suffix}", font=self.font, fill='black')
        y += 45
        draw.text((60, y), f"Statement Period: {start_date.strftime('%m/%d/%Y')} - {end_date.strftime('%m/%d/%Y')}", 
                 font=self.font, fill='black')
        y += 150
        
        # Summary
        draw.text((50, y), "Account Summary", font=self.font_bold, fill='black')
        y += 40
        draw.text((50, y), f"Beginning Balance: ${start_balance:,.2f}", font=self.font, fill='black')
        y += 30
        draw.text((50, y), f"Total Deposits: ${total_deposits:,.2f}", font=self.font, fill='black')
        y += 30
        draw.text((50, y), f"Total Withdrawals: ${total_withdrawals:,.2f}", font=self.font, fill='black')
        y += 30
        draw.text((50, y), f"Ending Balance: ${end_balance:,.2f}", font=self.font_bold, fill='black')
        y += 60
        
        # Transactions header
        draw.text((50, y), "Transaction Details", font=self.font_bold, fill='black')
        y += 40
        
        # Table header
        headers = ["Date", "Description", "Amount", "Balance"]
        x_positions = [50, 150, 500, 650]
        for x, h in zip(x_positions, headers):
            draw.text((x, y), h, font=self.font_bold, fill='black')
        y += 30
        draw.line((50, y, width-50, y), fill='black', width=2)
        y += 20
        
        # Transaction rows
        for date_str, desc, amount_str, balance_str in transactions:
            draw.text((50, y), date_str, font=self.font, fill='black')
            draw.text((150, y), desc, font=self.font, fill='black')
            draw.text((500, y), amount_str, font=self.font, fill='black')
            draw.text((650, y), balance_str, font=self.font, fill='black')
            y += 28
        
        # Footer
        y += 40
        draw.line((50, y, width-50, y), fill='black', width=1)
        y += 20
        phone = random.choice(["1-800-BANK-HELP", "1-888-555-0100", "1-877-CUST-SVC"])
        draw.text((50, y), f"Questions? Call {phone}", font=self.font_small, fill='black')
        
        # Apply degradation
        img = self._apply_degradation(img, degradation)
        
        path = f"{self.output_dir}/statements/statement_{idx:03d}.png"
        img.save(path)
        return path
    
    def generate_invoice(self, idx, degradation=None):
        """
        Generate synthetic invoice with fully randomized content
        """
        width, height = 800, 900
        img = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(img)
        
        # RANDOM: Invoice number
        inv_prefix = random.choice(["INV", "IN", "FTR", "BILL", "DOC"])
        inv_num = f"{inv_prefix}-{random.randint(10000, 99999)}"
        
        # RANDOM: Dates
        inv_date = self._random_date(days_back=45)
        due_days = random.choice([15, 30, 45, 60])
        due_date = inv_date + timedelta(days=due_days)
        
        # RANDOM: Vendor info
        vendors = [
            ("Tech Solutions LLC", "123 Business Ave", "San Francisco, CA 94102"),
            ("Creative Design Studio", "456 Innovation Dr", "Austin, TX 78701"),
            ("Consulting Partners Inc", "789 Corporate Pkwy", "New York, NY 10001"),
            ("Cloud Services Pro", "321 Data Center Ln", "Seattle, WA 98101"),
            ("Marketing Experts LLC", "555 Brand Blvd", "Chicago, IL 60601"),
            ("DevTeam Solutions", "888 Code Street", "Denver, CO 80202"),
        ]
        vendor_name, vendor_street, vendor_city = random.choice(vendors)
        
        # RANDOM: Client info
        clients = [
            "Client Corporation Inc.",
            "Enterprise Solutions Ltd.",
            "Global Industries LLC",
            "Innovation Partners Co.",
            "Strategic Ventures Group",
            "Premier Services Corp.",
            "Advanced Systems Inc.",
            "Business Growth LLC",
        ]
        client_name = random.choice(clients)
        
        # RANDOM: Line items based on vendor type
        service_catalogs = {
            "Tech": [
                ("Software Development", (100, 200), "hrs"),
                ("System Architecture", (150, 250), "hrs"),
                ("Code Review", (75, 125), "hrs"),
                ("DevOps Setup", (120, 180), "hrs"),
                ("API Integration", (800, 1500), "project"),
                ("Database Design", (600, 1200), "project"),
            ],
            "Creative": [
                ("Logo Design", (500, 1500), "project"),
                ("Brand Guidelines", (1200, 2500), "project"),
                ("Website Design", (2000, 5000), "project"),
                ("Social Media Kit", (300, 800), "project"),
                ("Print Materials", (150, 400), "hrs"),
                ("Photo Editing", (75, 150), "hrs"),
            ],
            "Consulting": [
                ("Strategy Session", (200, 400), "hrs"),
                ("Market Analysis", (150, 300), "hrs"),
                ("Process Audit", (5000, 12000), "project"),
                ("Training Workshop", (1000, 3000), "session"),
                ("Executive Coaching", (300, 600), "hrs"),
                ("Feasibility Study", (3000, 8000), "project"),
            ],
            "Cloud": [
                ("Cloud Migration", (5000, 15000), "project"),
                ("AWS Setup", (2000, 5000), "project"),
                ("Security Audit", (3000, 8000), "project"),
                ("Server Monitoring", (500, 1200), "mo"),
                ("Backup Solutions", (200, 500), "mo"),
                ("Disaster Recovery", (4000, 10000), "project"),
            ],
            "Marketing": [
                ("SEO Campaign", (1500, 4000), "mo"),
                ("Content Strategy", (1000, 2500), "mo"),
                ("PPC Management", (800, 2000), "mo"),
                ("Email Marketing", (500, 1500), "campaign"),
                ("Video Production", (2000, 8000), "project"),
                ("Influencer Outreach", (1000, 3000), "campaign"),
            ],
            "Dev": [
                ("Mobile App Dev", (15000, 50000), "project"),
                ("Web Application", (8000, 25000), "project"),
                ("E-commerce Setup", (5000, 15000), "project"),
                ("QA Testing", (50, 100), "hrs"),
                ("Bug Fixes", (75, 150), "hrs"),
                ("Feature Add-on", (100, 200), "hrs"),
            ],
        }
        
        # Pick catalog based on vendor name keywords
        if "Tech" in vendor_name or "Cloud" in vendor_name:
            catalog = service_catalogs["Tech"] + service_catalogs["Cloud"]
        elif "Creative" in vendor_name or "Design" in vendor_name:
            catalog = service_catalogs["Creative"]
        elif "Consulting" in vendor_name:
            catalog = service_catalogs["Consulting"]
        elif "Marketing" in vendor_name:
            catalog = service_catalogs["Marketing"]
        else:
            catalog = service_catalogs["Dev"]
        
        # RANDOM: Select 3-6 line items
        num_items = random.randint(3, 6)
        selected_services = random.sample(catalog, k=min(num_items, len(catalog)))
        
        # Draw content
        y = 50
        
        # Invoice header (right side)
        draw.text((550, y), "INVOICE", font=self.font_bold, fill='black')
        y += 35
        draw.text((550, y), f"#{inv_num}", font=self.font, fill='black')
        y += 60
        
        # From (left side)
        draw.text((50, y), "From:", font=self.font_bold, fill='black')
        y += 30
        draw.text((50, y), vendor_name, font=self.font, fill='black')
        y += 25
        draw.text((50, y), vendor_street, font=self.font, fill='black')
        y += 25
        draw.text((50, y), vendor_city, font=self.font, fill='black')
        y += 60
        
        # Bill To
        draw.text((50, y), "Bill To:", font=self.font_bold, fill='black')
        y += 30
        draw.text((50, y), client_name, font=self.font, fill='black')
        y += 25
        draw.text((50, y), "Attn: Accounts Payable", font=self.font_small, fill='black')
        y += 60
        
        # Invoice details
        draw.text((50, y), f"Invoice Date: {inv_date.strftime('%m/%d/%Y')}", font=self.font, fill='black')
        draw.text((450, y), f"Due Date: {due_date.strftime('%m/%d/%Y')}", font=self.font, fill='black')
        y += 50
        
        # Terms
        terms = random.choice(["Net 15", "Net 30", "Net 45", "Due on Receipt", "2/10 Net 30"])
        draw.text((50, y), f"Payment Terms: {terms}", font=self.font, fill='black')
        y += 60
        
        # Line items table
        headers = ["Description", "Qty", "Unit Price", "Amount"]
        x_positions = [50, 400, 500, 650]
        
        draw.line((50, y, width-50, y), fill='black', width=2)
        y += 10
        for x, h in zip(x_positions, headers):
            draw.text((x, y), h, font=self.font_bold, fill='black')
        y += 30
        draw.line((50, y, width-50, y), fill='black', width=1)
        y += 20
        
        # Items with random quantities
        subtotal = 0
        for service, price_range, unit in selected_services:
            unit_price = random.uniform(*price_range)
            
            if unit in ["hrs", "mo"]:
                qty = random.randint(1, 40) if unit == "hrs" else random.randint(1, 12)
            elif unit == "project":
                qty = 1
            else:
                qty = random.randint(1, 3)
            
            amount = qty * unit_price
            subtotal += amount
            
            draw.text((50, y), service[:35], font=self.font, fill='black')
            draw.text((400, y), f"{qty} {unit}", font=self.font, fill='black')
            draw.text((500, y), f"${unit_price:.2f}", font=self.font, fill='black')
            draw.text((650, y), f"${amount:.2f}", font=self.font, fill='black')
            y += 30
        
        y += 20
        draw.line((50, y, width-50, y), fill='black', width=1)
        y += 30
        
        # Totals with random tax
        tax_rate = random.choice([0.0, 0.06, 0.07, 0.08, 0.095])
        tax = subtotal * tax_rate
        total = subtotal + tax
        
        draw.text((450, y), "Subtotal:", font=self.font, fill='black')
        draw.text((650, y), f"${subtotal:.2f}", font=self.font, fill='black')
        y += 30
        
        if tax_rate > 0:
            draw.text((450, y), f"Tax ({tax_rate:.1%}):", font=self.font, fill='black')
            draw.text((650, y), f"${tax:.2f}", font=self.font, fill='black')
            y += 30
        
        draw.text((450, y), "TOTAL DUE:", font=self.font_bold, fill='black')
        draw.text((650, y), f"${total:.2f}", font=self.font_bold, fill='black')
        y += 60
        
        # Payment instructions (randomized)
        payment_methods = [
            "Bank: Chase | Routing: 021000021 | Account: ****{}",
            "Bank: BofA | Routing: 121000358 | Account: ****{}",
            "Payable to: {} | Wire transfer accepted",
            "ACH Routing: 021000021 | Account: ****{}",
            "Check payable to: {}",  # ← FIXED: just a string
        ]
        
        payment = random.choice(payment_methods)
        if "{}" in payment:
            payment = payment.format(random.randint(1000, 9999))
        
        draw.text((50, y), "Payment Instructions:", font=self.font_small, fill='black')
        y += 25
        draw.text((50, y), payment, font=self.font_small, fill='black')
        
        # Apply degradation
        img = self._apply_degradation(img, degradation)
        
        path = f"{self.output_dir}/invoices/invoice_{idx:03d}.png"
        img.save(path)
        return path
    
    def generate_dataset(self, n_per_type=10):
        """Generate complete dataset with variety"""
        paths = []
        
        for i in range(n_per_type):
            # Clean versions
            paths.append(self.generate_receipt(i*3, degradation=None))
            paths.append(self.generate_statement(i*3, degradation=None))
            paths.append(self.generate_invoice(i*3, degradation=None))
            
            # Blurred versions
            paths.append(self.generate_receipt(i*3 + 1, degradation={'blur': random.uniform(1, 3)}))
            paths.append(self.generate_statement(i*3 + 1, degradation={'blur': random.uniform(0.5, 2)}))
            paths.append(self.generate_invoice(i*3 + 1, degradation={'blur': random.uniform(1, 2.5)}))
            
            # Rotated versions
            paths.append(self.generate_receipt(i*3 + 2, degradation={'rotation': random.choice([90, 180, 270])}))
            paths.append(self.generate_statement(i*3 + 2, degradation={'rotation': random.choice([90, 180])}))
            paths.append(self.generate_invoice(i*3 + 2, degradation={'rotation': random.choice([90, 270])}))
        
        print(f"\nGenerated {len(paths)} synthetic documents:")
        print(f"  - {n_per_type*3} receipts")
        print(f"  - {n_per_type*3} statements")
        print(f"  - {n_per_type*3} invoices")
        print(f"\nLocation: {os.path.abspath(self.output_dir)}")
        return paths


if __name__ == "__main__":
    # Test generation
    gen = SyntheticDocumentGenerator("test_docs")
    
    # Generate one of each with different degradations
    print("Testing receipt...")
    r1 = gen.generate_receipt(1, degradation=None)
    r2 = gen.generate_receipt(2, degradation={'blur': 2, 'rotation': 90})
    print(f"  Clean: {r1}")
    print(f"  Blur+Rot: {r2}")
    
    print("\nTesting statement...")
    s1 = gen.generate_statement(1, degradation=None)
    s2 = gen.generate_statement(2, degradation={'noise': 0.03})
    print(f"  Clean: {s1}")
    print(f"  Noisy: {s2}")
    
    print("\nTesting invoice...")
    i1 = gen.generate_invoice(1, degradation=None)
    i2 = gen.generate_invoice(2, degradation={'perspective': True})
    print(f"  Clean: {i1}")
    print(f"  Perspective: {i2}")
    
    print("\n" + "="*50)
    print("Now generate full dataset? (y/n)")
    if input().lower() == 'y':
        gen.generate_dataset(n_per_type=5)