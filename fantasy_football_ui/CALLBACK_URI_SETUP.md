# Yahoo Callback URI Setup

## Required Setting

Yahoo requires a **valid URI format** for the callback/redirect URI. You cannot use `oob` or leave it blank.

## What to Set

In your Yahoo Developer app settings:

**Redirect URI / Callback URI:** `http://localhost`

## Steps

1. Go to https://developer.yahoo.com/apps/
2. Click on your app (App ID: 2iRMXUMG)
3. Click "Edit" or find the OAuth/Redirect URI setting
4. Set the Redirect URI to: `http://localhost`
5. **Save** the changes
6. Wait a minute or two for changes to propagate

## Why This Works

- `http://localhost` is a valid URI format that Yahoo accepts
- The app will automatically handle the OAuth flow
- You'll still get a verification code to enter manually (even though the callback is set)

## After Setting

1. Try authenticating in the app again
2. The app will use `http://localhost` as the callback
3. You'll still need to:
   - Click the authorization URL
   - Log in with your Yahoo account
   - Copy the verification code
   - Enter it in the app

## Alternative URIs (if localhost doesn't work)

If `http://localhost` doesn't work, try:
- `http://localhost:8080`
- `https://localhost`
- Any valid URL you control (if you have a domain)

The app will automatically try these alternatives if the first one fails.

