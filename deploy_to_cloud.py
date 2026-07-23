import os
import requests
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
from config.engine_cloud import get_cloud_connection

# Load secrets and security tokens
load_dotenv()
load_dotenv("tokens.env")

ACCESS_TOKEN = os.getenv("QB_ACCESS_TOKEN")
REALM_ID = os.getenv("QB_REALM_ID")

def create_cloud_tables_if_not_exists():
    """Configures the relational schema in Azure SQL"""
    print("☁️ Connecting to Azure SQL Server...")
    conn = get_cloud_connection()
    cursor = conn.cursor()
    
    print("🛠️ Creating 4-Table Warehouse Layout in the cloud...")
    
    # Drop existing tables safely in sequential foreign-key dependency order
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
    print("✅ Azure SQL Schema Successfully Formatted!")

def fetch_quickbooks_customers():
    """Pulls the 29 live sandbox customers over REST API"""
    print("📥 Extraction pipeline activated: Querying QuickBooks Cloud...")
    url = f"https://sandbox-quickbooks.api.intuit.com/v3/company/{REALM_ID}/query?query=select * from Customer maxresults 100"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Accept": "application/json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"QuickBooks extraction failure: {response.text}")
    return response.json().get("QueryResponse", {}).get("Customer", [])

def migrate_to_azure():
    create_cloud_tables_if_not_exists()
    
    try:
        qb_customers = fetch_quickbooks_customers()
    except Exception as e:
        print(f"❌ Migration Error: {e}")
        print("💡 Quick Check: Run 'python connect.py' to acquire a fresh 60-min OAuth token.")
        return

    conn = get_cloud_connection()
    cursor = conn.cursor()
    
    print(f"🚀 Hydrating Cloud Warehouse with {len(qb_customers)} customers & relational histories...")
    
    services_pool = ["Consulting Service", "Software Development", "Cloud Architecture Audit", "Database Administration", "UI/UX Prototyping"]
    invoice_counter, line_counter, payment_counter = 2001, 6001, 8001
    
    for qb_cust in qb_customers:
        cust_id = qb_cust.get("Id")
        display_name = qb_cust.get("DisplayName")
        company_name = qb_cust.get("CompanyName", display_name)
        balance = float(qb_cust.get("Balance", 0.0))
        active = 1 if qb_cust.get("Active", True) else 0
        
        cursor.execute("""
            INSERT INTO Customers (CustomerID, DisplayName, CompanyName, Balance, Active)
            VALUES (?, ?, ?, ?, ?);
        """, (cust_id, display_name, company_name, balance, active))
        
        num_invoices = random.randint(1, 3)
        for _ in range(num_invoices):
            inv_id = f"INV_{invoice_counter}"
            doc_num = f"AZ-{invoice_counter}"
            days_ago = random.randint(5, 90)
            txn_date = (datetime.now() - timedelta(days=days_ago)).date()
            
            num_lines = random.randint(1, 2)
            lines_to_insert = []
            invoice_total = 0.0
            
            for _ in range(num_lines):
                line_id = f"LINE_{line_counter}"
                item = random.choice(services_pool)
                qty = random.randint(1, 10)
                rate = random.choice([85.00, 130.00, 165.00, 220.00]) # Slightly different rates to distinguish cloud data
                line_amount = qty * rate
                invoice_total += line_amount
                
                lines_to_insert.append((line_id, inv_id, item, qty, line_amount))
                line_counter += 1
                
            # Insert parent row first
            cursor.execute("""
                INSERT INTO Invoices (InvoiceID, CustomerID, DocNumber, TxnDate, TotalAmount)
                VALUES (?, ?, ?, ?, ?);
            """, (inv_id, cust_id, doc_num, txn_date, invoice_total))
            
            # Insert child records
            for line in lines_to_insert:
                cursor.execute("""
                    INSERT INTO InvoiceLines (LineID, InvoiceID, ItemName, Quantity, Amount)
                    VALUES (?, ?, ?, ?, ?);
                """, line)
                
            if random.choice([True, False]) and balance == 0:
                pay_id = f"PAY_{payment_counter}"
                pay_date = (datetime.combine(txn_date, datetime.min.time()) + timedelta(days=random.randint(1, 5))).date()
                cursor.execute("""
                    INSERT INTO Payments (PaymentID, CustomerID, InvoiceID, PaymentDate, AmountPaid)
                    VALUES (?, ?, ?, ?, ?);
                """, (pay_id, cust_id, inv_id, pay_date, invoice_total))
                payment_counter += 1
                
            invoice_counter += 1

    conn.commit()
    cursor.close()
    conn.close()
    print("🎉 Cloud Database migration complete! The warehouse is fully charged.")

if __name__ == "__main__":
    migrate_to_azure()