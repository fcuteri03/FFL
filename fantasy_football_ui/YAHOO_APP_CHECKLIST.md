# Yahoo Developer App Configuration Checklist

## ⚠️ Your app is getting 401 errors - this checklist will help fix it

### Step 1: Go to Yahoo Developer
1. Visit: https://developer.yahoo.com/apps/
2. Sign in with your Yahoo account
3. Find your app (App ID: `2iRMXUMG`)

### Step 2: Check App Status
**CRITICAL:** Your app MUST be in one of these states:
- ✅ **"Active"** - Good!
- ✅ **"Approved"** - Good!
- ❌ **"Pending"** - BAD! You need to wait for Yahoo approval
- ❌ **"Inactive"** - BAD! Activate it
- ❌ **"Rejected"** - BAD! Check why it was rejected

**If your app is "Pending":**
- New Yahoo Developer apps often need manual approval
- This can take hours to days
- You cannot use the API until it's approved
- Check back periodically

### Step 3: Check API Permissions
1. In your app settings, find **"API Permissions"** or **"Scopes"**
2. Look for **"Fantasy Sports"** or **"Fantasy Sports API"**
3. It MUST be **checked/enabled**
4. If it's not there or not enabled, enable it and SAVE

### Step 4: Check Redirect URI/Callback
1. Find **"Redirect URI"**, **"Callback URI"**, or **"OAuth Callback"**
2. Set it to exactly: `http://localhost`
   - No quotes
   - No trailing slash
   - No spaces
   - Lowercase only
3. SAVE the changes

### Step 5: Verify Credentials
- Consumer Key: `dj0yJmk9MTJPUUpsREhpd1F4JmQ9WVdrOU1tbFNUVmhWVFVjbWNHbzlNQT09JnM9Y29uc3VtZXJzZWNyZXQmc3Y9MCZ4PTVk`
- Consumer Secret: `fd54e033a23ac09e8de6f52286aaf64b3a000333`
- These are saved in the app and look correct

### Step 6: Wait and Retry
1. After making changes, **SAVE** the app
2. **Wait 1-2 minutes** for changes to propagate
3. Try authenticating again in the Streamlit app

## Common Issues

### "I can't find the app status"
- Look for a badge, indicator, or status field
- It might be in "View" mode vs "Edit" mode
- Try clicking different tabs/sections

### "I can't find API Permissions"
- Look for "Scopes", "Permissions", "APIs", or "Access"
- It might be under "OAuth Settings" or "Advanced"
- Some apps have it in a separate "Permissions" tab

### "I can't find Redirect URI"
- Look for "OAuth Settings", "Authentication", or "Callback"
- It might be called "Redirect URI", "Callback URI", or "OAuth Callback"
- Some interfaces call it "Application Website" or "Redirect URL"

### "My app is Pending"
- This is normal for new apps
- Yahoo manually reviews new applications
- You must wait for approval before using the API
- Check back in a few hours/days

## Still Not Working?

If you've checked everything and it's still not working:
1. Take a screenshot of your Yahoo Developer app settings page
2. Check if there are any error messages or warnings in Yahoo Developer
3. Try creating a new Yahoo Developer app (sometimes helps)
4. Contact Yahoo Developer Support

## Test Script

Run this to test if your app is working:
```bash
cd fantasy_football_ui
py test_yahoo_oauth.py
```

If all callbacks fail with 401, it's definitely an app configuration issue.

