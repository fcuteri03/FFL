# Yahoo Credentials Setup

## Automatic Setup (Recommended)

1. Open the app and select "Yahoo", "Both", or "Merged" in the sidebar
2. Enter your Consumer Key and Consumer Secret
3. Click "Authenticate with Yahoo"
4. Follow the OAuth flow
5. Your credentials will be automatically saved to `.streamlit/secrets.toml`

## Manual Setup (If you have credentials)

If you already have your Yahoo credentials and want to add them directly, you can create or edit the file:

**Location:** `fantasy_football_ui/.streamlit/secrets.toml`

**Format:**
```toml
[yahoo]
consumer_key = "your_consumer_key_here"
consumer_secret = "your_consumer_secret_here"
access_token = "your_access_token_here"
access_token_secret = "your_access_token_secret_here"
```

**Note:** 
- The `secrets.toml` file is in `.gitignore` by default, so your credentials won't be committed to version control
- You only need to authenticate once - the app will remember your credentials
- If your access tokens expire, you'll need to re-authenticate

## Getting Yahoo Developer Credentials

1. Go to https://developer.yahoo.com/apps/
2. Create a new app
3. Copy your Consumer Key and Consumer Secret
4. Use these in the app's OAuth flow

