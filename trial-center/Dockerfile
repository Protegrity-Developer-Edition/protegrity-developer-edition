FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and Streamlit config (toolbarMode=minimal hides hamburger menu)
COPY src/ src/
COPY .streamlit/ .streamlit/

# Set Python path
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Streamlit config
ENV STREAMLIT_SERVER_PORT=8502
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true

EXPOSE 8502

# Use Python (already in the image) instead of curl, which python:slim does not ship.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8502/_stcore/health',timeout=3).status==200 else 1)" || exit 1

ENTRYPOINT ["streamlit", "run", "src/trial_center/app.py"]
