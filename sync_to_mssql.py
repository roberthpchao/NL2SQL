import os
import requests
import pyodbc
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load configuration secrets
load_dotenv()
load_dotenv("tokens.env")

SERVER = os.getenv("DB_SERVER")
DATABASE = os.getenv("DB_NAME")
ACCESS_TOKEN = os.getenv("QB_ACCESS_TOKEN")
REALM_ID = os.getenv("QB_REALM_ID")

def get_db_connection():
    conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;"
    return pyodbc.connect(conn_str)

def create_tables_if_not_exists():
    """Builds the 4-table relational warehouse schema"""
    print("🛠️ Verifying database schema layout...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Drop tables in correct order due to Foreign Key constraints
    cursor.execute("IF OBJECT_ID('Payments', 'U') IS NOT NULL DROP TABLE Payments;")
    cursor.execute("IF OBJECT_ID('InvoiceLines', 'U') IS NOT NULL DROP TABLE InvoiceLines;")
    cursor.execute("IF OBJECT_ID('Invoices', 'U') IS NOT NULL DROP TABLE Invoices;")
    cursor.execute("IF OBJECT_ID('Customers', 'U') IS NOT NULL DROP TABLE Customers;")
    
    # 1. Customers Table
    cursor.execute("""
        CREATE TABLE Customers (
            CustomerID VARCHAR(50) PRIMARY KEY,
            DisplayName NVARCHAR(255),
            CompanyName NVARCHAR(255),
            Balance DECIMAL(18,2),
            Active BIT
        );
    """)
    
    # 2. Invoices Table
    cursor.execute("""
        CREATE TABLE Invoices (
            InvoiceID VARCHAR(50) PRIMARY KEY,
            CustomerID VARCHAR(50) FOREIGN KEY REFERENCES Customers(CustomerID),
            DocNumber NVARCHAR(50),
            TxnDate DATE,
            TotalAmount DECIMAL(18,2)
        );
    """)
    
    # 3. InvoiceLines Table
    cursor.execute("""
        CREATE TABLE InvoiceLines (
            LineID VARCHAR(50) PRIMARY KEY,
            InvoiceID VARCHAR(50) FOREIGN KEY REFERENCES Invoices(InvoiceID),
            ItemName NVARCHAR(255),
            Quantity INT,
            Amount DECIMAL(18,2)
        );
    """)
    
    # 4. Payments Table
    cursor.execute("""
        CREATE TABLE Payments (
            PaymentID VARCHAR(50) PRIMARY KEY,
            CustomerID VARCHAR(50) FOREIGN KEY REFERENCES Customers(CustomerID),
            InvoiceID VARCHAR(50) FOREIGN KEY REFERENCES Invoices(InvoiceID),
            PaymentDate DATE,
            AmountPaid DECIMAL(18,2)
        );
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ 4-Table Relational Schema successfully configured!")

def fetch_quickbooks_customers():
    """Extracts live sandbox customer data from QuickBooks API"""
    print("📥 Extracting customer data from QuickBooks Sandbox...")
    url = f"https://sandbox-quickbooks.api.intuit.com/v3/company/{REALM_ID}/query?query=select * from Customer maxresults 100"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Accept": "application/json"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch QB data. Status: {response.status_code}, Msg: {response.text}")
        
    return response.json().get("QueryResponse", {}).get("Customer", [])

def populate_warehouse():
    create_tables_if_not_exists()
    
    try:
        qb_customers = fetch_quickbooks_customers()
    except Exception as e:
        print(f"❌ QuickBooks Sync Error: {e}")
        print("💡 Tip: Try running 'python connect.py' to refresh your tokens.env tokens!")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    
    print(f"💾 Syncing {len(qb_customers)} live customers & building rich transactional dependencies...")
    
    services_pool = ["Consulting Service", "Software Development", "Cloud Architecture Audit", "Database Administration", "UI/UX Prototyping"]
    
    invoice_counter = 1001
    line_counter = 5001
    payment_counter = 9001
    
    for qb_cust in qb_customers:
        cust_id = qb_cust.get("Id")
        display_name = qb_cust.get("DisplayName")
        company_name = qb_cust.get("CompanyName", display_name)
        balance = float(qb_cust.get("Balance", 0.0))
        active = 1 if qb_cust.get("Active", True) else 0
        
        # 1. Insert Customer row first
        cursor.execute("""
            INSERT INTO Customers (CustomerID, DisplayName, CompanyName, Balance, Active)
            VALUES (?, ?, ?, ?, ?);
        """, (cust_id, display_name, company_name, balance, active))
        
        # Generate 1 to 3 mock invoices for each customer
        num_invoices = random.randint(1, 3)
        for _ in range(num_invoices):
            inv_id = f"INV_{invoice_counter}"
            doc_num = f"QB-{invoice_counter}"
            
            # Create a random billing date over the last 90 days
            days_ago = random.randint(5, 90)
            txn_date = (datetime.now() - timedelta(days=days_ago)).date()
            
            # Generate temporary lines list so we can calculate the total first
            num_lines = random.randint(1, 2)
            lines_to_insert = []
            invoice_total = 0.0
            
            for _ in range(num_lines):
                line_id = f"LINE_{line_counter}"
                item = random.choice(services_pool)
                qty = random.randint(1, 10)
                rate = random.choice([75.00, 120.00, 150.00, 200.00])
                line_amount = qty * rate
                invoice_total += line_amount
                
                # Temporarily store line details
                lines_to_insert.append((line_id, inv_id, item, qty, line_amount))
                line_counter += 1
                
            # 2. Insert Parent Invoice Row FIRST (Resolves Foreign Key constraint)
            cursor.execute("""
                INSERT INTO Invoices (InvoiceID, CustomerID, DocNumber, TxnDate, TotalAmount)
                VALUES (?, ?, ?, ?, ?);
            """, (inv_id, cust_id, doc_num, txn_date, invoice_total))
            
            # 3. Insert Child Lines NOW that parent exists safely
            for line in lines_to_insert:
                cursor.execute("""
                    INSERT INTO InvoiceLines (LineID, InvoiceID, ItemName, Quantity, Amount)
                    VALUES (?, ?, ?, ?, ?);
                """, line)
                
            # Randomly decide if they paid this invoice
            is_paid = random.choice([True, False])
            if is_paid and balance == 0:  
                pay_id = f"PAY_{payment_counter}"
                pay_date = (datetime.combine(txn_date, datetime.min.time()) + timedelta(days=random.randint(1, 4))).date()
                
                cursor.execute("""
                    INSERT INTO Payments (PaymentID, CustomerID, InvoiceID, PaymentDate, AmountPaid)
                    VALUES (?, ?, ?, ?, ?);
                """, (pay_id, cust_id, inv_id, pay_date, invoice_total))
                payment_counter += 1
                
            invoice_counter += 1

    conn.commit()
    cursor.close()
    conn.close()
    print("🎉 Warehouse successfully hydrated with live and relational data fields!")

if __name__ == "__main__":
    populate_warehouse()