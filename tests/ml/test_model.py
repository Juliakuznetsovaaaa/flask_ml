import unittest
import sys
import os
import tempfile
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import tensorflow as tf
import numpy as np
from PIL import Image

class TestMLModel(unittest.TestCase):
    """Тесты ML модели и валидации предсказаний"""
    
    def setUp(self):
        # Создаем временную модель для тестов
        self.temp_dir = tempfile.mkdtemp()
        self.model_path = os.path.join(self.temp_dir, 'test_model.h5')
        
        # Создаем простую модель
        self.model = tf.keras.Sequential([
            tf.keras.layers.InputLayer(input_shape=(299, 299, 3)),
            tf.keras.layers.Conv2D(8, (3, 3), activation='relu'),
            tf.keras.layers.MaxPooling2D((2, 2)),
            tf.keras.layers.Flatten(),
            tf.keras.layers.Dense(2, activation='softmax')
        ])
        
        self.model.compile(
            optimizer='adam',
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        
        # Сохраняем модель
        self.model.save(self.model_path, save_format='h5')
    
    def tearDown(self):
        # Очищаем временные файлы
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_model_loading(self):
        """Тест загрузки модели"""
        # Загружаем модель
        loaded_model = tf.keras.models.load_model(self.model_path)
        
        # Проверяем структуру
        self.assertIsNotNone(loaded_model)
        self.assertEqual(len(loaded_model.layers), 4)
        self.assertEqual(loaded_model.input_shape, (None, 299, 299, 3))
        self.assertEqual(loaded_model.output_shape, (None, 2))
    
    def test_model_prediction_shape(self):
        """Тест формы выходных данных модели"""
        # Создаем тестовые данные
        test_data = np.random.random((2, 299, 299, 3)).astype(np.float32)
        
        # Получаем предсказания
        predictions = self.model.predict(test_data, verbose=0)
        
        # Проверяем форму
        self.assertEqual(predictions.shape, (2, 2))
        
        # Проверяем, что это вероятности
        self.assertTrue(np.all(predictions >= 0))
        self.assertTrue(np.all(predictions <= 1))
        
        # Сумма по классам должна быть ~1
        row_sums = predictions.sum(axis=1)
        np.testing.assert_array_almost_equal(row_sums, [1.0, 1.0], decimal=5)
    
    def test_model_prediction_consistency(self):
        """Тест консистентности предсказаний"""
        # Одни и те же данные должны давать одинаковые предсказания
        test_data = np.random.random((1, 299, 299, 3)).astype(np.float32)
        
        prediction1 = self.model.predict(test_data, verbose=0)
        prediction2 = self.model.predict(test_data, verbose=0)
        
        # Предсказания должны быть идентичными
        np.testing.assert_array_almost_equal(prediction1, prediction2, decimal=6)
    
    def test_model_with_different_batch_sizes(self):
        """Тест модели с разными размерами батча"""
        batch_sizes = [1, 4, 8]
        
        for batch_size in batch_sizes:
            with self.subTest(batch_size=batch_size):
                test_data = np.random.random((batch_size, 299, 299, 3)).astype(np.float32)
                
                predictions = self.model.predict(test_data, verbose=0)
                
                self.assertEqual(predictions.shape[0], batch_size)
                self.assertEqual(predictions.shape[1], 2)
    
    def test_model_input_normalization(self):
        """Тест нормализации входных данных"""
        # Создаем данные в диапазоне 0-255
        test_data_uint8 = np.random.randint(0, 256, (1, 299, 299, 3), dtype=np.uint8)
        test_data_float = test_data_uint8.astype(np.float32) / 255.0
        
        # Предсказания должны быть схожими
        pred_uint8 = self.model.predict(test_data_float, verbose=0)
        
        # Проверяем, что модель работает с нормализованными данными
        self.assertIsNotNone(pred_uint8)
    
    def test_model_performance(self):
        """Тест производительности модели"""
        import time
        
        test_data = np.random.random((1, 299, 299, 3)).astype(np.float32)
        
        # Измеряем время предсказания
        start_time = time.time()
        predictions = self.model.predict(test_data, verbose=0)
        end_time = time.time()
        
        prediction_time = end_time - start_time
        
        # Предсказание должно занимать разумное время
        # (менее 5 секунд на CPU для простой модели)
        self.assertLess(prediction_time, 5.0)
        
        print(f"Время предсказания: {prediction_time:.3f} сек")
    
    def test_model_output_interpretation(self):
        """Тест интерпретации выходных данных модели"""
        # Создаем тестовые данные
        test_data = np.random.random((3, 299, 299, 3)).astype(np.float32)
        
        predictions = self.model.predict(test_data, verbose=0)
        
        # Находим предсказанные классы
        predicted_classes = np.argmax(predictions, axis=1)
        
        # Проверяем, что классы в правильном диапазоне
        self.assertTrue(np.all(predicted_classes >= 0))
        self.assertTrue(np.all(predicted_classes < 2))
        
        # Проверяем уверенность предсказаний
        confidence = np.max(predictions, axis=1)
        self.assertTrue(np.all(confidence >= 0))
        self.assertTrue(np.all(confidence <= 1))
    
    def test_model_metadata(self):
        """Тест метаданных модели"""
        # Проверяем атрибуты модели
        self.assertIsNotNone(self.model.input_shape)
        self.assertIsNotNone(self.model.output_shape)
        self.assertIsNotNone(self.model.layers)
        
        # Проверяем, что модель скомпилирована
        self.assertIsNotNone(self.model.optimizer)
        self.assertIsNotNone(self.model.loss)
        self.assertIsNotNone(self.model.metrics)

if __name__ == '__main__':
    unittest.main()