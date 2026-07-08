# Playwright Python image
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python requirements
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application code
COPY . .

# Run the auto_sync script on startup
CMD ["python", "auto_sync.py"]
