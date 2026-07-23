import os
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load local and cloud credential tokens
load_dotenv()
load_dotenv("tokens.env")

# 1. Initialize Gemini Client using the modern SDK layout
# Make sure GEMINI_API_KEY is defined in your local .env file
@st.cache_resource
def get_gemini_client():
    return genai.Client()

ai_client = get_gemini_client()

# 2. Database Routing Logic
def get_db_connection(stack_option):
    """Dynamically routes database queries based on the UI toggle selection"""
    if stack_option == "☁️ Azure Cloud Warehouse":
        from config.engine_cloud import get_cloud_connection
        return get_cloud_connection()
    else:
        from config.engine_local import get_local_connection
        return get_local_connection()

# 3. Streamlit Page Configuration
st.set_page_config(page_title="Enterprise QuickBooks NL2SQL Engine", layout="wide")

# Sidebar Configuration Control Panel
st.sidebar.title("🎛️ Control Panel")
stack_selection = st.sidebar.radio(
    "Target Data Stack Environment:",
    ("🏠 Local Stack (.\SQLEXPRESS)", "☁️ Azure Cloud Warehouse")
)

st.sidebar.markdown("---")
st.sidebar.info(
    f"**Active AI Engine:** Google Gemini\n\n"
    f"**Active Database:** {stack_selection}"
)

# Main Application Headers
st.title("📊 QuickBooks Financial AI Warehouse Engine")
st.subheader("Translate conversational natural language into production-grade T-SQL insights")

# 4. Define the AI System Prompt Architecture
SCHEMA_PROMPT = """
You are an expert T-SQL translation engine for an enterprise financial warehouse.
Your sole job is to translate conversational requests into valid, clean T-SQL syntax based exclusively on this 4-table schema:

1. Customers (CustomerID VARCHAR PRIMARY KEY, DisplayName NVARCHAR, CompanyName NVARCHAR, Balance DECIMAL, Active BIT)
2. Invoices (InvoiceID VARCHAR PRIMARY KEY, CustomerID VARCHAR FK, DocNumber NVARCHAR, TxnDate DATE, TotalAmount DECIMAL)
3. InvoiceLines (LineID VARCHAR PRIMARY KEY, InvoiceID VARCHAR FK, ItemName NVARCHAR, Quantity INT, Amount DECIMAL)
4. Payments (PaymentID VARCHAR PRIMARY KEY, CustomerID VARCHAR FK, InvoiceID VARCHAR FK, PaymentDate DATE, AmountPaid DECIMAL)

CRITICAL RULES:
- Return ONLY the executable T-SQL code block.
- Do NOT wrap the query inside markdown code blocks like ```sql or ```. Return raw text only.
- Ensure all string searches use LIKE with safe wildcards where appropriate.
- Always perform accurate JOIN tracking across table keys.
"""

user_query = st.text_input(
    "Enter your financial question (e.g., 'Show me total sales by customer company name ordered by highest spending'):",
    placeholder="What would you like to extract from the warehouse?"
)

if user_query:
    with st.spinner("🤖 Gemini is parsing schema and constructing secure T-SQL pipeline..."):
        try:
            # 5. Call Gemini using the official v1 configuration protocol
            response = ai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=user_query,
                config=types.GenerateContentConfig(
                    system_instruction=SCHEMA_PROMPT,
                    temperature=0.0  # Force maximum determination precision for code execution
                )
            )
            
            generated_sql = response.text.strip()
            
            # Render the query clean for verification
            st.markdown("### 🖥️ Generated T-SQL Execution Script")
            st.code(generated_sql, language="sql")
            
            # 6. Execute directly against the chosen environment
            with st.spinner("⏳ Querying target database cluster..."):
                conn = get_db_connection(stack_selection)
                df = pd.read_sql(generated_sql, conn)
                conn.close()
                
            if not df.empty:
                st.markdown("### 📈 Extracted Data Insights")
                st.dataframe(df, use_container_width=True)
                
                # Built-in live reporting exporter
                st.markdown("---")
                excel_file = "financial_extract.xlsx"
                df.to_excel(excel_file, index=False, engine='openpyxl')
                with open(excel_file, "rb") as f:
                    st.download_button(
                        label="📥 Download Data Extract as Excel",
                        data=f,
                        file_name=excel_file,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.warning("Query executed successfully, but returned 0 records matching those constraints.")
                
        except Exception as e:
            st.error(f"Execution Error Encountered: {e}")