# gunicorn_config.py
import multiprocessing
import os

# Базовые настройки
bind = "0.0.0.0:5000"
workers = multiprocessing.cpu_count() * 2 + 1
threads = 2
timeout = 120
keepalive = 5

# Логирование
accesslog = "-"  # stdout
errorlog = "-"   # stdout
loglevel = os.getenv("LOG_LEVEL", "info")

# Производительность
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Безопасность
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# Переменные окружения
raw_env = [
    "FLASK_ENV=production",
    "PYTHONUNBUFFERED=1",
]

def when_ready(server):
    server.log.info("Gunicorn готов к обработке запросов")

def worker_int(worker):
    worker.log.info("Worker получил сигнал прерывания")

def worker_abort(worker):
    worker.log.info("Worker получил сигнал аварийного завершения")