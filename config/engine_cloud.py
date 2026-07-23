# config/engine_cloud.py
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

def get_cloud_connection():
    """Returns a connection to the Azure SQL Cloud Database using Entra ID MFA Authentication"""
    server = os.getenv("AZURE_DB_SERVER")
    database = os.getenv("AZURE_DB_NAME")
    username = os.getenv("AZURE_DB_USER") # Make sure this is back to your full email redmount@hungpei.onmicrosoft.com
    
    # We use ActiveDirectoryInteractive so it pops up the browser for your MFA app
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};"
        "Authentication=ActiveDirectoryInteractive;"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
)
    return pyodbc.connect(conn_str)