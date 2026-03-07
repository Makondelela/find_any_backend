# Fix Firebase API Key Error

## Problem
You're seeing: `API key not valid. Please pass a valid API key.`

Even though Email/Password and Google Sign-In are enabled in Firebase Console, the **Identity Toolkit API** needs to be enabled in Google Cloud Console.

## Solution - Enable Identity Toolkit API

### Step 1: Go to Google Cloud Console
Visit: https://console.cloud.google.com/apis/library/identitytoolkit.googleapis.com?project=find-any-55a42

### Step 2: Enable the API
1. Click the **"ENABLE"** button
2. Wait for it to enable (takes a few seconds)
3. You should see "API enabled" confirmation

### Step 3: Also Enable Identity Toolkit V1
Visit: https://console.cloud.google.com/apis/library/identitytoolkit.googleapis.com?project=find-any-55a42

Click **"ENABLE"** if not already enabled

### Step 4: Check API Key Restrictions (if still having issues)
1. Go to: https://console.cloud.google.com/apis/credentials?project=find-any-55a42
2. Find your API key (starts with `AIzaSyDAk6h8V9r...`)
3. Click on it to edit
4. Under **"API restrictions"**:
   - Select "Don't restrict key" (for testing)
   - OR select "Restrict key" and add:
     * Identity Toolkit API
     * Token Service API
5. Under **"Application restrictions"**:
   - For development: Select "None"
   - For production: Select "HTTP referrers" and add your domain
6. Click **"Save"**

### Step 5: Test Again
1. Reload the login page: http://127.0.0.1:5000/login
2. Try logging in with email/password or Google Sign-In
3. The API key error should be resolved

## Quick Links
- **Enable Identity Toolkit API**: https://console.cloud.google.com/apis/library/identitytoolkit.googleapis.com?project=find-any-55a42
- **API Credentials**: https://console.cloud.google.com/apis/credentials?project=find-any-55a42
- **Firebase Console**: https://console.firebase.google.com/project/find-any-55a42

## Alternative: Create Test User via Firebase Console
If you just want to test quickly with email/password:
1. Go to: https://console.firebase.google.com/project/find-any-55a42/authentication/users
2. Click "Add user"
3. Email: `test@example.com`
4. Password: `Test123!`
5. Click "Add user"

Then try logging in with those credentials.
