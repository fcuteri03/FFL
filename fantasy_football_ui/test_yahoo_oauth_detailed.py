"""
Detailed Yahoo OAuth diagnostic script
Tests each step of the OAuth flow to identify where it fails
"""

import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from fantasy_football_api.yahoo_oauth_simple import YahooOAuthSimple
import toml

def load_credentials():
    """Load credentials from secrets.toml"""
    secrets_file = Path(__file__).parent / ".streamlit" / "secrets.toml"
    if secrets_file.exists():
        secrets = toml.load(secrets_file)
        yahoo = secrets.get("yahoo", {})
        return yahoo.get("consumer_key"), yahoo.get("consumer_secret")
    return None, None

def test_oauth_flow():
    """Test the OAuth flow step by step"""
    print("=" * 60)
    print("Yahoo OAuth Diagnostic Test")
    print("=" * 60)
    print()
    
    # Load credentials
    consumer_key, consumer_secret = load_credentials()
    
    if not consumer_key or not consumer_secret:
        print("[ERROR] Could not load credentials from secrets.toml")
        print("Make sure .streamlit/secrets.toml exists with:")
        print("  [yahoo]")
        print("  consumer_key = '...'")
        print("  consumer_secret = '...'")
        return
    
    print(f"[OK] Loaded Consumer Key: {consumer_key[:30]}...")
    print(f"[OK] Loaded Consumer Secret: {'*' * len(consumer_secret)}")
    print()
    
    # Initialize OAuth helper
    print("Step 1: Initializing OAuth helper...")
    try:
        oauth_helper = YahooOAuthSimple(consumer_key, consumer_secret)
        print("[OK] OAuth helper initialized")
    except Exception as e:
        print(f"[ERROR] Failed to initialize: {e}")
        return
    print()
    
    # Test different callback URIs
    callbacks_to_test = [
        "https://localhost",
        "http://localhost",
        "oob",
        "",
    ]
    
    print("Step 2: Testing request token with different callback URIs...")
    print("-" * 60)
    
    request_token = None
    request_token_secret = None
    auth_url = None
    successful_callback = None
    
    for callback_uri in callbacks_to_test:
        callback_display = callback_uri if callback_uri else "(empty)"
        print(f"\nTrying callback URI: {callback_display}")
        
        try:
            oauth_helper = YahooOAuthSimple(consumer_key, consumer_secret)
            request_token, request_token_secret, auth_url = oauth_helper.get_request_token(callback_uri)
            
            if request_token and request_token_secret:
                print(f"[SUCCESS] Got request token with callback: {callback_display}")
                print(f"  Request Token: {request_token[:30]}...")
                print(f"  Auth URL: {auth_url}")
                successful_callback = callback_uri
                break
        except Exception as e:
            error_str = str(e)
            print(f"[FAILED] {error_str}")
            
            # Check for specific error types
            if "401" in error_str or "Unauthorized" in error_str:
                print("  -> This is a 401 Unauthorized error")
                print("  -> Yahoo is rejecting the request")
                print("  -> Check your Yahoo Developer app configuration:")
                print("     - App Status must be 'Active' or 'Approved'")
                print("     - OAuth Client Type must be 'Confidential Client'")
                print("     - Fantasy Sports API must be enabled")
                print("     - Redirect URI must match one of the callbacks above")
            elif "403" in error_str or "Forbidden" in error_str:
                print("  -> This is a 403 Forbidden error")
                print("  -> Your app may not have permission to access Fantasy Sports API")
            else:
                print(f"  -> Error type: {type(e).__name__}")
    
    print()
    print("-" * 60)
    
    if not request_token:
        print()
        print("[ERROR] Failed to get request token with all callback URIs")
        print()
        print("TROUBLESHOOTING:")
        print("1. Verify your Consumer Key and Secret are correct")
        print("2. Check your Yahoo Developer app at: https://developer.yahoo.com/apps/")
        print("3. Make sure:")
        print("   - App Status is 'Active' or 'Approved' (not 'Pending')")
        print("   - OAuth Client Type is set to 'Confidential Client'")
        print("   - Fantasy Sports API permission is enabled")
        print("   - Redirect URI is set to one of: https://localhost, http://localhost, or oob")
        print("4. Save changes in Yahoo Developer and wait 1-2 minutes")
        return
    
    print()
    print("=" * 60)
    print("SUCCESS! OAuth flow can proceed")
    print("=" * 60)
    print()
    print(f"Successful Callback URI: {successful_callback or '(empty)'}")
    print(f"Request Token: {request_token[:30]}...")
    print()
    print("Next steps:")
    print(f"1. Visit this URL in your browser: {auth_url}")
    print("2. Log in with your Yahoo account")
    print("3. Copy the verification code")
    print("4. Use it in the Streamlit app to complete authentication")
    print()

if __name__ == "__main__":
    test_oauth_flow()

