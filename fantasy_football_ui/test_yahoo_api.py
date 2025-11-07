"""
Test script to verify Yahoo Fantasy API access
"""

import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from fantasy_football_api.oauth_helper import YahooOAuthHelper

def test_oauth_credentials():
    """Test if OAuth credentials work"""
    print("=" * 60)
    print("Testing Yahoo OAuth Credentials")
    print("=" * 60)
    
    # Load credentials from secrets
    try:
        import streamlit as st
        from streamlit import runtime
        if runtime.exists():
            # Running in Streamlit context
            if hasattr(st, 'secrets') and 'yahoo' in st.secrets:
                yahoo_secrets = st.secrets['yahoo']
                consumer_key = yahoo_secrets.get('consumer_key', '')
                consumer_secret = yahoo_secrets.get('consumer_secret', '')
            else:
                print("[ERROR] No credentials found in Streamlit secrets")
                return False
        else:
            # Not in Streamlit, read from file directly
            secrets_path = Path(__file__).parent / ".streamlit" / "secrets.toml"
            if not secrets_path.exists():
                print(f"[ERROR] Secrets file not found at: {secrets_path}")
                return False
            
            import tomllib
            with open(secrets_path, 'rb') as f:
                secrets = tomllib.load(f)
            yahoo_secrets = secrets.get('yahoo', {})
            consumer_key = yahoo_secrets.get('consumer_key', '')
            consumer_secret = yahoo_secrets.get('consumer_secret', '')
    except Exception as e:
        print(f"[ERROR] Error loading credentials: {e}")
        return False
    
    if not consumer_key or not consumer_secret:
        print("[ERROR] Consumer Key or Secret is missing")
        return False
    
        print(f"[OK] Consumer Key found: {consumer_key[:20]}...")
        print(f"[OK] Consumer Secret found: {consumer_secret[:10]}...")
    print()
    
    # Test OAuth flow - Step 1: Get request token
    print("Step 1: Testing request token retrieval...")
    try:
        oauth_helper = YahooOAuthHelper(consumer_key, consumer_secret)
        request_token, request_token_secret = oauth_helper.get_request_token()
        
        print(f"[OK] Request token obtained successfully!")
        print(f"  Token: {request_token[:20]}...")
        print()
        
        # Step 2: Get authorization URL
        print("Step 2: Generating authorization URL...")
        auth_url = oauth_helper.get_authorization_url(request_token)
        print(f"[OK] Authorization URL generated!")
        print(f"  URL: {auth_url}")
        print()
        
        print("=" * 60)
        print("[SUCCESS] OAuth credentials are VALID!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Visit the authorization URL above")
        print("2. Log in with your Yahoo account")
        print("3. Authorize the application")
        print("4. Copy the verification code")
        print("5. Use it in the Streamlit app to complete authentication")
        print()
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error during OAuth test: {str(e)}")
        print()
        print("Possible issues:")
        print("1. Consumer Key or Secret is incorrect")
        print("2. Yahoo Developer app is not approved/active")
        print("3. Fantasy Sports API is not enabled in your app")
        print("4. Callback URI is not configured correctly (should be 'oob')")
        print()
        return False

def test_api_access():
    """Test if we can access Yahoo Fantasy API with access tokens"""
    print("=" * 60)
    print("Testing Yahoo Fantasy API Access")
    print("=" * 60)
    
    try:
        import streamlit as st
        from streamlit import runtime
        if runtime.exists():
            if hasattr(st, 'secrets') and 'yahoo' in st.secrets:
                yahoo_secrets = st.secrets['yahoo']
                consumer_key = yahoo_secrets.get('consumer_key', '')
                consumer_secret = yahoo_secrets.get('consumer_secret', '')
                access_token = yahoo_secrets.get('access_token', '')
                access_token_secret = yahoo_secrets.get('access_token_secret', '')
            else:
                print("[ERROR] No credentials found")
                return False
        else:
            secrets_path = Path(__file__).parent / ".streamlit" / "secrets.toml"
            if not secrets_path.exists():
                print(f"[ERROR] Secrets file not found")
                return False
            
            import tomllib
            with open(secrets_path, 'rb') as f:
                secrets = tomllib.load(f)
            yahoo_secrets = secrets.get('yahoo', {})
            consumer_key = yahoo_secrets.get('consumer_key', '')
            consumer_secret = yahoo_secrets.get('consumer_secret', '')
            access_token = yahoo_secrets.get('access_token', '')
            access_token_secret = yahoo_secrets.get('access_token_secret', '')
    except Exception as e:
        print(f"[ERROR] Error loading credentials: {e}")
        return False
    
    if not access_token or not access_token_secret:
        print("[ERROR] Access tokens not found. Please complete OAuth flow first.")
        return False
    
    print("[OK] Access tokens found")
    print()
    
    # Test API call
    try:
        from fantasy_football_api import YahooClient
        
        client = YahooClient(consumer_key, consumer_secret, access_token, access_token_secret)
        
        # Try to get user games (a simple API call)
        print("Testing API call: get_user_games()...")
        games = client.get_user_games()
        
        print("[OK] API call successful!")
        print("[SUCCESS] Yahoo Fantasy API is accessible!")
        return True
        
    except Exception as e:
        print(f"[ERROR] API call failed: {str(e)}")
        print("Access tokens may be expired. Please re-authenticate.")
        return False

if __name__ == "__main__":
    print()
    print("Yahoo Fantasy API Test Script")
    print()
    
    # Test 1: OAuth credentials
    oauth_works = test_oauth_credentials()
    print()
    
    # Test 2: API access (if we have access tokens)
    if oauth_works:
        print()
        api_works = test_api_access()
    
    print()
    print("=" * 60)
    print("Test Complete")
    print("=" * 60)

