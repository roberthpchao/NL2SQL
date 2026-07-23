import os
import streamlit as st
import pyodbc
import pandas as pd
import io
from dotenv import load_dotenv
from google import genai

# Load our database environment variables
load_dotenv()

SERVER = os.getenv("DB_SERVER")
DATABASE = os.getenv("DB_NAME")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

# Initialize the Gemini client
client = genai.Client(api_key=GEMINI_KEY)

def run_sql_query(sql_query):
    """Executes the generated SQL query against our local MS SQL Server"""
    conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;"
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        cursor.execute(sql_query)
        
        # Get column names
        columns = [column[0] for column in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        
        cursor.close()
        conn.close()
        return columns, rows
    except Exception as e:
        return None, str(e)

def ask_gemini_ai(user_question):
    """Instructs Gemini to write highly complex relational SQL joins based on our 4 tables"""
    system_prompt = """
    You are an expert Microsoft SQL Server T-SQL developer. 
    Given a user question, output ONLY a valid SQL query that answers it.
    Do not wrap the response in markdown blocks like ```sql. Do not provide explanations. Output raw text only.
    
    Database Schema:
    
    1. Table: Customers
       - CustomerID (VARCHAR(50), PK)
       - DisplayName (NVARCHAR(255))
       - CompanyName (NVARCHAR(255))
       - Balance (DECIMAL(18,2))
       - Active (BIT)
       
    2. Table: Invoices
       - InvoiceID (VARCHAR(50), PK)
       - CustomerID (VARCHAR(50), FK -> Customers.CustomerID)
       - DocNumber (NVARCHAR(50))
       - TxnDate (DATE)
       - TotalAmount (DECIMAL(18,2))
       
    3. Table: InvoiceLines
       - LineID (VARCHAR(50), PK)
       - InvoiceID (VARCHAR(50), FK -> Invoices.InvoiceID)
       - ItemName (NVARCHAR(255))
       - Quantity (INT)
       - Amount (DECIMAL(18,2))
       
    4. Table: Payments
       - PaymentID (VARCHAR(50), PK)
       - CustomerID (VARCHAR(50), FK -> Customers.CustomerID)
       - InvoiceID (VARCHAR(50), FK -> Invoices.InvoiceID)
       - PaymentDate (DATE)
       - AmountPaid (DECIMAL(18,2))
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"{system_prompt}\n\nUser Question: {user_question}\nSQL Query:"
        )
        return response.text.strip()
    except Exception as e:
        return f"Error contacting Gemini API: {e}"

# --- STREAMLIT USER INTERFACE CONFIGURATION ---
st.set_page_config(page_title="AI Financial Intelligence", layout="wide")

st.title("📊 Enterprise QuickBooks AI Warehouse Assistant")
st.write("Query your live QuickBooks data and synthetic financial records instantly using natural English.")

# Create a text input for the user
user_input = st.text_input(
    "Ask a complex financial question:", 
    placeholder="e.g., Which customers ordered software development services in the last 90 days but still have outstanding balances?"
)

if user_input:
    with st.spinner("🤖 AI is translating your question to T-SQL..."):
        generated_sql = ask_gemini_ai(user_input)
    
    # Display the generated SQL so clients can see the engineering depth
    st.subheader("📝 Generated Multi-Table T-SQL Query")
    st.code(generated_sql, language="sql")
    
    # Run the SQL query against MS SQL Server
    with st.spinner("⚡ Running query against database warehouse..."):
        cols, data = run_sql_query(generated_sql)
    
    # Handle the results
    if cols is not None:
        if len(data) > 0:
            # Convert pyodbc result to standard Pandas DataFrame
            df = pd.DataFrame(data=[list(row) for row in data], columns=cols)
            
            st.subheader("📋 Query Results")
            st.dataframe(df, use_container_width=True)
            
            # --- ONE-CLICK EXCEL EXPORT ENGINE ---
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='AI_Financial_Report')
            
            # Add the green Excel export button right below the dataframe
            st.download_button(
                label="📥 Export Financial Report to Excel",
                data=buffer.getvalue(),
                file_name="qb_ai_financial_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("ℹ️ The query executed successfully, but returned no matching records.")
    else:
        st.error(f"❌ Database execution error: {data}")