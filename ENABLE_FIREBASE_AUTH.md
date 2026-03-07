# Enable Firebase Authentication

Your Firebase project is configured but authentication methods need to be enabled.

## Quick Steps to Enable Authentication:

### 1. Go to Firebase Console
Visit: https://console.firebase.google.com/project/find-any-55a42/authentication/providers

### 2. Enable Email/Password Authentication
1. Click on **"Email/Password"** in the Sign-in method tab
2. Click the **"Enable"** toggle switch
3. Make sure **both** "Email/Password" and "Email link (passwordless sign-in)" are enabled
4. Click **"Save"**

### 3. Enable Google Sign-In
1. Click on **"Google"** in the Sign-in providers list
2. Click the **"Enable"** toggle switch
3. Enter a support email (use your email address)
4. Click **"Save"**

### 4. Create a Test User (Optional)
1. Go to the **"Users"** tab at: https://console.firebase.google.com/project/find-any-55a42/authentication/users
2. Click **"Add user"**
3. Enter test email: `test@example.com`
4. Enter password: `Test123!`
5. Click **"Add user"**

## After Enabling:

1. Restart your Flask app if it's running
2. Visit http://127.0.0.1:5000/login
3. Try logging in with:
   - Email/Password (if you created a test user)
   - Google Sign-In button

## Current Configuration:
- ✅ Project ID: `find-any-55a42`
- ✅ Service Account Key: Configured
- ✅ Firebase Client SDK: Configured
- ⏳ Email/Password Auth: **NEEDS TO BE ENABLED**
- ⏳ Google Sign-In: **NEEDS TO BE ENABLED**

## Common Issues:

**"API key not valid" error:**
- This means authentication methods aren't enabled yet
- Follow steps 2 & 3 above to enable them

**"User not found" error:**
- Create a test user in Firebase Console (step 4)
- Or use Google Sign-In

**Google popup blocked:**
- Allow popups in your browser for localhost
- Try again after allowing popups
