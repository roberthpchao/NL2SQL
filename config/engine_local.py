# config/engine_local.py
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

def get_local_connection():
    """Returns a connection to the local .\SQLEXPRESS instance"""
    server = os.getenv("DB_SERVER")
    database = os.getenv("DB_NAME")
    
    conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;"
    return pyodbc.connect(conn_str)