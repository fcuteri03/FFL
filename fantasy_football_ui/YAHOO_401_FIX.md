# Fixing 401 Unauthorized Error

## The Problem

You're getting a **401 Unauthorized** error from Yahoo. This means Yahoo is **rejecting your OAuth request** before it even gets to the authorization step.

**This is NOT a code problem** - it's a Yahoo Developer app configuration issue.

## Diagnostic Results

The diagnostic test (`test_yahoo_oauth_detailed.py`) confirmed:
- ✅ Your credentials are loaded correctly
- ✅ The OAuth code is working
- ❌ **ALL callback URIs fail with 401** - this means Yahoo is rejecting the app itself

## What This Means

When **all** callback URIs fail with 401, it means:
- The issue is NOT the Redirect URI
- The issue is with your **Yahoo Developer app configuration**
- Yahoo is blocking your app from making OAuth requests

## Most Likely Causes (in order)

### 1. App Status is "Pending" (MOST COMMON)
**This is the #1 cause of 401 errors for new Yahoo apps.**

- New Yahoo Developer apps need manual approval
- Status must be "Active" or "Approved" to use the API
- "Pending" apps cannot make OAuth requests (401 error)
- Approval can take **hours to days**

**How to check:**
1. Go to https://developer.yahoo.com/apps/
2. Find your app (App ID: `2iRMXUMG`)
3. Look for "Status", "App Status", or a badge/indicator
4. If it says "Pending", you must wait for Yahoo approval

**What to do:**
- Wait for Yahoo to approve your app
- Check back periodically
- There's nothing you can do to speed this up

### 2. OAuth Client Type Not Selected
**This is REQUIRED for server-side OAuth.**

- Must select: "Confidential Client - Choose for traditional web apps"
- Without this, Yahoo doesn't know how to handle your OAuth requests

**How to fix:**
1. Go to your app settings
2. Find "OAuth Client Type" section
3. Select: "Confidential Client - Choose for traditional web apps"
4. Save

### 3. Fantasy Sports API Not Enabled
**Your app needs permission to access Fantasy Sports data.**

- Fantasy Sports API must be checked/enabled
- Must have "Read" permission selected

**How to check:**
1. Go to "API Permissions" or "Scopes" section
2. Find "Fantasy Sports"
3. Make sure it's checked
4. Make sure "Read" is selected

### 4. Redirect URI Mismatch (Less Likely)
**Since ALL callbacks fail, this is probably not the issue, but check anyway.**

- Redirect URI should be: `https://localhost` or `http://localhost`
- No port number, no trailing slash

## Step-by-Step Fix Checklist

Go through this checklist in order:

- [ ] **1. Check App Status**
  - Go to https://developer.yahoo.com/apps/
  - Find app ID: `2iRMXUMG`
  - What does the status say?
    - ✅ "Active" or "Approved" → Good! Continue to next step
    - ❌ "Pending" → **STOP HERE** - You must wait for approval
    - ❌ "Inactive" → Activate it
    - ❌ "Rejected" → Check why it was rejected

- [ ] **2. Select OAuth Client Type**
  - Find "OAuth Client Type" section
  - Select: "Confidential Client - Choose for traditional web apps"
  - Save

- [ ] **3. Check API Permissions**
  - Find "API Permissions" or "Scopes"
  - Make sure "Fantasy Sports" is checked
  - Make sure "Read" permission is selected
  - Save

- [ ] **4. Set Redirect URI**
  - Find "Redirect URI(s)" field
  - Set to: `https://localhost` (no port, no trailing slash)
  - Save

- [ ] **5. Wait and Test**
  - Save all changes
  - Wait 1-2 minutes for changes to propagate
  - Run diagnostic: `py test_yahoo_oauth_detailed.py`
  - Try authentication in the app again

## If App Status is "Pending"

**This is the most common issue.** New Yahoo Developer apps need approval before they can use the API.

**What to do:**
1. Wait for Yahoo to approve your app
2. Check back periodically (can take hours to days)
3. Once approved, the 401 error should go away

**You cannot bypass this** - Yahoo requires manual approval for new apps.

## Still Not Working?

If you've checked everything and it's still failing:

1. **Take a screenshot** of your Yahoo Developer app settings page
2. **Check the exact error message** in the Streamlit app (expand "Error Details")
3. **Run the diagnostic** and share the output:
   ```bash
   cd fantasy_football_ui
   py test_yahoo_oauth_detailed.py
   ```

## Summary

The 401 error means Yahoo is rejecting your app. The most common cause is:
- **App Status is "Pending"** - You must wait for Yahoo approval

Other causes:
- OAuth Client Type not selected
- Fantasy Sports API not enabled
- Redirect URI mismatch

Once your app is "Active" or "Approved" and all settings are correct, authentication should work!

