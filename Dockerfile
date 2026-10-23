FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEMO_MODE=true \
    APP_ENV=demo \
    CACHE_DIR=.cache \
    PORT=8501

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN useradd --create-home app && mkdir -p .cache && chown -R app /app
USER app

EXPOSE 8501
# Default: Streamlit UI. For the API instead:
#   docker run -p 8000:8000 -e PORT=8000 authassist uvicorn api.main:app --host 0.0.0.0 --port 8000
CMD ["sh", "-c", "streamlit run ui/app.py --server.address=0.0.0.0 --server.port=${PORT} --server.headless=true --browser.gatherUsageStats=false"]
