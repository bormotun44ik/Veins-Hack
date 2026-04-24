FROM python:3.11-slim

WORKDIR /app

# Deps first — слой кэшируется пока requirements.txt не поменялся
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# SQLite лежит в volume /app/db, создаётся init_db() при старте
RUN mkdir -p /app/db

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
