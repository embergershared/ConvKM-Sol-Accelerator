FROM python:3.11-alpine

# Install system dependencies required for building and running the application
RUN apk add --no-cache --virtual .build-deps \
    build-base \
    libffi-dev \
    openssl-dev \
    curl \
    unixodbc-dev \
    libpq \
    opus-dev \
    libvpx-dev

# Download and install Microsoft ODBC Driver 18 and MSSQL tools (latest release)
RUN curl -O https://download.microsoft.com/download/fae28b9a-d880-42fd-9b98-d779f0fdd77f/msodbcsql18_18.5.1.1-1_amd64.apk \
    && curl -O https://download.microsoft.com/download/7/6/d/76de322a-d860-4894-9945-f0cc5d6a45f8/mssql-tools18_18.4.1.1-1_amd64.apk \
    && apk add --allow-untrusted msodbcsql18_18.5.1.1-1_amd64.apk \
    && apk add --allow-untrusted mssql-tools18_18.4.1.1-1_amd64.apk \
    && rm msodbcsql18_18.5.1.1-1_amd64.apk mssql-tools18_18.4.1.1-1_amd64.apk

# Set the working directory inside the container
WORKDIR /app

# Make Python logging visible immediately in Azure Log stream.
#   PYTHONUNBUFFERED   — flush stdout/stderr line-by-line, no buffering.
#   PYTHONFAULTHANDLER — dump a Python traceback on segfault / fatal signal.
#   PYTHONDONTWRITEBYTECODE — keep the image smaller / read-only friendly.
ENV PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy only the requirements file first to leverage Docker layer caching
COPY ./requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    rm -rf /root/.cache

# Copy the backend application code into the container
COPY ./ .

# Expose port 80 for incoming traffic
EXPOSE 80

# Start the application using Uvicorn.
#   --log-level info          — match the app's default log level.
#   --access-log              — emit one log line per request (visible in Log stream).
#   --proxy-headers           — honor X-Forwarded-* from the App Service front-end.
#   --forwarded-allow-ips=*   — trust those headers from any upstream (App Service).
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "80", "--log-level", "info", "--access-log", "--proxy-headers", "--forwarded-allow-ips", "*"]