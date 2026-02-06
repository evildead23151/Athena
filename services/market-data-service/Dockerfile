FROM python:3.11-slim

WORKDIR /app

COPY shared/common /app/shared/common
COPY services/market-data-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/market-data-service/main.py .

ENV PYTHONPATH=/app/shared:/app

EXPOSE 7002

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7002"]
