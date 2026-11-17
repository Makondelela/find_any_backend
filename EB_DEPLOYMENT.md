# Elastic Beanstalk Deployment Guide for FindFast

## Overview
This guide covers deploying the FindFast Flask app to your existing Elastic Beanstalk environment (`findfast-env`).

## Architecture
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   GitHub        │────▶│  Elastic         │────▶│  Firebase       │
│   Actions       │     │  Beanstalk       │     │  Realtime DB    │
│   (CI/CD)       │     │  (findfast-env)  │     │  (Jobs, Users)  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │  GitHub Actions  │
                       │  (Scheduled      │
                       │   Scraping)      │
                       └──────────────────┘
```

**Key Points:**
- **Elastic Beanstalk** runs the Flask web app only (no Playwright/Chromium)
- **GitHub Actions** runs scrapers daily (has full Playwright support)
- **Firebase** stores all persistent data (jobs, user profiles, history)
- Scraped jobs are committed back to the repo and deployed automatically

## Prerequisites

### 1. AWS Setup (Already Done ✓)
- Elastic Beanstalk Application: `findfast`
- Environment: `findfast-env` (Python 3.11 on Amazon Linux 2023)
- Domain: `findfast.eu-north-1.elasticbeanstalk.com`

### 2. GitHub Repository Secrets
Go to **Settings → Secrets and variables → Actions → New repository secret**:

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `AWS_ACCESS_KEY_ID` | `AKIA...` | IAM user with ElasticBeanstalkFullAccess |
| `AWS_SECRET_ACCESS_KEY` | `...` | Secret key for above IAM user |
| `FIREBASE_DATABASE_URL` | `https://find-any-55a42-default-rtdb.firebaseio.com/` | Your Firebase RTDB URL |
| `FIREBASE_CONFIG` | `{"type":"service_account",...}` | Full service account JSON (one line) |
| `GOOGLE_API_KEY` | `AIzaSy...` | Google Gemini API key |
| `FLASK_SECRET_KEY | `...` | Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `FIREBASE_API_KEY` | `AIzaSy...` | Firebase Web API key |
| `FIREBASE_MESSAGING_SENDER_ID` | `756935502893` | From Firebase Console |
| `FIREBASE_APP_ID` | `1:756935502893:web:...` | From Firebase Console |
| `ADMIN_EMAIL` | `makondelelamaps@gmail.com` | Admin email for access control |
| `SCRAPE_API_KEY` | `...` | Generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `PROFILE_ENCRYPTION_KEY` | `...` | Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |

### 3. IAM User Permissions
Create IAM user with these policies:
- `AWSElasticBeanstalkFullAccess`
- `AmazonS3FullAccess` (for EB version storage)
- `CloudWatchLogsFullAccess` (for logs)

## Deployment Steps

### 1. Push to Main Branch
```bash
git add .
git commit -m "Configure Elastic Beanstalk deployment"
git push origin main
```

### 2. Watch GitHub Actions
1. Go to **Actions** tab in GitHub
2. Watch "Deploy FindFast to Elastic Beanstalk" workflow
3. First deploy takes ~5-10 minutes

### 3. Verify Deployment
```bash
# Check health endpoint
curl https://findfast.eu-north-1.elasticbeanstalk.com/api/stats

# Should return JSON with job statistics
```

## Post-Deployment Configuration

### 1. Update Firebase Authorized Domains
1. Firebase Console → Authentication → Settings → Authorized domains
2. Add: `findfast.eu-north-1.elasticbeanstalk.com`

### 2. Set Environment Variables in EB Console (Alternative to GitHub Secrets)
If you prefer setting vars in EB Console instead of GitHub:
1. EB Console → Environments → findfast-env → Configuration
2. Software → Edit → Environment properties
3. Add all variables from the secrets table above

### 3. Configure Custom Domain (Optional)
1. EB Console → Configuration → Load balancer → Edit
2. Add HTTPS listener with ACM certificate
3. Update Route 53 / DNS with CNAME to EB domain

## Running Scrapers

### Automatic (Daily at 2 AM UTC)
The `scrape.yml` workflow runs automatically. It:
1. Runs all scrapers on GitHub Actions (with Playwright support)
2. Combines results via `combine_jobs.py`
3. Commits updated `data/` files to repo
4. Triggers a new EB deployment automatically

### Manual Trigger
1. Go to **Actions → Scrape Jobs → Run workflow**
2. Optionally customize search terms
3. Click **Run workflow**

### Local Development
```bash
# Install dev dependencies
pip install -r requirements-dev.txt
playwright install chromium

# Run scrapers locally
python backend/main.py --search "data engineer, python developer"

# Combine and sync to Firebase
python combine_jobs.py
```

## Monitoring

### Health Checks
- **EB Health**: EB Console → Environment health
- **App Health**: `curl https://your-domain.com/api/stats`
- **Logs**: EB Console → Logs → Request last 100 lines

### CloudWatch Alarms (Recommended)
```bash
# CPU Alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "findfast-high-cpu" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions arn:aws:sns:eu-north-1:ACCOUNT:topic

# Request Latency
aws cloudwatch put-metric-alarm \
  --alarm-name "findfast-high-latency" \
  --metric-name Latency \
  --namespace AWS/ApplicationELB \
  --statistic Average \
  --period 60 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 3
```

## Troubleshooting

### Deployment Fails
```bash
# Check EB events
aws elasticbeanstalk describe-events --environment-name findfast-env

# Check logs
aws elasticbeanstalk request-environment-info --environment-name findfast-env --info-type tail
aws elasticbeanstalk retrieve-environment-info --environment-name findfast-env --info-type tail
```

### App Won't Start
1. Check `runtime.txt` has correct Python version
2. Check `Procfile` has correct gunicorn command
3. Check `.ebextensions/01_python.config` WSGIPath
4. Verify all dependencies in `requirements.txt`

### Firebase Connection Issues
- Verify `FIREBASE_DATABASE_URL` format: `https://project.firebaseio.com/`
- Check `FIREBASE_CONFIG` is valid JSON (escape quotes properly)
- Ensure service account has `Firebase Realtime Database Admin` role

### Scraping Fails on GitHub Actions
- Check Playwright installation in workflow logs
- Verify search terms don't contain special characters
- Some sites may block GitHub Actions IPs (use delays)

### Static Files Not Loading
- Check `.ebextensions/02_nginx.config` static file mapping
- Verify `templates/` and `static/` folders are in deployment package
- Check browser dev tools for 404 errors

## Cost Estimation

| Component | Monthly Cost (eu-north-1) |
|-----------|--------------------------|
| EB Environment (t3.medium, 1 instance) | ~$30 |
| EB Environment (t3.medium, 2 instances for HA) | ~$60 |
| Data Transfer (first 1GB free) | ~$0.09/GB |
| CloudWatch Logs | ~$0.50/GB |
| GitHub Actions (2000 min/mo free) | Free for most usage |
| **Total (single instance)** | **~$31/month** |
| **Total (HA, 2 instances)** | **~$61/month** |

## Scaling

### Auto Scaling (Already Configured)
```yaml
# In .ebextensions/01_python.config
aws:autoscaling:trigger:
  MeasureName: CPUUtilization
  UpperThreshold: 70
  LowerThreshold: 30
```

### Manual Scaling
```bash
# Scale to 3 instances
aws elasticbeanstalk update-environment \
  --environment-name findfast-env \
  --option-settings Namespace=aws:autoscaling:asg,OptionName=MinSize,Value=3 \
  Namespace=aws:autoscaling:asg,OptionName=MaxSize,Value=3
```

## Security Checklist

- [ ] All secrets in GitHub Secrets (not in code)
- [ ] Firebase service account has minimal permissions
- [ ] HTTPS enforced (configure ALB listener)
- [ ] Security groups restrict SSH to your IP only
- [ ] `FLASK_SECRET_KEY` is strong and unique
- [ ] `SCRAPE_API_KEY` is used for remote scraping
- [ ] Firebase Auth domains configured
- [ ] Regular dependency updates (`pip-audit`)

## Quick Commands

```bash
# Deploy manually
git push origin main

# Check deployment status
aws elasticbeanstalk describe-environments --environment-names findfast-env

# View logs
aws elasticbeanstalk request-environment-info --environment-name findfast-env --info-type tail
aws elasticbeanstalk retrieve-environment-info --environment-name findfast-env --info-type tail

# Restart app servers
aws elasticbeanstalk restart-app-server --environment-name findfast-env

# Trigger scraping manually
gh workflow run scrape.yml -f search_terms="data engineer, python"

# Check current EB version
aws elasticbeanstalk describe-environments --environment-names findfast-env --query 'Environments[0].VersionLabel'
```