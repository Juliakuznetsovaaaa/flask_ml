import unittest
import sys
import os
import json
import io
import base64
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from unittest.mock import Mock, patch, MagicMock
from PIL import Image
import numpy as np
from app import app

class TestMockMLComponents(unittest.TestCase):
    """Mock тесты для изоляции ML компонентов"""
    
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        
        # Создаем тестовое изображение
        self.test_image = Image.new('RGB', (300, 300), color='red')
        buffered = io.BytesIO()
        self.test_image.save(buffered, format='JPEG')
        self.image_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    @patch('app.routes.model')
    def test_predict_with_mock_model(self, mock_model):
        """Тест /predict endpoint с mock моделью"""
        # Настраиваем mock модель
        mock_prediction = np.array([[0.8, 0.2]], dtype=np.float32)
        mock_model.predict.return_value = mock_prediction
        mock_model.input_shape = (None, 299, 299, 3)
        
        # Данные запроса
        data = {
            'image': f'data:image/jpeg;base64,{self.image_base64}'
        }
        
        response = self.app.post(
            '/predict',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Проверяем, что модель была вызвана
        self.assertEqual(response.status_code, 200)
        
        # Парсим ответ
        response_data = json.loads(response.data)
        
        # Проверяем структуру ответа
        self.assertIn('success', response_data)
        self.assertIn('predictions', response_data)
        self.assertIn('original_image', response_data)
    
    @patch('app.routes.tf.keras.models.load_model')
    def test_load_model_mocked(self, mock_load_model):
        """Тест загрузки модели с mock"""
        # Создаем mock модель
        mock_model_instance = Mock()
        mock_model_instance.input_shape = (None, 299, 299, 3)
        mock_model_instance.output_shape = (None, 2)
        mock_model_instance.layers = [Mock(), Mock(), Mock()]
        
        mock_load_model.return_value = mock_model_instance
        
        # Пытаемся загрузить модель через routes
        from app.routes import load_model, model
        
        # Сбрасываем глобальную переменную
        import app.routes
        app.routes.model = None
        
        # Загружаем модель
        load_model()
        
        # Проверяем, что функция load_model была вызвана
        mock_load_model.assert_called_once()
        
        # Проверяем, что модель была установлена
        self.assertIsNotNone(app.routes.model)
    
    @patch('app.routes.preprocess_image')
    def test_predict_with_mock_preprocessing(self, mock_preprocess):
        """Тест с mock функцией предобработки"""
        # Настраиваем mock
        mock_processed = np.random.random((1, 299, 299, 3)).astype(np.float32)
        mock_preprocess.return_value = mock_processed
        
        # Данные запроса
        data = {
            'image': f'data:image/jpeg;base64,{self.image_base64}'
        }
        
        response = self.app.post(
            '/predict',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Проверяем, что функция предобработки была вызвана
        mock_preprocess.assert_called_once()
        
        # Проверяем ответ
        self.assertEqual(response.status_code, 200)
    
    @patch('app.routes.convert_tiff_to_jpeg')
    def test_tiff_conversion_mocked(self, mock_convert):
        """Тест обработки TIFF с mock конвертацией"""
        # Настраиваем mock
        mock_jpeg_data = b'mock_jpeg_data'
        mock_convert.return_value = mock_jpeg_data
        
        # Создаем "TIFF" данные (на самом деле любые)
        tiff_base64 = base64.b64encode(b'fake_tiff_data').decode()
        
        data = {
            'image': f'data:image/tiff;base64,{tiff_base64}'
        }
        
        response = self.app.post(
            '/predict',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Проверяем, что конвертация была вызвана
        mock_convert.assert_called_once()
    
    @patch('app.routes.model')
    @patch('app.routes.preprocess_image')
    def test_full_prediction_pipeline_mocked(self, mock_preprocess, mock_model):
        """Тест полного пайплайна предсказания с mock"""
        # Настраиваем mocks
        mock_processed = np.array([[[[0.5] * 3] * 299] * 299], dtype=np.float32)
        mock_preprocess.return_value = mock_processed
        
        mock_prediction = np.array([[0.75, 0.25]], dtype=np.float32)
        mock_model.predict.return_value = mock_prediction
        
        # Данные запроса
        data = {
            'image': f'data:image/jpeg;base64,{self.image_base64}'
        }
        
        response = self.app.post(
            '/predict',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Проверяем вызовы
        mock_preprocess.assert_called_once()
        mock_model.predict.assert_called_once_with(mock_processed, verbose=0)
        
        # Проверяем ответ
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.data)
        self.assertTrue(response_data['success'])
        self.assertEqual(response_data['predictions'], [0.75, 0.25])
    
    def test_health_endpoint_without_model(self):
        """Тест /health endpoint без загруженной модели"""
        # Временно заменяем модель на None
        original_model = None
        if hasattr(app, 'model'):
            original_model = app.model
        
        # Устанавливаем model = None
        import app.routes
        app.routes.model = None
        
        try:
            response = self.app.get('/health')
            self.assertEqual(response.status_code, 200)
            
            data = json.loads(response.data)
            self.assertFalse(data['model_loaded'])
        finally:
            # Восстанавливаем оригинальную модель
            app.routes.model = original_model
    
    @patch('app.routes.Image.open')
    def test_image_loading_error_mocked(self, mock_image_open):
        """Тест обработки ошибок загрузки изображения"""
        # Настраиваем mock для вызова исключения
        mock_image_open.side_effect = Exception("Mocked image loading error")
        
        data = {
            'image': f'data:image/jpeg;base64,{self.image_base64}'
        }
        
        response = self.app.post(
            '/predict',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Должен вернуться статус ошибки
        self.assertEqual(response.status_code, 500)
        
        response_data = json.loads(response.data)
        self.assertFalse(response_data['success'])
        self.assertIn('error', response_data)
    
    @patch('app.routes.base64.b64decode')
    def test_base64_decoding_error(self, mock_b64decode):
        """Тест обработки ошибок декодирования base64"""
        # Настраиваем mock для вызова исключения
        mock_b64decode.side_effect = Exception("Mocked base64 error")
        
        data = {
            'image': f'data:image/jpeg;base64,{self.image_base64}'
        }
        
        response = self.app.post(
            '/predict',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Должен вернуться статус ошибки
        self.assertEqual(response.status_code, 500)

if __name__ == '__main__':
    unittest.main()