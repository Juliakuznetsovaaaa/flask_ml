from flask import Flask
from flask_cors import CORS
import os
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем экземпляр Flask приложения
# Определяем базовую директорию
basedir = os.path.abspath(os.path.dirname(__file__))

# Создаем экземпляр Flask приложения
# Указываем правильные пути к шаблонам и статическим файлам
app = Flask(__name__,
            template_folder=os.path.join(basedir, '..', 'templates'),
            static_folder=os.path.join(basedir, '..', 'static'))
CORS(app)
# Конфигурация для production/development
class Config:
    ENV = os.getenv('FLASK_ENV', 'production')
    DEBUG = ENV == 'development'

app.config.from_object(Config)

# Импортируем routes после создания app чтобы избежать circular imports
from app import routes