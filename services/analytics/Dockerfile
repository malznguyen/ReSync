FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

COPY services/analytics/requirements.txt /app/services/analytics/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/services/analytics/requirements.txt

COPY services/analytics/ /app/services/analytics/
COPY services/ai_worker/schemas.py /app/services/ai_worker/schemas.py

CMD ["python", "-m", "services.analytics.main"]
