# Deployment Instructions for Render

## Prerequisites
1. Create a Render account at https://render.com
2. Have your Firebase service account credentials ready
3. Your code pushed to a Git repository (GitHub, GitLab, or Bitbucket)

## Deployment Steps

### 1. Create a New Web Service on Render

1. Go to your Render dashboard
2. Click "New +" button and select "Web Service"
3. Connect your Git repository
4. Select the `scrape` folder/repo

### 2. Configure Build Settings

- **Name**: `findfast-backend` (or your preferred name)
- **Environment**: `Python 3`
- **Build Command**:  
  ```bash
  pip install -r requirements.txt && playwright install chromium
  ```
- **Start Command**:  
  ```bash
  gunicorn run:app --bind 0.0.0.0:$PORT
  ```

### 3. Set Environment Variables

In Render dashboard, go to Environment tab and add:

```
FIREBASE_DATABASE_URL=https://find-any-55a42-default-rtdb.firebaseio.com
FLASK_ENV=production
PORT=5000
CORS_ORIGINS=https://your-frontend-domain.com
```

### 4. Add Firebase Credentials

Since `firebase.config.json` contains sensitive data:

**Option A: Use Render's Secret Files**
1. Go to "Secret Files" tab in Render dashboard
2. Add new secret file:
   - **Filename**: `firebase.config.json`
   - **Contents**: Paste your entire firebase.config.json content

**Option B: Use Environment Variable**
1. Convert firebase.config.json to base64
2. Add environment variable `FIREBASE_CREDENTIALS_BASE64`
3. Update `backend/services/firebase_service.py` to decode it

### 5. Deploy

Click "Create Web Service" - Render will:
1. Clone your repository
2. Install dependencies
3. Install Playwright browsers
4. Start the Gunicorn server

### 6. Update Frontend CORS

Once deployed, update your Angular app's environment files with the Render backend URL:

```typescript
export const environment = {
  production: true,
  apiUrl: 'https://findfast-backend.onrender.com'
};
```

## Important Notes

- Free tier services sleep after 15 minutes of inactivity
- First request after sleep may take 30-60 seconds
- Consider upgrading to paid tier for production use
- Set up health check endpoint at `/health` for better uptime

## Troubleshooting

If deployment fails:
1. Check build logs in Render dashboard
2. Verify all environment variables are set
3. Ensure firebase.config.json is correctly configured
4. Check that requirements.txt includes all dependencies

## Production Checklist

- [ ] Firebase credentials configured
- [ ] CORS origins updated for production domain
- [ ] Environment variables set
- [ ] Frontend updated with production API URL
- [ ] Health check endpoint configured
- [ ] Error monitoring set up (optional: Sentry)
