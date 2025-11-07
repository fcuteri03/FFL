# Yahoo Developer App Setup Guide

## Where to Find Settings

### Option 1: App Details Page
1. Go to https://developer.yahoo.com/apps/
2. Click on your app (App ID: 2iRMXUMG)
3. Look for these sections:
   - **Application Status** - Usually at the top
   - **OAuth Settings** or **Authentication** - Look for callback URI
   - **API Access** or **Permissions** - Look for Fantasy Sports

### Option 2: Edit Application
1. Click "Edit Application" or the edit icon
2. Look for tabs or sections:
   - **General** - App name, description
   - **OAuth Settings** - Callback Domain/URI
   - **API Access** - Which APIs are enabled
   - **Advanced** - Additional settings

### Option 3: Check Different Views
- Try clicking "View" vs "Edit"
- Look for a "Settings" or "Configuration" tab
- Check if there's a dropdown menu with different sections

## What to Look For

### Callback Domain/URI
- Should be set to: `oob` (out-of-band)
- OR leave it blank/empty
- This is CRITICAL for the OAuth flow to work

### Fantasy Sports API
- Look for a list of APIs or permissions
- Make sure "Fantasy Sports" or "Fantasy Sports API" is checked/enabled
- Sometimes it's under "Read" permissions

### App Status
- Should say "Active", "Approved", or "Live"
- If it says "Pending" or "Inactive", that's the problem

## If You Can't Find These Settings

Yahoo's interface varies. Try:

1. **Screenshot the page** - I can help identify where settings are
2. **Look for "OAuth 1.0" or "OAuth Settings"** - This is where callback goes
3. **Check for "APIs" or "Scopes"** - This is where Fantasy Sports should be
4. **Look for any "Status" indicator** - Usually green = active

## Alternative: Test with Different Callback

If you can't find the callback setting, we can try:
- Setting callback to: `http://localhost` 
- Or: `urn:ietf:wg:oauth:2.0:oob`
- Or: Leave it completely blank

## Quick Checklist

- [ ] App is visible in your developer dashboard
- [ ] You can see Consumer Key and Secret (you have these)
- [ ] Look for any "Status" or "State" indicator
- [ ] Find OAuth/Callback settings
- [ ] Find API/Permissions list
- [ ] Enable Fantasy Sports if it's not already

## Still Having Issues?

If you can't find these settings:
1. Take a screenshot of what you see
2. Or describe what sections/tabs you can see
3. We can modify the code to work with different callback settings

