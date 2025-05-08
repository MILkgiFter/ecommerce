FROM python:3.11-slim

WORKDIR /app

# Копируем зависимости
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код приложения
COPY backend/ .

# Порт для Flask
EXPOSE 5000

# Запуск приложения
CMD ["python", "api.py"]
