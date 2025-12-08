from flask import request, jsonify, render_template
# УБЕРИТЕ старые импорты tensorflow и добавьте эти:
import tensorflow as tf
import numpy as np
from PIL import Image
import io
import base64
import logging
from app import app

logger = logging.getLogger(__name__)

# Глобальная переменная для модели
model = None

def load_model():
    """Загрузка модели .h5"""
    global model
    try:
        # Используем tf.keras вместо отдельных импортов
        model = tf.keras.models.load_model(
            'app/models/classification_model.h5',
            custom_objects=None,
            compile=False
        )
        logger.info("✅ Модель загружена успешно")
       
        # Компилируем модель для предсказаний
        model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy']) 
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки модели: {e}")
        raise e

def preprocess_image(image):
    """Предобработка изображения для модели (299x299) с поддержкой TIFF"""
    try:
        logger.info(f"📥 Начало предобработки. Размер: {image.size}, режим: {image.mode}")
       
        # Всегда изменяем размер до 299x299
        image = image.resize((299, 299), Image.Resampling.LANCZOS)
        image_array = np.array(image, dtype=np.float32) / 255.0
       
        logger.info(f"📊 Размер массива после resize: {image_array.shape}")
       
        # Обработка разных форматов изображений
        if len(image_array.shape) == 2:
            # Grayscale -> RGB
            image_array = np.stack([image_array] * 3, axis=-1)
            logger.info("🔄 Конвертировано из Grayscale в RGB")
        elif image_array.shape[2] == 4:
            # RGBA -> RGB
            image_array = image_array[:, :, :3]
            logger.info("🔄 Конвертировано из RGBA в RGB")
        elif image_array.shape[2] == 1:
            # Single channel -> RGB
            image_array = np.stack([image_array.squeeze()] * 3, axis=-1)
            logger.info("🔄 Конвертировано из single channel в RGB")
       
        # Финальная проверка размера
        if image_array.shape != (299, 299, 3):
            logger.warning(f"⚠️  Неправильный размер: {image_array.shape}. Принудительно изменяем на (299, 299, 3)")
            # Создаем новое изображение с правильным размером
            temp_img = Image.fromarray((image_array * 255).astype(np.uint8))
            temp_img = temp_img.resize((299, 299), Image.Resampling.LANCZOS)
            image_array = np.array(temp_img, dtype=np.float32) / 255.0
       
        # Добавляем batch dimension
        image_array = np.expand_dims(image_array, axis=0)
       
        logger.info(f"✅ Предобработка завершена. Финальный размер: {image_array.shape}")
        return image_array
       
    except Exception as e:
        logger.error(f"❌ Ошибка в preprocess_image: {e}")
        raise e

def convert_tiff_to_jpeg(image_bytes):
    """Конвертирует TIFF в JPEG"""
    try:
        # Открываем TIFF изображение
        image = Image.open(io.BytesIO(image_bytes))
       
        # Конвертируем в RGB если нужно
        if image.mode != 'RGB':
            image = image.convert('RGB')
       
        # Конвертируем в JPEG
        jpeg_buffer = io.BytesIO()
        image.save(jpeg_buffer, format='JPEG', quality=95)
        jpeg_buffer.seek(0)
       
        logger.info("✅ TIFF успешно конвертирован в JPEG")
        return jpeg_buffer.getvalue()
   
    except Exception as e:
        logger.error(f"❌ Ошибка конвертации TIFF в JPEG: {e}")
        raise e

@app.route('/predict', methods=['POST'])
def predict():
    try:
        if model is None:
            return jsonify({'success': False, 'error': 'Модель не загружена'}), 500
           
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'success': False, 'error': 'No image data provided'}), 400
       
        logger.info("📨 Получен запрос на предсказание...")
           
        # Извлекаем base64 данные
        image_data = data['image']
        if ',' in image_data:
            image_data = image_data.split(',')[1]
       
        image_bytes = base64.b64decode(image_data)
       
        # Определяем формат по сигнатурам файлов
        is_tiff = image_bytes.startswith(b'II*\x00') or image_bytes.startswith(b'MM\x00*')
       
        if is_tiff:
            logger.info("🔍 Обнаружен TIFF формат, конвертируем в JPEG...")
            # Конвертируем TIFF в JPEG
            image_bytes = convert_tiff_to_jpeg(image_bytes)
            file_format = 'TIFF (converted to JPEG)'
        else:
            file_format = 'JPEG/PNG'
       
        # Открываем изображение с помощью PIL
        image = Image.open(io.BytesIO(image_bytes))
       
        logger.info(f"📐 Исходный размер: {image.size}, режим: {image.mode}, формат: {file_format}")
       
        # Конвертируем в RGB если нужно
        if image.mode != 'RGB':
            original_mode = image.mode
            image = image.convert('RGB')
            logger.info(f"🔄 Конвертирован из {original_mode} в RGB")
       
        # Предобработка для модели
        processed_image = preprocess_image(image)
       
        logger.info(f"🔮 Выполняем предсказание...")
       
        # Предсказание
        prediction = model.predict(processed_image, verbose=0)
        results = prediction.tolist()[0]
       
        logger.info(f"✅ Предсказание завершено. Результаты: {results}")
       
        # Конвертируем оригинальное изображение в base64 для отображения
        buffered_original = io.BytesIO()
        image.save(buffered_original, format='JPEG', quality=95)
        original_base64 = base64.b64encode(buffered_original.getvalue()).decode('utf-8')
        original_image_data = f"data:image/jpeg;base64,{original_base64}"
       
        response_data = {
            'success': True,
            'predictions': results,
            'processed_shape': processed_image.shape,
            'original_image': original_image_data
        }
       
        return jsonify(response_data)
       
    except Exception as e:
        logger.error(f"❌ Error in prediction: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health')
def health():
    """Проверка статуса API"""
    model_info = {}
    if model is not None:
        try:
            # Получаем информацию о входных данных модели
            if hasattr(model, 'input_shape'):
                model_info['input_shape'] = model.input_shape
            if hasattr(model, 'layers'):
                model_info['layers'] = len(model.layers)
        except Exception as e:
            model_info['error'] = str(e)
   
    return jsonify({
        'status': 'healthy',
        'model_loaded': model is not None,
        'model_info': model_info
    })