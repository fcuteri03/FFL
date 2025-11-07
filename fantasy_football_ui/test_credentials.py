"""
Simple test to verify credentials are loaded correctly
"""

from pathlib import Path
import tomllib

secrets_path = Path(__file__).parent / ".streamlit" / "secrets.toml"

print("=" * 60)
print("Testing Credentials File")
print("=" * 60)
print()

if not secrets_path.exists():
    print(f"[ERROR] Secrets file not found at: {secrets_path}")
else:
    print(f"[OK] Secrets file found: {secrets_path}")
    print()
    
    try:
        with open(secrets_path, 'rb') as f:
            secrets = tomllib.load(f)
        
        yahoo_secrets = secrets.get('yahoo', {})
        consumer_key = yahoo_secrets.get('consumer_key', '')
        consumer_secret = yahoo_secrets.get('consumer_secret', '')
        
        print("Credentials loaded:")
        print(f"  Consumer Key: {consumer_key[:30]}... (length: {len(consumer_key)})")
        print(f"  Consumer Secret: {'*' * len(consumer_secret)} (length: {len(consumer_secret)})")
        print()
        
        if consumer_key and consumer_secret:
            print("[OK] Both credentials are present")
        else:
            print("[ERROR] Missing credentials")
            
    except Exception as e:
        print(f"[ERROR] Failed to read secrets file: {e}")

print()
print("=" * 60)
print("The 401 error means:")
print("1. Credentials are being sent correctly")
print("2. Yahoo is rejecting the request")
print()
print("Most likely causes:")
print("- Yahoo Developer app is not approved/active")
print("- Fantasy Sports API is not enabled")
print("- Callback URI is not set to 'oob'")
print("=" * 60)

