"""
Test Yahoo OAuth to diagnose 401 errors
"""

import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from requests_oauthlib import OAuth1Session
import requests

# Load credentials
secrets_path = Path(__file__).parent / ".streamlit" / "secrets.toml"
import tomllib

with open(secrets_path, 'rb') as f:
    secrets = tomllib.load(f)

yahoo_secrets = secrets.get('yahoo', {})
consumer_key = yahoo_secrets.get('consumer_key', '')
consumer_secret = yahoo_secrets.get('consumer_secret', '')

print("=" * 60)
print("Yahoo OAuth Diagnostic Test")
print("=" * 60)
print()
print(f"Consumer Key: {consumer_key[:30]}... (length: {len(consumer_key)})")
print(f"Consumer Secret: {'*' * len(consumer_secret)} (length: {len(consumer_secret)})")
print()

# Test different callback URIs
callbacks_to_try = [
    ("http://localhost", "http://localhost"),
    ("oob", "oob"),
    ("", "empty string"),
    ("http://localhost:8080", "http://localhost:8080"),
]

print("Testing different callback URIs...")
print()

for callback_uri, description in callbacks_to_try:
    print(f"Testing: {description}")
    try:
        oauth_session = OAuth1Session(
            consumer_key,
            client_secret=consumer_secret,
            callback_uri=callback_uri if callback_uri else None
        )
        
        request_token_url = "https://api.login.yahoo.com/oauth/v1/get_request_token"
        
        # Make request and capture response details
        response = oauth_session.fetch_request_token(request_token_url)
        
        request_token = response.get('oauth_token')
        request_token_secret = response.get('oauth_token_secret')
        
        if request_token and request_token_secret:
            print(f"  [SUCCESS] Got request token: {request_token[:20]}...")
            print()
            print("=" * 60)
            print("SUCCESS! OAuth is working!")
            print("=" * 60)
            print()
            print(f"Authorization URL:")
            print(f"https://api.login.yahoo.com/oauth/v1/request_auth?oauth_token={request_token}")
            sys.exit(0)
        else:
            print(f"  [FAILED] No tokens returned")
    except Exception as e:
        error_msg = str(e)
        print(f"  [FAILED] {error_msg}")
        
        # Try to get more details
        if hasattr(e, 'response') and e.response is not None:
            try:
                print(f"  Response status: {e.response.status_code}")
                print(f"  Response text: {e.response.text[:200]}")
            except:
                pass
    print()

print("=" * 60)
print("ALL CALLBACKS FAILED")
print("=" * 60)
print()
print("This means Yahoo is rejecting your OAuth request.")
print()
print("Most likely causes:")
print("1. Yahoo Developer app is NOT approved/active")
print("2. Fantasy Sports API is NOT enabled")
print("3. App status is 'Pending' or 'Inactive'")
print()
print("What to do:")
print("1. Go to https://developer.yahoo.com/apps/")
print("2. Find your app (App ID: 2iRMXUMG)")
print("3. Check the app STATUS - it must be 'Active' or 'Approved'")
print("4. Check API PERMISSIONS - Fantasy Sports must be enabled")
print("5. Set Redirect URI to: http://localhost")
print("6. SAVE and wait 1-2 minutes")
print()
print("If the app is 'Pending', you may need to wait for Yahoo approval.")
print("New apps can take time to be approved.")

