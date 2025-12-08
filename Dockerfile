# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Установка минимальных системных зависимостей
# Для Ubuntu 22.04/Debian совместимые пакеты
RUN apt-get update && apt-get install -y --no-install-recommends \
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

# Создание необходимых директорий
RUN mkdir -p app/models static templates

# Настройка пользователя для безопасности
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Порт
EXPOSE 5000

# Команда запуска с gunicorn для production
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--threads", "2", "run:app"]