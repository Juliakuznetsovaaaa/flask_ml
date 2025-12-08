from app import app
from app.routes import load_model  # ← Импортируем из routes, а не из app
import logging

# Настройка логирования для продакшена
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    logger.info("🚀 Загружаем модель и запускаем сервер...")
    load_model()  # ← Теперь эта функция доступна
    app.run(host='0.0.0.0', port=5000, debug=False)