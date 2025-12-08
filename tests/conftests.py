# tests/conftest.py
import pytest
import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture(scope='session')
def app():
    """Фикстура для создания Flask приложения"""
    from app import app as flask_app
    
    # Настраиваем тестовое окружение
    flask_app.config.update({
        'TESTING': True,
        'DEBUG': False,
        'ENV': 'test'
    })
    
    return flask_app

@pytest.fixture
def client(app):
    """Фикстура для тестового клиента"""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Фикстура для CLI runner"""
    return app.test_cli_runner()