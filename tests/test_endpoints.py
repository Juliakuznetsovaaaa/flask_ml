import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_endpoint(client):
    """Test the health endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'
    assert 'model_loaded' in data

def test_index_endpoint(client):
    """Test the main index endpoint"""
    response = client.get('/')
    assert response.status_code == 200
    assert 'text/html' in response.content_type

def test_predict_endpoint_invalid_data(client):
    """Test predict endpoint with invalid data"""
    response = client.post('/predict', json={})
    assert response.status_code == 400

if __name__ == '__main__':
    pytest.main([__file__, '-v'])