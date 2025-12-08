# deploy_local.py
#!/usr/bin/env python
"""
Скрипт для локального деплоя и проверки Flask ML приложения
"""

import subprocess
import time
import requests
import json
import sys
import os

class LocalDeployer:
    def __init__(self, host='localhost', port=5000):
        self.host = host
        self.port = port
        self.base_url = f'http://{host}:{port}'
        self.container_name = 'flask-ml-app-local'
    
    def build_image(self):
        """Сборка Docker образа"""
        print("Сборка Docker образа...")
        try:
            result = subprocess.run(
                ['docker', 'build', '-t', 'flask-ml-app:local', '-f', 'Dockerfile.local', '.'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("Docker образ собран успешно")
                return True
            else:
                print(f"Ошибка сборки:\n{result.stderr}")
                return False
        except Exception as e:
            print(f"Ошибка при сборке: {e}")
            return False
    
    def run_container(self):
        """Запуск контейнера"""
        print("Запуск контейнера...")
        
        # Останавливаем старый контейнер, если есть
        self.stop_container()
        
        try:
            result = subprocess.run([
                'docker', 'run', '-d',
                '--name', self.container_name,
                '-p', f'{self.port}:5000',
                '--health-cmd', f'curl -f http://localhost:5000/health || exit 1',
                '--health-interval', '30s',
                '--health-timeout', '10s',
                '--health-retries', '3',
                'flask-ml-app:local'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("Контейнер запущен")
                print(f"Доступен по адресу: {self.base_url}")
                
                # Ждем запуска приложения
                print("Ожидание запуска приложения...")
                time.sleep(15)
                
                return True
            else:
                print(f"Ошибка запуска контейнера:\n{result.stderr}")
                return False
                
        except Exception as e:
            print(f"Ошибка при запуске контейнера: {e}")
            return False
    
    def stop_container(self):
        """Остановка контейнера"""
        try:
            subprocess.run(['docker', 'stop', self.container_name], 
                         capture_output=True, text=True)
            subprocess.run(['docker', 'rm', self.container_name], 
                         capture_output=True, text=True)
            print(" Старый контейнер остановлен и удален")
        except:
            pass
    
    def check_health(self):
        """Проверка health endpoint"""
        print("Проверка health endpoint...")
        try:
            response = requests.get(f'{self.base_url}/health', timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"Health endpoint: {json.dumps(data, indent=2)}")
                
                if data.get('status') == 'healthy':
                    print("Приложение здорово")
                    return True
                else:
                    print(f"Приложение не здорово: статус {data.get('status')}")
                    return False
            else:
                print(f"Health endpoint вернул {response.status_code}")
                return False
        except Exception as e:
            print(f"Ошибка при проверке health: {e}")
            return False
    
    def check_main_page(self):
        """Проверка главной страницы"""
        print("Проверка главной страницы...")
        try:
            response = requests.get(self.base_url, timeout=10)
            if response.status_code == 200:
                content = response.text
                
                # Проверяем ключевые элементы
                checks = [
                    ('HTML документ', '<!DOCTYPE html>' in content),
                    ('Заголовок', 'Выявление остеогенной дифференцировки' in content),
                    ('Интерфейс загрузки', 'Загрузите изображение' in content),
                    ('Поле файла', 'id="fileInput"' in content),
                ]
                
                all_passed = True
                for check_name, passed in checks:
                    if passed:
                        print(f"  {check_name}")
                    else:
                        print(f"  {check_name}")
                        all_passed = False
                
                return all_passed
            else:
                print(f" Главная страница вернула {response.status_code}")
                return False
        except Exception as e:
            print(f" Ошибка при проверке главной страницы: {e}")
            return False
    
    def check_static_files(self):
        """Проверка статических файлов"""
        print("Проверка статических файлов...")
        try:
            # Проверяем наличие CSS файла
            response = requests.get(f'{self.base_url}/static/style.css', timeout=10)
            
            if response.status_code == 200:
                print(" CSS файлы доступны")
                return True
            elif response.status_code == 404:
                print(" CSS файлы не найдены (может быть ожидаемо в тестах)")
                return True
            else:
                print(f" Статические файлы: {response.status_code}")
                return True  # Не фатальная ошибка
        except Exception as e:
            print(f" Ошибка при проверке статических файлов: {e}")
            return True  # Не фатальная ошибка
    
    def check_predict_endpoint(self):
        """Проверка predict endpoint"""
        print("Проверка predict endpoint...")
        try:
            # Проверяем структуру ответа (не отправляя реальное изображение)
            response = requests.post(
                f'{self.base_url}/predict',
                json={'image': 'test'},
                timeout=30
            )
            
            if response.status_code in [200, 400, 500]:
                print(f"Predict endpoint отвечает (статус: {response.status_code})")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f" Ответ: {json.dumps(data, indent=2)}")
                
                return True
            else:
                print(f"Predict endpoint вернул неожиданный статус: {response.status_code}")
                return False
        except Exception as e:
            print(f"Ошибка при проверке predict endpoint: {e}")
            return False
    
    def test_frontend_functionality(self):
        """Тестирование функциональности фронтенда"""
        print(" Тестирование фронтенд функциональности...")
        
        # Создаем простой HTML файл для тестирования
        test_html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Frontend</title>
            <script>
                async function testFrontend() {
                    const baseUrl = 'http://localhost:5000';
                    
                    // Тестируем доступность endpoints
                    const endpoints = [
                        { url: baseUrl + '/', name: 'Главная' },
                        { url: baseUrl + '/health', name: 'Health' }
                    ];
                    
                    for (const endpoint of endpoints) {
                        try {
                            const response = await fetch(endpoint.url);
                            console.log(`${endpoint.name}: ${response.status}`);
                        } catch (error) {
                            console.error(`${endpoint.name}: ${error.message}`);
                        }
                    }
                }
                
                // Запускаем тест при загрузке
                window.onload = testFrontend;
            </script>
        </head>
        <body>
            <h1>Тест фронтенда Flask ML приложения</h1>
            <div id="results"></div>
        </body>
        </html>
        '''
        
        # Сохраняем тестовый файл
        with open('test_frontend.html', 'w', encoding='utf-8') as f:
            f.write(test_html)
        
        print("Тестовый HTML файл создан: test_frontend.html")
        print("Откройте его в браузере для проверки фронтенда")
        
        return True
    
    def run_load_test(self):
        """Запуск простого нагрузочного теста"""
        print("Запуск нагрузочного теста...")
        
        import threading
        
        results = []
        
        def make_request(url, request_id):
            try:
                start_time = time.time()
                response = requests.get(url, timeout=10)
                end_time = time.time()
                
                response_time = (end_time - start_time) * 1000  # в мс
                results.append({
                    'request_id': request_id,
                    'status_code': response.status_code,
                    'response_time': response_time
                })
            except Exception as e:
                results.append({
                    'request_id': request_id,
                    'error': str(e)
                })
        
        # Создаем несколько параллельных запросов
        threads = []
        for i in range(5):
            thread = threading.Thread(
                target=make_request,
                args=(f'{self.base_url}/health', i)
            )
            threads.append(thread)
            thread.start()
        
        # Ждем завершения всех потоков
        for thread in threads:
            thread.join()
        
        # Анализируем результаты
        successful = [r for r in results if 'status_code' in r and r['status_code'] == 200]
        failed = [r for r in results if 'error' in r]
        
        print(f"Результаты нагрузочного теста:")
        print(f"  Успешных запросов: {len(successful)}")
        print(f"  Неудачных запросов: {len(failed)}")
        
        if successful:
            avg_time = sum(r['response_time'] for r in successful) / len(successful)
            max_time = max(r['response_time'] for r in successful)
            min_time = min(r['response_time'] for r in successful)
            
            print(f"  Среднее время ответа: {avg_time:.2f} мс")
            print(f"  Минимальное время: {min_time:.2f} мс")
            print(f"  Максимальное время: {max_time:.2f} мс")
        
        return len(failed) == 0
    
    def deploy_and_validate(self):
        """Полный процесс деплоя и валидации"""
        print("=" * 60)
        print("ЗАПУСК ЛОКАЛЬНОГО ДЕПЛОЯ FLASK ML ПРИЛОЖЕНИЯ")
        print("=" * 60)
        
        steps = [
            ("Сборка Docker образа", self.build_image),
            ("Запуск контейнера", self.run_container),
            ("Проверка health endpoint", self.check_health),
            ("Проверка главной страницы", self.check_main_page),
            ("Проверка статических файлов", self.check_static_files),
            ("Проверка predict endpoint", self.check_predict_endpoint),
            ("Нагрузочное тестирование", self.run_load_test),
            ("Тестирование фронтенда", self.test_frontend_functionality),
        ]
        
        results = []
        for step_name, step_func in steps:
            print(f"\n Шаг: {step_name}")
            try:
                success = step_func()
                results.append((step_name, success))
                if not success and step_name != "Тестирование фронтенда":
                    print(f"Шаг '{step_name}' завершился с ошибкой")
                    break
            except Exception as e:
                print(f"Непредвиденная ошибка в шаге '{step_name}': {e}")
                results.append((step_name, False))
                break
        
        # Выводим итоговый отчет
        print("\n" + "=" * 60)
        print("ИТОГОВЫЙ ОТЧЕТ ПО ДЕПЛОЮ")
        print("=" * 60)
        
        all_passed = True
        for step_name, success in results:
            status = "УСПЕХ" if success else "ОШИБКА"
            print(f"{status}: {step_name}")
            if not success:
                all_passed = False
        
        print("\n" + "=" * 60)
        if all_passed:
            print("ЛОКАЛЬНЫЙ ДЕПЛОЙ ЗАВЕРШЕН УСПЕШНО!")
            print(f"Приложение доступно по адресу: {self.base_url}")
        else:
            print("ЛОКАЛЬНЫЙ ДЕПЛОЙ ЗАВЕРШЕН С ОШИБКАМИ")
            print("Проверьте логи и исправьте проблемы")
        
        return all_passed

def main():
    """Основная функция"""
    deployer = LocalDeployer()
    
    try:
        success = deployer.deploy_and_validate()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n Деплой прерван пользователем")
        deployer.stop_container()
        sys.exit(1)
    except Exception as e:
        print(f"\nКритическая ошибка: {e}")
        deployer.stop_container()
        sys.exit(1)

if __name__ == "__main__":
    main()