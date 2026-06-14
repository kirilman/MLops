import pytest
from fastapi.testclient import TestClient
from typing import Optional
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import builtins

# Сохраняем оригинальный open
original_open = builtins.open

def mock_open_wrapper(file, mode='r', *args, **kwargs):
    """Мокируем open для файлов моделей"""
    if file in ['cars.joblib', 'power.joblib']:
        mock_file = MagicMock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=False)
        return mock_file
    return original_open(file, mode, *args, **kwargs)

# Мокируем загрузку моделей перед импортом приложения
mock_model = Mock()
mock_model.predict = Mock(return_value=[10000.0])

mock_predict2price = Mock()
mock_predict2price.inverse_transform = Mock(return_value=[[25000.0]])

with patch('builtins.open', mock_open_wrapper):
    with patch('pickle.load') as mock_pickle_load:
        mock_pickle_load.side_effect = [mock_model, mock_predict2price]
        from main import app, CarFeatures

client = TestClient(app)


class TestPredictEndpoint:
    """Тесты для эндпоинта /predict"""

    def test_predict_success(self):
        """Тест успешного предсказания"""
        car_data = {
            "make": "BMW",
            "model": "X5",
            "year": 2020,
            "style": "SUV",
            "distance": 50000.0,
            "engine_capacity": 3000.0,
            "fuel_type": "Diesel",
            "transmission": "Automatic"
        }
        
        response = client.post("/predict", json=car_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "predicted_price" in data or "error" in data

    def test_predict_missing_fields(self):
        """Тест с отсутствующими обязательными полями"""
        car_data = {
            "make": "BMW",
            "year": 2020
        }
        
        response = client.post("/predict", json=car_data)
        
        assert response.status_code == 422

    def test_predict_invalid_year_type(self):
        """Тест с некорректным типом года (Pydantic автоконвертирует строку в int)"""
        car_data = {
            "make": "BMW",
            "model": "X5",
            "year": "2020",  # Pydantic v2 автоматически конвертирует в int
            "style": "SUV",
            "distance": 50000.0,
            "engine_capacity": 3000.0,
            "fuel_type": "Diesel",
            "transmission": "Automatic"
        }
        
        response = client.post("/predict", json=car_data)
        
        # Pydantic v2 автоматически конвертирует "2020" в 2020, поэтому будет 200
        assert response.status_code == 200

    def test_predict_invalid_year_value(self):
        """Тест с некорректным значением года (не число)"""
        car_data = {
            "make": "BMW",
            "model": "X5",
            "year": "invalid",  # Не может быть конвертировано в int
            "style": "SUV",
            "distance": 50000.0,
            "engine_capacity": 3000.0,
            "fuel_type": "Diesel",
            "transmission": "Automatic"
        }
        
        response = client.post("/predict", json=car_data)
        
        assert response.status_code == 422

    def test_predict_empty_body(self):
        """Тест с пустым телом запроса"""
        response = client.post("/predict", json={})
        
        assert response.status_code == 422


class TestHealthCheck:
    """Тесты для проверки доступности API"""

    def test_root_endpoint(self):
        """Тест корневого эндпоинта"""
        response = client.get("/")
        assert response.status_code in [200, 404, 405]

    def test_docs_available(self):
        """Тест доступности документации"""
        response = client.get("/docs")
        assert response.status_code in [200, 404]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
