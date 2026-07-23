import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

# Initialize the Gemini client using the key from your .env file
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def ask_gemini_ai(user_question):
    """Sends the multi-table database layout and client question to Gemini to generate raw T-SQL"""
    
    # We define the advanced 4-table structure to the AI so it knows how to write JOIN statements
    system_prompt = """
    You are an expert Microsoft SQL Server T-SQL developer. 
    Given a user question, output ONLY a valid SQL query that answers it.
    Do not wrap the response in markdown blocks like ```sql. Do not provide explanations. Output raw text only.
    
    Database Table Structure:
    
    1. Table Name: Customers
       - CustomerID (VARCHAR(50), Primary Key)
       - DisplayName (NVARCHAR(255))
       - CompanyName (NVARCHAR(255))
       - Balance (DECIMAL(18,2))
       - Active (BIT)
       
    2. Table Name: Invoices
       - InvoiceID (VARCHAR(50), Primary Key)
       - CustomerID (VARCHAR(50), Foreign Key -> Customers.CustomerID)
       - DocNumber (NVARCHAR(50))
       - TxnDate (DATE)
       - TotalAmount (DECIMAL(18,2))
       
    3. Table Name: InvoiceLines
       - LineID (VARCHAR(50), Primary Key)
       - InvoiceID (VARCHAR(50), Foreign Key -> Invoices.InvoiceID)
       - ItemName (NVARCHAR(255))
       - Quantity (INT)
       - Amount (DECIMAL(18,2))
       
    4. Table Name: Payments
       - PaymentID (VARCHAR(50), Primary Key)
       - CustomerID (VARCHAR(50), Foreign Key -> Customers.CustomerID)
       - InvoiceID (VARCHAR(50), Foreign Key -> Invoices.InvoiceID)
       - PaymentDate (DATE)
       - AmountPaid (DECIMAL(18,2))
    """
    
    try:
        # Call the lightweight, high-speed gemini-2.5-flash model
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"{system_prompt}\n\nUser Question: {user_question}\nSQL Query:"
        )
        return response.text.strip()
    except Exception as e:
        return f"Error contacting Gemini API: {e}"

# Simple test to verify the API key connection works perfectly
if __name__ == "__main__":
    test_question = "Which customer has the highest balance?"
    print(f"🤔 Testing Question: '{test_question}'")
    print("⏳ Querying Gemini...")
    sql_result = ask_gemini_ai(test_question)
    print("\n📝 Generated SQL Output:")
    print(sql_result)
    