from flask import Flask
from flask_cors import CORS
import os
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Определяем базовую директорию
basedir = os.path.abspath(os.path.dirname(__file__))

# Создаем экземпляр Flask приложения
app = Flask(__name__,
            template_folder=os.path.join(basedir, '..', 'templates'),
            static_folder=os.path.join(basedir, '..', 'static'))

# Настраиваем CORS только если не в тестовом режиме
# или если явно указано в переменных окружения
if os.getenv('FLASK_ENV') != 'test' or os.getenv('ENABLE_CORS_IN_TESTS'):
    CORS(app)
    logger.info("CORS включен")
else:
    logger.info("CORS отключен в тестовом режиме")

# Конфигурация для production/development
class Config:
    ENV = os.getenv('FLASK_ENV', 'production')
    DEBUG = os.getenv('FLASK_DEBUG', '0') == '1' or ENV == 'development'
    TESTING = ENV == 'test'
    
    # Секретный ключ
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

app.config.from_object(Config)

# Импортируем routes после создания app чтобы избежать circular imports
from app import routes

# Логируем конфигурацию
logger.info(f"Flask приложение инициализировано")
logger.info(f"  Режим: {app.config['ENV']}")
logger.info(f"  Отладка: {app.config['DEBUG']}")
logger.info(f"  Тестирование: {app.config['TESTING']}")