# Yahoo Developer App Configuration - Fix These Issues

## ❌ Issues Found in Your Configuration

### 1. **Redirect URI** (Update based on Yahoo's requirements)
**Yahoo requires HTTPS**, so use: `https://localhost`

**Why:** 
- Yahoo's interface now requires HTTPS for Redirect URIs
- The callback URI doesn't need to actually work - it's just validated
- No port number needed

**How to fix:**
1. In the "Redirect URI(s)" field, change it to: `https://localhost`
2. Remove the port number (`:8502`)
3. Make sure it's `https` (not `http`)

### 2. **OAuth Client Type is NOT SELECTED** (Critical!)
**Current:** Neither option selected  
**Should be:** "Confidential Client - Choose for traditional web apps"

**Why:**
- Your app is a web application (Streamlit)
- Confidential Client is required for server-side OAuth flows
- Without this selected, Yahoo won't process your OAuth requests

**How to fix:**
1. Select the radio button: **"Confidential Client - Choose for traditional web apps"**

### 3. **Homepage URL** (Optional but recommended)
**Current:** `https://localhost:8502`  
**Recommended:** `https://localhost:8502` or `http://localhost:8502` or leave blank

**Why:**
- This field is less critical
- Can match your actual setup or be left blank

**How to fix:**
1. Keep as is, or change to `http://localhost:8502` (if you want to specify)
2. Or leave blank if not required

## ✅ What's Already Correct

- **Application Name:** ✓
- **Description:** ✓
- **API Permissions:** ✓ Fantasy Sports with "Read" permission is checked

## Step-by-Step Fix Instructions

1. **Change Redirect URI:**
   - Find the "Redirect URI(s)" field
   - Delete: `https://localhost:8502`
   - Type: `https://localhost`
   - Make sure there are no spaces or trailing slashes
   - **Note:** Yahoo requires HTTPS, so use `https://localhost` (not `http://`)

2. **Select OAuth Client Type:**
   - Find "OAuth Client Type" section
   - Click the radio button: **"Confidential Client - Choose for traditional web apps"**

3. **Optional - Fix Homepage URL:**
   - Change `https://localhost:8502` to `http://localhost:8502` (if you want)
   - Or leave blank if not required

4. **Save the changes:**
   - Click "Save" or "Update" button
   - Wait 1-2 minutes for changes to propagate

5. **Test again:**
   - Go back to your Streamlit app
   - Click "Start Authentication"
   - The 401 error should be gone!

## Why These Matter

- **Redirect URI:** Yahoo validates this exactly. Since Yahoo requires HTTPS, use `https://localhost` (the URI doesn't need to actually work - it's just validated).
- **OAuth Client Type:** Without this selected, Yahoo doesn't know how to handle your OAuth requests, causing authentication failures.

## After Fixing

Once you've made these changes:
1. Save the app configuration
2. Wait 1-2 minutes
3. Try authentication again in your Streamlit app
4. You should now be able to get past the 401 error!
