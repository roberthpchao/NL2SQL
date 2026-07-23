# connect.py
import os
import sys
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
from intuitlib.client import AuthClient
from intuitlib.enums import Scopes

load_dotenv()

auth_client = AuthClient(
    client_id=os.getenv("QB_CLIENT_ID"),
    client_secret=os.getenv("QB_CLIENT_SECRET"),
    redirect_uri=os.getenv("QB_REDIRECT_URI"),
    environment=os.getenv("QB_ENVIRONMENT", "sandbox")
)

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Respond to browser instantly so user knows it worked
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h1>Success!</h1><p>Tokens captured! You can close this tab and return to VS Code.</p>")
        
        # Pull parameters from the Intuit Redirect URL
        query_components = parse_qs(urlparse(self.path).query)
        
        if "code" in query_components:
            auth_code = query_components["code"][0]
            realm_id = query_components["realmId"][0]
           
            # --- DEBUGGING PRINTS ---
            print("\n🔍 DEBUGGING KEYS SENT TO INTUIT:")
            print(f"Loaded Client ID:     {auth_client.client_id}")
            print(f"Loaded Client Secret: {auth_client.client_secret[:5]}...")
            print(f"Loaded Environment:   {auth_client.environment}")
            print(f"Captured Auth Code:   {auth_code[:15]}...\n")
            # ------------------------
            
            # Exchange code for actual security tokens
            auth_client.get_bearer_token(auth_code, realm_id=realm_id)
            
            # CRITICAL FIX: Write the file immediately BEFORE any loop interrupts!
            print("\n💾 Tokens intercepted! Writing tokens.env now...")
            with open("tokens.env", "w") as f:
                f.write(f"QB_REALM_ID={auth_client.realm_id}\n")
                f.write(f"QB_ACCESS_TOKEN={auth_client.access_token}\n")
                f.write(f"QB_REFRESH_TOKEN={auth_client.refresh_token}\n")
            
            print("="*50)
            print("🎉 tokens.env CREATED SUCCESSFULLY!")
            print("="*50 + "\n")
            
            # Force a hard exit of the python process so the terminal returns to normal
            os._exit(0)

def run_auth_flow():
    scopes = [Scopes.ACCOUNTING]
    auth_url = auth_client.get_authorization_url(scopes)
    
    print("🌍 Opening your browser to authorize QuickBooks Sandbox access...")
    webbrowser.open(auth_url)
    
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, OAuthCallbackHandler)
    httpd.serve_forever()

if __name__ == "__main__":
    run_auth_flow()