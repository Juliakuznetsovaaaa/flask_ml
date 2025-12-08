import unittest
import sys
import os
import io
import base64
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from PIL import Image
import numpy as np

# Импортируем функции из routes
try:
    from app.routes import preprocess_image, convert_tiff_to_jpeg
    HAS_PROCESSING_FUNCTIONS = True
except ImportError:
    HAS_PROCESSING_FUNCTIONS = False
    print("⚠️  Функции обработки изображений не найдены")

@unittest.skipIf(not HAS_PROCESSING_FUNCTIONS, "Функции обработки изображений не найдены")
class TestImageProcessing(unittest.TestCase):
    """Тесты предобработки изображений"""
    
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
        
        # Проверяем, что все каналы одинаковы (grayscale -> RGB)
        # Допускаем небольшую погрешность из-за интерполяции
        channel_diff = np.abs(processed[0, :, :, 0] - processed[0, :, :, 1]).max()
        self.assertTrue(channel_diff < 0.1)
    
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
    
    def test_preprocess_validation(self):
        """Тест валидации входных данных"""
        # Неправильный тип данных
        with self.assertRaises(Exception):
            preprocess_image("not an image")
        
        # None значение
        with self.assertRaises(Exception):
            preprocess_image(None)

if __name__ == '__main__':
    unittest.main()