# Firebase Authentication Setup Guide

## Step 1: Create a Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Add project" or select existing project
3. Follow the setup wizard

## Step 2: Enable Authentication

1. In Firebase Console, go to **Build** → **Authentication**
2. Click **Get Started**
3. Enable **Email/Password** sign-in method
4. Enable **Google** sign-in method

## Step 3: Get Firebase Configuration (Frontend)

1. In Firebase Console, go to **Project Settings** (gear icon)
2. Scroll down to "Your apps"
3. Click the **Web** icon `</>`
4. Register your app
5. Copy the `firebaseConfig` object
6. Replace the config in `templates/login.html` (around line 108)

Example:
```javascript
const firebaseConfig = {
    apiKey: "AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXX",
    authDomain: "your-app.firebaseapp.com",
    projectId: "your-app",
    storageBucket: "your-app.appspot.com",
    messagingSenderId: "123456789",
    appId: "1:123456789:web:xxxxx"
};
```

## Step 4: Get Service Account Key (Backend)

1. In Firebase Console, go to **Project Settings** → **Service Accounts**
2. Click **Generate New Private Key**
3. Download the JSON file
4. Rename it to `firebase-service-account.json`
5. Place it in the project root directory (same folder as `app.py`)
6. **IMPORTANT**: Add `firebase-service-account.json` to `.gitignore`

## Step 5: Install Required Packages

```bash
pip install firebase-admin
```

## Step 6: Update .gitignore

Add this line to `.gitignore`:
```
firebase-service-account.json
```

## Step 7: Test the Setup

1. Start your Flask server:
   ```bash
   python app.py
   ```

2. Navigate to `http://localhost:5000/login`

3. Try these login methods:
   - Create a test user in Firebase Console (Authentication → Users → Add User)
   - Use Google Sign-In button
   - Test password reset

## Security Notes

- ✅ Keep `firebase-service-account.json` private and never commit it
- ✅ Use environment variables in production
- ✅ Set up Firebase Security Rules
- ✅ Enable app verification for Google Sign-In in production
- ✅ Change `app.secret_key` to a secure random string

## Optional: Create Test User via Firebase Console

1. Go to **Authentication** → **Users** tab
2. Click **Add User**
3. Enter email and password
4. Click **Add User**
5. Use these credentials to test login

## Production Deployment

For production, use environment variables:

```python
# In app.py
import os

app.secret_key = os.environ.get('SECRET_KEY', 'dev-key')

# For Firebase service account
service_account_path = os.environ.get('FIREBASE_SERVICE_ACCOUNT', 'firebase-service-account.json')
cred = credentials.Certificate(service_account_path)
```

Set environment variables:
```bash
export SECRET_KEY="your-random-secret-key"
export FIREBASE_SERVICE_ACCOUNT="/path/to/service-account.json"
```
