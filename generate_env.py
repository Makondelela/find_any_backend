"""
Generate .env file for Render deployment from firebase-service-account.json
"""
import json
import secrets

# Read Firebase service account
with open('firebase-service-account.json', 'r') as f:
    firebase_config = json.load(f)

# Convert to single-line JSON string
firebase_config_str = json.dumps(firebase_config)

# Generate Flask secret key
flask_secret = secrets.token_hex(32)

# Create .env content
env_content = f"""# Flask Configuration
FLASK_SECRET_KEY={flask_secret}

# Firebase Configuration
FIREBASE_DATABASE_URL=https://find-any-55a42-default-rtdb.firebaseio.com/
FIREBASE_CONFIG={firebase_config_str}

# Google API Key (for AI features - optional)
GOOGLE_API_KEY=your-google-api-key-here
"""

# Write to .env file
with open('.env', 'w') as f:
    f.write(env_content)

print("✅ .env file created successfully!")
print("\nYou can now:")
print("1. Upload this .env file to Render using 'Add from .env' option")
print("2. Or copy the contents and paste them in Render's environment variables")
print("\nNote: Don't forget to update GOOGLE_API_KEY if you're using AI features")
