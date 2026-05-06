FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

COPY services/dispatcher/requirements.txt /app/services/dispatcher/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/services/dispatcher/requirements.txt

COPY services/dispatcher/ /app/services/dispatcher/
COPY services/ai_worker/schemas.py /app/services/ai_worker/schemas.py

CMD ["python", "-m", "services.dispatcher.main"]

