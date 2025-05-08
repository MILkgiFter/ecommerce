FROM python:3.11-slim

WORKDIR /app

# Копируем зависимости
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY backend/ .

# Порт для приложения Flask
EXPOSE 5000

# Запускаем приложение
CMD ["python", "api.py"]