# AWS EC2 Deployment Guide for FindFast Job Portal

## Overview
This guide covers deploying the FindFast backend to AWS EC2 with Firebase for data storage.

## Prerequisites
- AWS Account
- Firebase project already set up (see FIREBASE_SETUP.md)
- Domain name (optional, for SSL)

## Step 1: Launch EC2 Instance

### 1.1 Create EC2 Instance
1. Go to AWS Console → EC2 → Launch Instance
2. **Name**: `findfast-backend`
3. **OS**: Ubuntu Server 22.04 LTS (64-bit x86)
4. **Instance Type**: `t3.medium` (2 vCPU, 4 GB RAM) - minimum for Playwright/Chromium
5. **Key Pair**: Create new or select existing (download `.pem` file)
6. **Network Settings**:
   - Create new Security Group: `findfast-sg`
   - Allow SSH (port 22) from your IP
   - Allow HTTP (port 80) from anywhere
   - Allow HTTPS (port 443) from anywhere
   - Allow Custom TCP (port 5000) from anywhere (for testing)
7. **Storage**: 30 GB gp3

### 1.2 Elastic IP (Recommended)
1. Allocate Elastic IP in EC2 → Elastic IPs
2. Associate with your instance
3. Use this IP for DNS A record

## Step 2: Configure Security Group
Add these inbound rules to `findfast-sg`:
| Type | Protocol | Port | Source | Description |
|------|----------|------|--------|-------------|
| SSH | TCP | 22 | Your IP | SSH access |
| HTTP | TCP | 80 | 0.0.0.0/0 | Web traffic |
| HTTPS | TCP | 443 | 0.0.0.0/0 | Secure web traffic |
| Custom TCP | TCP | 5000 | 0.0.0.0/0 | Direct Flask access (dev only) |

## Step 3: Connect and Setup Server

```bash
# Connect via SSH
ssh -i your-key.pem ubuntu@<EC2_PUBLIC_IP>

# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv nginx git \
    chromium-browser chromium-chromedriver \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2

# Install Node.js (for Firebase CLI if needed)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

## Step 4: Deploy Application

```bash
# Clone repository
cd /home/ubuntu
git clone https://github.com/yourusername/find_any_backend.git
cd find_any_backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
playwright install-deps chromium

# Create .env file with your credentials
cat > .env << 'EOF'
FLASK_SECRET_KEY=your-super-secret-key-here-generate-with-python-secrets
FIREBASE_DATABASE_URL=https://your-project.firebaseio.com/
FIREBASE_CONFIG={"type":"service_account","project_id":"your-project",...}
GOOGLE_API_KEY=your-google-api-key
FIREBASE_API_KEY=your-firebase-api-key
FIREBASE_MESSAGING_SENDER_ID=your-sender-id
FIREBASE_APP_ID=your-app-id
ADMIN_EMAIL=your-admin@email.com
SCRAPE_API_KEY=your-random-api-key-for-remote-trigger
PROFILE_ENCRYPTION_KEY=your-32-byte-hex-key
EOF

# Test the application
python app.py
# Should start on port 5000
```

## Step 5: Configure Systemd Service

```bash
# Create systemd service file
sudo tee /etc/systemd/system/findfast.service > /dev/null << 'EOF'
[Unit]
Description=FindFast Flask Application
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/find_any_backend
Environment=PATH=/home/ubuntu/find_any_backend/venv/bin
ExecStart=/home/ubuntu/find_any_backend/venv/bin/gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 2 \
    --timeout 120 \
    --access-logfile /var/log/findfast/access.log \
    --error-logfile /var/log/findfast/error.log \
    app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Create log directory
sudo mkdir -p /var/log/findfast
sudo chown ubuntu:ubuntu /var/log/findfast

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable findfast
sudo systemctl start findfast
sudo systemctl status findfast
```

## Step 6: Configure Nginx Reverse Proxy

```bash
# Create Nginx config
sudo tee /etc/nginx/sites-available/findfast > /dev/null << 'EOF'
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;  # Or EC2 public IP

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }

    # Static files
    location /static {
        alias /home/ubuntu/find_any_backend/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Health check
    location /health {
        proxy_pass http://127.0.0.1:5000/api/stats;
        access_log off;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/findfast /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

## Step 7: SSL with Let's Encrypt (Optional but Recommended)

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Auto-renewal test
sudo certbot renew --dry-run
```

## Step 8: Configure Firebase Authorized Domains

1. Go to Firebase Console → Authentication → Settings → Authorized domains
2. Add:
   - `your-domain.com`
   - `your-ec2-public-ip` (if no domain yet)
   - `localhost` (for local development)

## Step 9: Set Up Remote Scraping Trigger

### 9.1 Generate API Key
```bash
# On your local machine
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Copy output to SCRAPE_API_KEY in .env
```

### 9.2 Trigger from Phone (Using Shortcuts/HTTP Request)
Create an HTTP request shortcut on your phone:

**iOS Shortcuts:**
1. Open Shortcuts app → Create Shortcut
2. Add "Get Contents of URL" action
3. URL: `https://your-domain.com/api/scrape/trigger`
4. Method: POST
5. Headers: `X-API-Key` = `your-scrape-api-key`
6. Request Body: JSON `{"search_terms": "data engineer, python developer"}`
7. Save and add to Home Screen

**Android (Tasker/HTTP Request Shortcuts):**
Similar approach with HTTP POST action.

### 9.3 Using curl (for testing)
```bash
curl -X POST https://your-domain.com/api/scrape/trigger \
  -H "X-API-Key: your-scrape-api-key" \
  -H "Content-Type: application/json" \
  -d '{"search_terms": "data engineer, data analyst"}'
```

## Step 10: Monitoring and Maintenance

### 10.1 Check Logs
```bash
# Application logs
sudo journalctl -u findfast -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# App-specific logs
tail -f /var/log/findfast/error.log
```

### 10.2 Auto-restart on Failure
The systemd service is configured with `Restart=always`. For extra reliability:

```bash
# Create a health check cron
crontab -e
# Add:
*/5 * * * * /home/ubuntu/find_any_backend/venv/bin/python -c "
import requests
try:
    r = requests.get('http://localhost:5000/api/stats', timeout=10)
    if r.status_code != 200:
        print('Health check failed')
except:
    print('Health check error')
" >> /home/ubuntu/health_check.log 2>&1
```

### 10.3 Scheduled Scraping (Optional)
```bash
# Add to crontab for daily scraping at 2 AM
crontab -e
# Add:
0 2 * * * /home/ubuntu/find_any_backend/venv/bin/python /home/ubuntu/find_any_backend/combine_jobs.py >> /home/ubuntu/scrape_cron.log 2>&1
```

## Step 11: Cost Optimization

| Instance Type | Monthly Cost (On-Demand) | Notes |
|---------------|------------------------|-------|
| t3.medium | ~$30/month | Good for production |
| t3.small | ~$15/month | Minimum for Playwright |
| t3.micro | ~$7/month | Too small for scraping |

**Savings Options:**
- Reserved Instances (1yr): ~30-40% off
- Spot Instances: ~70% off (but can be interrupted)
- Savings Plans: Flexible commitment

## Troubleshooting

### Playwright/Chromium Issues
```bash
# Reinstall Playwright dependencies
playwright install-deps chromium
playwright install chromium

# Test manually
python -c "from playwright.sync_api import sync_playwright; p = sync_playwright().start(); b = p.chromium.launch(); print('OK'); b.close(); p.stop()"
```

### Memory Issues
If OOM killer stops the process:
```bash
# Add swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Firebase Connection Issues
- Verify `FIREBASE_DATABASE_URL` format: `https://project-id.firebaseio.com/`
- Check service account permissions in Firebase Console
- Ensure Realtime Database is enabled (not Firestore only)

## Backup Strategy

1. **Firebase**: Automatic backups via Firebase Console → Realtime Database → Backups
2. **Code**: Git repository
3. **Config**: Store `.env` in AWS Secrets Manager or Parameter Store
4. **Logs**: CloudWatch Logs (optional integration)

## Updates Deployment

```bash
cd /home/ubuntu/find_any_backend
git pull
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
sudo systemctl restart findfast
sudo systemctl reload nginx
```

## Quick Commands Reference

```bash
# Service management
sudo systemctl status findfast
sudo systemctl restart findfast
sudo systemctl stop findfast
sudo systemctl start findfast

# Nginx
sudo nginx -t
sudo systemctl reload nginx

# Logs
sudo journalctl -u findfast -f --since "1 hour ago"

# Manual scrape
cd /home/ubuntu/find_any_backend && source venv/bin/activate && python combine_jobs.py

# Check disk space
df -h

# Check memory
free -h
```