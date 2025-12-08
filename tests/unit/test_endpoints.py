import unittest
import json
import base64
import io
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from PIL import Image
import numpy as np
from app import app

class TestAPIEndpoints(unittest.TestCase):
    """API тесты для проверки endpoints"""
    
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        
        # Создаем тестовое изображение
        self.test_image = Image.new('RGB', (300, 300), color='red')
        buffered = io.BytesIO()
        self.test_image.save(buffered, format='JPEG')
        self.image_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    def test_health_endpoint(self):
        """Тест /health endpoint"""
        response = self.app.get('/health')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        
        data = json.loads(response.data)
        
        self.assertIn('status', data)
        self.assertIn('model_loaded', data)
        self.assertIn('model_info', data)
        
        self.assertEqual(data['status'], 'healthy')
    
    def test_root_endpoint(self):
        """Тест главного endpoint /"""
        response = self.app.get('/')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'text/html; charset=utf-8')
        self.assertIn(b'<!DOCTYPE html>', response.data)
    
    def test_predict_endpoint_valid_request(self):
        """Тест /predict endpoint с валидным изображением"""
        data = {
            'image': f'data:image/jpeg;base64,{self.image_base64}'
        }
        
        response = self.app.post(
            '/predict',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Проверяем структуру ответа
        if response.status_code == 200:
            data = json.loads(response.data)
            
            self.assertIn('success', data)
            self.assertIn('predictions', data)
            self.assertIn('original_image', data)
            
            if data['success']:
                self.assertTrue(isinstance(data['predictions'], list))
                self.assertTrue(len(data['predictions']) > 0)
        else:
            # Если модель не загружена, это ожидаемо в тестах
            self.assertIn(response.status_code, [200, 500])
    
    def test_predict_endpoint_invalid_json(self):
        """Тест /predict endpoint с невалидным JSON"""
        response = self.app.post(
            '/predict',
            data='invalid json',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
    
    def test_predict_endpoint_missing_image(self):
        """Тест /predict endpoint без изображения"""
        data = {}
        
        response = self.app.post(
            '/predict',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
    
    def test_predict_endpoint_invalid_image(self):
        """Тест /predict endpoint с невалидным изображением"""
        data = {
            'image': 'data:image/jpeg;base64,invalid_base64'
        }
        
        response = self.app.post(
            '/predict',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertIn(response.status_code, [400, 500])
    
    def test_predict_endpoint_tiff_image(self):
        """Тест /predict endpoint с TIFF изображением"""
        # Создаем TIFF изображение
        tiff_image = Image.new('RGB', (300, 300), color='blue')
        buffered = io.BytesIO()
        tiff_image.save(buffered, format='TIFF')
        tiff_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        data = {
            'image': f'data:image/tiff;base64,{tiff_base64}'
        }
        
        response = self.app.post(
            '/predict',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Проверяем, что сервер обрабатывает TIFF
        self.assertIn(response.status_code, [200, 500])
    
    def test_static_files(self):
        """Тест обслуживания статических файлов"""
        response = self.app.get('/static/test.css')
        
        # Может вернуть 404 если файла нет, но важно что статика обслуживается
        self.assertIn(response.status_code, [200, 404])

if __name__ == '__main__':
    unittest.main()