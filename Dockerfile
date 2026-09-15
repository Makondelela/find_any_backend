# Playwright's official image already ships Chromium and every OS-level
# dependency it needs, so no `playwright install` step is required at build
# time. Keep this tag in sync with the playwright version in requirements.txt.
FROM mcr.microsoft.com/playwright/python:v1.58.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120"]
