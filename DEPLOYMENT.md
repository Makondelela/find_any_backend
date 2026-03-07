# Render Deployment Guide for FindFast Job Portal

## Prerequisites
1. GitHub account
2. Render account (sign up at https://render.com)
3. Firebase service account JSON file

## Step 1: Prepare Your Repository

1. **Create a `.gitignore` file** (if not exists):
```
.venv/
__pycache__/
*.pyc
.env
firebase-service-account.json
data/user_history.json
data/user_checked.json
```

2. **Push your code to GitHub**:
```bash
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

## Step 2: Set Up Render

1. **Go to Render Dashboard**: https://dashboard.render.com/

2. **Create a New Web Service**:
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select the `find_any_backend` repository

3. **Configure the Service**:
   - **Name**: `findfast-job-portal` (or your preferred name)
   - **Region**: Choose closest to your users
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt && playwright install chromium`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
   - **Instance Type**: Free (or paid for better performance)

## Step 3: Set Environment Variables

In Render dashboard, add these environment variables:

1. **FLASK_SECRET_KEY**:
   - Generate: `python -c "import secrets; print(secrets.token_hex(32))"`
   - Copy the output and paste as value

2. **FIREBASE_DATABASE_URL**:
   - Value: `https://find-any-55a42-default-rtdb.firebaseio.com/`

3. **FIREBASE_CONFIG**:
   - Open your `firebase-service-account.json` file
   - Copy the ENTIRE JSON content (all of it, including curly braces)
   - Paste it as a single-line JSON string in the environment variable
   - Example format: `{"type":"service_account","project_id":"find-any-55a42",...}`

4. **GOOGLE_API_KEY** (if using AI features):
   - Your Google API key for Gemini
   - Value: `AIzaSy...` (your actual API key)

## Step 4: Deploy

1. Click **"Create Web Service"**
2. Render will automatically:
   - Clone your repository
   - Install dependencies
   - Install Playwright browsers
   - Start your application

3. **Monitor the deployment**:
   - Watch the logs in real-time
   - First deployment takes 5-10 minutes
   - Look for "Firebase Admin SDK initialized successfully"

## Step 5: Update Firebase Authentication

1. **Go to Firebase Console**: https://console.firebase.google.com/
2. **Select your project**: `find-any-55a42`
3. **Authentication** → **Settings** → **Authorized domains**
4. **Add your Render domain**:
   - It will be: `findfast-job-portal.onrender.com` (or your custom name)
   - Click "Add domain"

## Step 6: Update Your Frontend

If your domain changes, update the login.html:
- No changes needed! The app will work with the new domain automatically

## Step 7: Test Your Deployment

1. **Visit your app**: `https://findfast-job-portal.onrender.com`
2. **Test features**:
   - ✅ Login with email/password
   - ✅ Login with Google
   - ✅ Job listings load
   - ✅ Filters work
   - ✅ AI search works
   - ✅ View tracking saves to Firebase

## Troubleshooting

### Firebase Not Working
- Check that `FIREBASE_CONFIG` is properly formatted JSON
- Verify `FIREBASE_DATABASE_URL` is correct
- Check Render logs for initialization errors

### Build Failed
- Check `requirements.txt` has all dependencies
- Ensure Python version is compatible (3.11.0)
- Check Render build logs for specific errors

### Timeout Errors
- Free tier has 512MB RAM limit
- Consider upgrading to Starter plan if needed
- Optimize memory usage in your code

### Database Reads
- Render free tier can restart (cold starts)
- Data persists in Firebase (not local files)
- Local JSON files won't persist on Render

## Important Notes

1. **Free Tier Limitations**:
   - Service spins down after 15 minutes of inactivity
   - First request after spin-down takes 30-60 seconds
   - 512MB RAM limit
   - 400 hours/month free

2. **Data Persistence**:
   - Use Firebase for all user data (already implemented)
   - Local JSON files will be lost on restarts
   - Scraped jobs data is loaded from `data_jobs_combined.json` on startup

3. **Custom Domain** (Optional):
   - Can add custom domain in Render settings
   - Update Firebase authorized domains accordingly

## Deployment Complete! 🎉

Your FindFast job portal is now live at: `https://findfast-job-portal.onrender.com`

For updates:
```bash
git add .
git commit -m "Your update message"
git push origin main
```

Render will automatically redeploy on every push to main branch.
