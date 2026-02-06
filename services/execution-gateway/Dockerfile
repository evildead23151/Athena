FROM python:3.11-slim

WORKDIR /app

COPY shared/common /app/shared/common
COPY services/execution-gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/execution-gateway/main.py .

ENV PYTHONPATH=/app/shared:/app

EXPOSE 7005

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7005"]
