FROM python:3.9-slim

WORKDIR /app

# Установка системных зависимостей для Debian 12
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Копирование зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование приложения
COPY . .

# Порт
EXPOSE 5000

# Запуск приложения
CMD ["python", "run.py"]