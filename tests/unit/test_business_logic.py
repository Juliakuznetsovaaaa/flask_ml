import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import app

class TestBusinessLogic(unittest.TestCase):
    """Тесты бизнес-логики Flask приложения"""
    
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
    
    def test_app_initialization(self):
        """Тест инициализации Flask приложения"""
        self.assertIsNotNone(app)
        self.assertEqual(app.config['ENV'], 'production')
    
    def test_app_configuration(self):
        """Тест конфигурации приложения"""
        self.assertIn('SECRET_KEY', app.config)
        self.assertFalse(app.config.get('DEBUG', True))
    
    def test_url_rules(self):
        """Тест наличия всех endpoints"""
        rules = [str(rule) for rule in app.url_map.iter_rules()]
        expected_rules = ['/', '/health', '/predict']
        
        for expected_rule in expected_rules:
            with self.subTest(rule=expected_rule):
                self.assertIn(expected_rule, rules)
    
    def test_cors_configuration(self):
        """Тест настройки CORS"""
        # Проверяем, что CORS настроен
        from flask_cors import CORS
        cors_ext = None
        for ext in app.extensions.values():
            if isinstance(ext, CORS):
                cors_ext = ext
                break
        
        self.assertIsNotNone(cors_ext, "CORS не настроен")
    
    def test_error_handlers(self):
        """Тест обработчиков ошибок"""
        # Тестируем несуществующий endpoint
        response = self.app.get('/nonexistent')
        self.assertEqual(response.status_code, 404)

if __name__ == '__main__':
    unittest.main()