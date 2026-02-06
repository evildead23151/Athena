FROM python:3.11-slim

WORKDIR /app

# Copy shared utilities first
COPY shared/common /app/shared/common

# Copy service files
COPY services/auth-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/auth-service/main.py .

# Set Python path
ENV PYTHONPATH=/app/shared:/app

EXPOSE 7001

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7001"]
