# Firebase Service Account Setup

## Current Status

✅ Frontend Firebase configured with web credentials  
⚠️ Backend needs service account credentials

## Why Service Account?

The backend needs **Admin SDK credentials** to:
- Read/write to Realtime Database without authentication
- Run scraper pipeline with elevated permissions
- Manage user data and scrape jobs

## Quick Setup (3 steps)

### Step 1: Go to Firebase Console

Open: https://console.firebase.google.com/project/find-any-55a42/settings/serviceaccounts/adminsdk

### Step 2: Generate New Private Key

1. Click **"Generate New Private Key"** button
2. Click **"Generate Key"** in the confirmation dialog
3. A JSON file will download (e.g., `find-any-55a42-firebase-adminsdk-xxxxx.json`)

### Step 3: Replace firebase.config.json

Replace the contents of `c:\Users\Wanga\Desktop\Mako\Work\scrape\firebase.config.json` with the downloaded file contents.

The file should look like:

```json
{
  "type": "service_account",
  "project_id": "find-any-55a42",
  "private_key_id": "abc123def456...",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqh...\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-xxxxx@find-any-55a42.iam.gserviceaccount.com",
  "client_id": "123456789012345678901",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs/firebase-adminsdk-xxxxx%40find-any-55a42.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
```

## Test the Backend

After adding credentials, restart the Flask server:

```powershell
cd c:\Users\Wanga\Desktop\Mako\Work\scrape
.\.venv\Scripts\python.exe run.py
```

You should see:
```
Firebase initialized successfully
```

## Security Note

**IMPORTANT**: Never commit `firebase.config.json` to Git!

Add to `.gitignore`:
```
firebase.config.json
```

The template `firebase.config.json.template` is safe to commit.

## Troubleshooting

### "Firebase config not found"
- Make sure file is named exactly `firebase.config.json`
- Check file is in `scrape` folder (same level as `run.py`)

### "Permission denied"
- The service account needs "Firebase Admin SDK Administrator Service Agent" role
- Go to: https://console.cloud.google.com/iam-admin/iam?project=find-any-55a42
- Find the service account email
- Ensure it has correct permissions

### "Invalid private key"
- Make sure you copied the entire JSON content
- Private key should include `-----BEGIN PRIVATE KEY-----` and `-----END PRIVATE KEY-----`
- Don't modify the `\n` characters in the private key
