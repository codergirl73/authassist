FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DEMO_MODE=true \
    APP_ENV=demo \
    CACHE_DIR=.cache \
    PORT=8000

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN useradd --create-home app && mkdir -p .cache && chown -R app /app
USER app

EXPOSE 8000
# Default: the web app (landing, sign-in, workspace) served by FastAPI. For the Streamlit UI instead:
#   docker run -p 8501:8501 -e PORT=8501 authassist streamlit run ui/app.py --server.address=0.0.0.0 --server.port=8501 --server.headless=true
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT}"]
