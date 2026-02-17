FROM python:3.12-slim

# System deps for camoufox (Firefox)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgtk-3-0 libdbus-glib-1-2 libxt6 libx11-xcb1 \
    libasound2 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libxkbcommon0 libpango-1.0-0 libatk1.0-0 \
    libcairo2 libgdk-pixbuf-2.0-0 fonts-liberation \
    xvfb && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Install the package
RUN pip install --no-cache-dir -e .

# Pre-download camoufox browser
RUN python3 -c "from camoufox.utils import install; install()"

EXPOSE 8888

# Start with Xvfb for headless display
CMD ["sh", "-c", "Xvfb :99 -screen 0 1920x1080x24 & export DISPLAY=:99 && agentic-browser --port 8888"]
