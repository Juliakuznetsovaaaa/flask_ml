# tests/image_processing/test_image_preprocessing_no_tf.py
import unittest
import io
import base64
import numpy as np
from PIL import Image

# Копия функции preprocess_image из app/routes.py (без TensorFlow)
def preprocess_image(image):
    """Предобработка изображения для модели (299x299)"""
    try:
        # Всегда изменяем размер до 299x299
        image = image.resize((299, 299), Image.Resampling.LANCZOS)
        image_array = np.array(image, dtype=np.float32) / 255.0
        
        # Обработка разных форматов изображений
        if len(image_array.shape) == 2:
            # Grayscale -> RGB
            image_array = np.stack([image_array] * 3, axis=-1)
        elif image_array.shape[2] == 4:
            # RGBA -> RGB
            image_array = image_array[:, :, :3]
        elif image_array.shape[2] == 1:
            # Single channel -> RGB
            image_array = np.stack([image_array.squeeze()] * 3, axis=-1)
        
        # Финальная проверка размера
        if image_array.shape != (299, 299, 3):
            # Создаем новое изображение с правильным размером
            temp_img = Image.fromarray((image_array * 255).astype(np.uint8))
            temp_img = temp_img.resize((299, 299), Image.Resampling.LANCZOS)
            image_array = np.array(temp_img, dtype=np.float32) / 255.0
        
        # Добавляем batch dimension
        image_array = np.expand_dims(image_array, axis=0)
        
        return image_array
    except Exception as e:
        raise e

# Копия функции convert_tiff_to_jpeg из app/routes.py
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
        
        return jpeg_buffer.getvalue()
    except Exception as e:
        raise e

class TestImageProcessingNoTF(unittest.TestCase):
    """Тесты обработки изображений без зависимости от TensorFlow"""
    
    def setUp(self):
        # Создаем тестовые изображения разных форматов
        self.rgb_image = Image.new('RGB', (400, 300), color='red')
        self.grayscale_image = Image.new('L', (350, 250), color=128)
        self.rgba_image = Image.new('RGBA', (300, 200), color=(255, 0, 0, 128))
    
    def test_preprocess_image_rgb(self):
        """Тест предобработки RGB изображения"""
        processed = preprocess_image(self.rgb_image)
        
        # Проверяем размеры
        self.assertEqual(processed.shape, (1, 299, 299, 3))
        
        # Проверяем нормализацию
        self.assertTrue(processed.min() >= 0)
        self.assertTrue(processed.max() <= 1)
        
        # Проверяем тип данных
        self.assertEqual(processed.dtype, np.float32)
    
    def test_preprocess_image_grayscale(self):
        """Тест предобработки Grayscale изображения"""
        processed = preprocess_image(self.grayscale_image)
        
        # Должно быть конвертировано в RGB
        self.assertEqual(processed.shape, (1, 299, 299, 3))
    
    def test_preprocess_image_rgba(self):
        """Тест предобработки RGBA изображения"""
        processed = preprocess_image(self.rgba_image)
        
        # Должно быть конвертировано в RGB (без альфа-канала)
        self.assertEqual(processed.shape, (1, 299, 299, 3))
    
    def test_preprocess_image_different_sizes(self):
        """Тест предобработки изображений разных размеров"""
        test_sizes = [(100, 100), (800, 600), (299, 299), (500, 300)]
        
        for size in test_sizes:
            with self.subTest(size=size):
                img = Image.new('RGB', size, color='green')
                processed = preprocess_image(img)
                
                self.assertEqual(processed.shape, (1, 299, 299, 3))
    
    def test_tiff_conversion(self):
        """Тест конвертации TIFF в JPEG"""
        # Создаем TIFF изображение
        tiff_buffer = io.BytesIO()
        self.rgb_image.save(tiff_buffer, format='TIFF', compression='tiff_lzw')
        tiff_bytes = tiff_buffer.getvalue()
        
        # Конвертируем
        jpeg_bytes = convert_tiff_to_jpeg(tiff_bytes)
        
        # Проверяем, что результат не пустой
        self.assertGreater(len(jpeg_bytes), 0)
        
        # Проверяем, что это валидный JPEG
        jpeg_image = Image.open(io.BytesIO(jpeg_bytes))
        self.assertEqual(jpeg_image.format, 'JPEG')
        self.assertEqual(jpeg_image.mode, 'RGB')
    
    def test_tiff_conversion_grayscale(self):
        """Тест конвертации Grayscale TIFF"""
        # Создаем Grayscale TIFF
        tiff_buffer = io.BytesIO()
        self.grayscale_image.save(tiff_buffer, format='TIFF')
        tiff_bytes = tiff_buffer.getvalue()
        
        # Конвертируем
        jpeg_bytes = convert_tiff_to_jpeg(tiff_bytes)
        
        # Проверяем результат
        jpeg_image = Image.open(io.BytesIO(jpeg_bytes))
        self.assertEqual(jpeg_image.mode, 'RGB')  # Должно быть конвертировано в RGB
    
    def test_image_base64_encoding(self):
        """Тест кодирования/декодирования base64"""
        # Создаем изображение
        img_buffer = io.BytesIO()
        self.rgb_image.save(img_buffer, format='JPEG')
        img_bytes = img_buffer.getvalue()
        
        # Кодируем в base64
        encoded = base64.b64encode(img_bytes).decode()
        
        # Декодируем обратно
        decoded = base64.b64decode(encoded)
        
        # Проверяем, что данные совпадают
        self.assertEqual(img_bytes, decoded)
        
        # Проверяем, что можно создать изображение из декодированных данных
        decoded_image = Image.open(io.BytesIO(decoded))
        self.assertEqual(decoded_image.size, self.rgb_image.size)

if __name__ == '__main__':
    unittest.main()