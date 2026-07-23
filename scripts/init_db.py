import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

def initialize_warehouse():
    server = os.getenv("DB_SERVER")
    database = os.getenv("DB_NAME")
    
    print(f"🔌 Connecting to Microsoft SQL Server: {server}...")
    
    # Connect directly to master database to check/create target database
    conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE=master;Trusted_Connection=yes;"
    conn = pyodbc.connect(conn_str, autocommit=True)
    cursor = conn.cursor()
    
    # Create database if it does not exist
    cursor.execute(f"IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = '{database}') CREATE DATABASE {database};")
    cursor.close()
    conn.close()
    
    # Reconnect to our newly verified warehouse database
    conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;"
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    print(f"🛠️ Initializing target layout inside database: {database}...")
    cursor.execute("""
        IF OBJECT_ID('Customers', 'U') IS NOT NULL DROP TABLE Customers;
        
        CREATE TABLE Customers (
            CustomerID VARCHAR(50) PRIMARY KEY,
            DisplayName NVARCHAR(255),
            CompanyName NVARCHAR(255),
            Balance DECIMAL(18, 2),
            Active BIT
        );
    """)
    conn.commit()
    cursor.close()
    conn.close()
    print("🎉 Database warehouse tables successfully initialized!")

if __name__ == "__main__":
    initialize_warehouse()