# run.py
import os
import sys
import logging
from app import app
from app.routes import load_model

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    """Запуск приложения"""
    
    env = os.getenv('FLASK_ENV', 'development')
    
    try:
        # Загружаем модель
        logger.info("🚀 Загружаем ML модель...")
        load_model()
        logger.info("✅ Модель загружена успешно")
        
        if env == 'production':
            # Production режим - используем gunicorn
            logger.info("🚀 Запуск в production режиме")
            
            # Импортируем gunicorn только в production
            from gunicorn.app.base import BaseApplication
            
            class FlaskApplication(BaseApplication):
                def __init__(self, app, options=None):
                    self.options = options or {}
                    self.application = app
                    super().__init__()
                
                def load_config(self):
                    for key, value in self.options.items():
                        self.cfg.set(key.lower(), value)
                
                def load(self):
                    return self.application
            
            options = {
                'bind': '0.0.0.0:5000',
                'workers': 4,
                'threads': 2,
                'timeout': 120,
                'loglevel': 'info'
            }
            
            FlaskApplication(app, options).run()
        else:
            # Development режим
            logger.info("🔧 Запуск в development режиме")
            app.run(
                host='0.0.0.0',
                port=5000,
                debug=True,
                threaded=True
            )
            
    except Exception as e:
        logger.error(f"❌ Ошибка запуска приложения: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()