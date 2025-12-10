"""
Этап 5: Blue-Green деплой для Flask ML приложений
Реализация стратегии замещения контейнеров с валидацией ML моделей
"""

import subprocess
import time
import requests
import json
import sys
import os
import socket
from datetime import datetime
import uuid

class BlueGreenDeployer:
    """
    Класс для реализации Blue-Green деплоя ML приложений
    """
    
    def __init__(self, app_name="flask-ml-app", main_port=5000, 
                 blue_port=5001, green_port=5002, health_timeout=180):
        """
        Инициализация Blue-Green деплоя
        """
        self.app_name = app_name
        self.main_port = main_port
        self.blue_port = blue_port
        self.green_port = green_port
        
        # Имена контейнеров и образов
        self.container_blue = f"{app_name}-blue"
        self.container_green = f"{app_name}-green"
        
        self.image_blue = f"{app_name}:blue"
        self.image_green = f"{app_name}:green"
        self.image_latest = f"{app_name}:latest"
        
        # Конфигурация
        self.health_timeout = health_timeout
        self.graceful_shutdown_time = 30
        
        # Состояние
        self.active_environment = None
        self.previous_environment = None
        self.deployment_log = []
        self.metrics = {
            'deployments': 0,
            'successful': 0,
            'failed': 0,
            'rollbacks': 0,
            'avg_deployment_time': 0
        }
        
    def log(self, message, level="INFO"):
        """Логирование событий деплоя"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} [{level}] {message}"
        self.deployment_log.append(log_entry)
        
        if level == "SUCCESS":
            print(f" {message}")
        elif level == "ERROR":
            print(f" {message}")
        elif level == "WARNING":
            print(f"  {message}")
        else:
            print(f" {message}")
            
        # Пишем в файл
        self._write_to_log_file(log_entry)
    
    def _write_to_log_file(self, log_entry):
        """Запись логов в файл"""
        log_dir = "deployment_logs"
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"deploy_{datetime.now().strftime('%Y%m%d')}.log")
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry + "\n")
        except:
            pass
    
    def run_command(self, command, check=False, description=""):
        """Выполнение shell команд с обработкой ошибок"""
        if description:
            print(f"    {description}...")
        
        try:
            # Для Windows используем правильное экранирование
            if sys.platform == "win32":
                command = command.replace("'", '"')
            
            result = subprocess.run(
                command,
                shell=True,
                check=check,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.stdout:
                print(f"   Команда выполнена успешно")
                return {
                    'success': True,
                    'stdout': result.stdout.strip(),
                    'stderr': result.stderr.strip() if result.stderr else '',
                    'returncode': result.returncode
                }
            else:
                return {
                    'success': True,
                    'stdout': '',
                    'stderr': result.stderr.strip() if result.stderr else '',
                    'returncode': result.returncode
                }
                
        except subprocess.CalledProcessError as e:
            error_msg = f"Ошибка выполнения команды"
            if e.stderr:
                error_msg += f": {e.stderr[:100]}"
            print(f" {error_msg}")
            return {
                'success': False,
                'stdout': e.stdout.strip() if e.stdout else '',
                'stderr': e.stderr.strip() if e.stderr else '',
                'returncode': e.returncode
            }
        except subprocess.TimeoutExpired:
            print(f"     Таймаут выполнения команды")
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Command timed out',
                'returncode': -1
            }
        except Exception as e:
            print(f"Неожиданная ошибка: {str(e)[:100]}")
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'returncode': -1
            }
    
    def detect_active_environment(self):
        """
        Обнаружение активного окружения (blue/green)
        """
        print("Поиск активного ML окружения...")
        
        # Проверяем порт 5000
        try:
            response = requests.get(f"http://localhost:{self.main_port}/health", timeout=3)
            if response.status_code == 200:
                # Ищем контейнер на порту 5000
                result = self.run_command(
                    f'docker ps --filter "publish={self.main_port}" --format "{{{{.Names}}}}"',
                    check=False
                )
                if result['success'] and result['stdout']:
                    container_name = result['stdout'].strip()
                    if 'blue' in container_name:
                        self.active_environment = 'blue'
                        print(f"Активное окружение: BLUE ({container_name})")
                        return 'blue'
                    elif 'green' in container_name:
                        self.active_environment = 'green'
                        print(f"Активное окружение: GREEN ({container_name})")
                        return 'green'
        except:
            pass
        
        # Проверяем все контейнеры
        result = self.run_command(
            f'docker ps --filter "name={self.app_name}" --format "{{{{.Names}}}} {{{{.Ports}}}}"',
            check=False
        )
        
        if result['success'] and result['stdout']:
            for line in result['stdout'].strip().split('\n'):
                if line and self.app_name in line:
                    if 'blue' in line:
                        self.active_environment = 'blue'
                        print(f"Найдено окружение BLUE")
                        return 'blue'
                    elif 'green' in line:
                        self.active_environment = 'green'
                        print(f"Найдено окружение GREEN")
                        return 'green'
        
        print("Активное окружение не обнаружено")
        return None
    
    def cleanup_old_containers(self):
        """
        Очистка старых контейнеров и образов
        """
        print("Очистка старых ресурсов...")
        
        # Удаляем остановленные контейнеры
        self.run_command("docker container prune -f", check=False)
        
        # Удаляем dangling образы
        self.run_command("docker image prune -f", check=False)
        
        print("Очистка завершена")
    
    def graceful_shutdown(self, container_name):
        """
        Graceful shutdown контейнера
        """
        print(f"Остановка контейнера {container_name}...")
        
        # Проверяем, существует ли контейнер
        check_result = self.run_command(
            f'docker ps -a --filter "name={container_name}" --format "{{{{.Names}}}}"',
            check=False
        )
        
        if not check_result['success'] or container_name not in check_result['stdout']:
            print(f"     Контейнер {container_name} не существует")
            return True
        
        # Останавливаем контейнер
        stop_result = self.run_command(
            f"docker stop {container_name}",
            check=False
        )
        
        if stop_result['success']:
            print(f"    Контейнер {container_name} остановлен")
        else:
            # Если не удалось остановить, убиваем
            print(f"     Контейнер {container_name} не остановился, принудительная остановка...")
            kill_result = self.run_command(
                f"docker kill {container_name}",
                check=False
            )
            
            if not kill_result['success']:
                print(f"  Не удалось остановить контейнер {container_name}")
                return False
        
        # Удаляем контейнер
        remove_result = self.run_command(
            f"docker rm {container_name}",
            check=False
        )
        
        if remove_result['success']:
            print(f"    Контейнер {container_name} удален")
            return True
        else:
            print(f"     Не удалось удалить контейнер {container_name}")
            return False
    
    def build_new_image(self, environment, dockerfile="Dockerfile"):
        """
        Сборка нового образа для окружения
        """
        print(f"Сборка образа для окружения {environment.upper()}...")
        
        image_name = getattr(self, f"image_{environment}")
        
        # Формируем команду сборки
        build_cmd = f"docker build -t {image_name} -f {dockerfile} ."
        
        # Выполняем сборку
        result = self.run_command(
            build_cmd,
            description=f"Сборка образа {image_name}"
        )
        
        if result['success']:
            build_id = str(uuid.uuid4())[:8]
            print(f"Образ {image_name} успешно собран (Build ID: {build_id})")
            return True
        else:
            print(f"Ошибка сборки образа для {environment}")
            return False
    
    def deploy_environment(self, environment, validate_model=True):
        """
        Деплой окружения
        """
        start_time = time.time()
        
        container_name = getattr(self, f"container_{environment}")
        image_name = getattr(self, f"image_{environment}")
        port = getattr(self, f"{environment}_port")
        
        print(f"Деплой окружения {environment.upper()}...")
        
        # 1. Останавливаем старый контейнер (если есть)
        self.graceful_shutdown(container_name)
        
        # 2. Запускаем новый контейнер
        print(f"Запуск контейнера {container_name} на порту {port}...")
        
        run_cmd = (
            f"docker run -d "
            f"--name {container_name} "
            f"-p {port}:5000 "
            f"--restart unless-stopped "
            f"--memory=2g "
            f"--cpus=1.0 "
            f"{image_name}"
        )
        
        result = self.run_command(
            run_cmd,
            description=f"Запуск контейнера {container_name}"
        )
        
        if not result['success']:
            print(f"Ошибка запуска контейнера {environment}")
            return False
        
        # 3. Ожидание запуска приложения
        if not self.wait_for_health(environment):
            print(f"Таймаут ожидания запуска окружения {environment}")
            return False
        
        # 4. Валидация ML модели (если требуется)
        if validate_model:
            self.validate_ml_model(environment)
        
        deployment_time = time.time() - start_time
        print(f"Окружение {environment.upper()} успешно развернуто за {deployment_time:.2f} секунд")
        
        return True
    
    def wait_for_health(self, environment, timeout=None):
        """
        Ожидание готовности окружения
        """
        if timeout is None:
            timeout = self.health_timeout
            
        port = getattr(self, f"{environment}_port")
        url = f"http://localhost:{port}/health"
        
        print(f"Ожидание готовности окружения {environment.upper()} (максимум {timeout} сек)...")
        
        start_time = time.time()
        check_interval = 5
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    health_data = response.json()
                    
                    if health_data.get('status') == 'healthy':
                        print(f"Окружение {environment.upper()} готово")
                        return True
                    
                    # Проверяем статус модели
                    model_status = health_data.get('model_status')
                    if model_status == 'loading':
                        print(f"    Модель загружается...")
                    elif model_status == 'ready':
                        print(f"    Модель готова")
                        return True
                
                elapsed = time.time() - start_time
                print(f"     Ожидание... ({elapsed:.0f}/{timeout} сек)")
                
            except requests.exceptions.ConnectionError:
                elapsed = time.time() - start_time
                print(f"    Соединение отсутствует... ({elapsed:.0f}/{timeout} сек)")
            except Exception as e:
                print(f"     Ошибка проверки здоровья: {e}")
            
            time.sleep(check_interval)
        
        print(f"Таймаут ожидания здоровья окружения {environment}")
        return False
    
    def validate_ml_model(self, environment):
        """
        Валидация ML модели после деплоя (не блокирующая)
        """
        port = getattr(self, f"{environment}_port")
        
        print(f" Проверка ML модели в окружении {environment.upper()}...")
        
        validation_endpoints = [
            ('/health', 'GET'),
            ('/api/model/info', 'GET'),
            ('/predict', 'POST'),
        ]
        
        # Пробуем разные endpoint'ы для валидации
        for endpoint, method in validation_endpoints:
            url = f"http://localhost:{port}{endpoint}"
            
            try:
                if method == 'GET':
                    response = requests.get(url, timeout=10)
                else:
                    # Отправляем тестовые данные
                    test_data = {"test": "validation"}
                    response = requests.post(url, json=test_data, timeout=10)
                
                if response.status_code in [200, 400, 422]:
                    print(f"    Endpoint {endpoint} отвечает (статус: {response.status_code})")
                    return True
                
            except Exception as e:
                print(f"     Endpoint {endpoint} не отвечает: {e}")
                continue
        
        print(f"  Валидация ML модели не пройдена, но приложение работает")
        return False
    
    def switch_traffic(self, new_environment):
        """
        Переключение трафика на новое окружение
        """
        print(f" Переключение трафика на окружение {new_environment.upper()}...")
        
        old_environment = self.active_environment
        self.previous_environment = old_environment
        
        try:
            # 1. Получаем контейнер нового окружения
            new_container = getattr(self, f"container_{new_environment}")
            new_port = getattr(self, f"{new_environment}_port")
            
            # 2. Останавливаем текущий контейнер на основном порту
            if old_environment:
                old_container = getattr(self, f"container_{old_environment}")
                print(f"     Останавливаем старое окружение {old_environment.upper()}...")
                self.graceful_shutdown(old_container)
            
            # 3. Останавливаем новый контейнер (если запущен на своем порту)
            print(f"     Останавливаем новое окружение с порта {new_port}...")
            self.graceful_shutdown(new_container)
            
            # 4. Запускаем контейнер на основном порту
            image_name = getattr(self, f"image_{new_environment}")
            
            run_cmd = (
                f"docker run -d "
                f"--name {new_container} "
                f"-p {self.main_port}:5000 "
                f"--restart unless-stopped "
                f"--memory=2g "
                f"--cpus=1.0 "
                f"{image_name}"
            )
            
            result = self.run_command(
                run_cmd,
                description=f"Запуск контейнера {new_container} на основном порту"
            )
            
            if not result['success']:
                raise Exception(f"Ошибка запуска контейнера на основном порту")
            
            # 5. Обновляем активное окружение
            self.active_environment = new_environment
            
            # 6. Проверяем здоровье на основном порту
            if self.wait_for_health_on_main_port():
                print(f" Трафик успешно переключен на {new_environment.upper()}")
                return True
            else:
                print(" Проверка здоровья на основном порту не пройдена")
                return False
            
        except Exception as e:
            print(f" Ошибка переключения трафика: {e}")
            return False
    
    def wait_for_health_on_main_port(self, timeout=60):
        """Проверка здоровья на основном порту после переключения"""
        url = f"http://localhost:{self.main_port}/health"
        
        print("Проверка здоровья на основном порту...")
        
        start_time = time.time()
        check_interval = 2
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    health_data = response.json()
                    if health_data.get('status') == 'healthy':
                        print(f" Основной порт готов")
                        return True
            except:
                pass
            
            time.sleep(check_interval)
            elapsed = time.time() - start_time
            print(f"     Ожидание... ({elapsed:.0f}/{timeout} сек)")
        
        print(" Таймаут проверки здоровья на основном порту")
        return False
    
    def perform_rollback(self):
        """
        Откат к предыдущей версии
        """
        if not self.previous_environment:
            print(" Нет предыдущего окружения для отката")
            return False
        
        print(f" Инициирован откат к окружению {self.previous_environment.upper()}")
        
        try:
            # Переключаем трафик обратно
            success = self.switch_traffic(self.previous_environment)
            
            if success:
                print(f" Откат к {self.previous_environment.upper()} выполнен успешно")
                self.metrics['rollbacks'] += 1
                return True
            else:
                print(" Откат не удался")
                return False
                
        except Exception as e:
            print(f" Ошибка при откате: {e}")
            return False
    
    def deploy_with_replacement(self, strategy='blue-green', validate=True, 
                                canary_percentage=0, auto_rollback=True):
        """
        Основной метод деплоя с замещением
        """
        deploy_start = time.time()
        self.metrics['deployments'] += 1
        
        print("\n" + "=" * 80)
        print(f" ЗАПУСК ДЕПЛОЯ С ЗАМЕЩЕНИЕМ (стратегия: {strategy})")
        print("=" * 80)
        
        try:
            # 1. Обнаружение текущего состояния
            current_env = self.detect_active_environment()
            
            if current_env is None:
                # Первый деплой
                target_env = 'blue'
                print(" Первый деплой, выбираем BLUE окружение")
            else:
                # Определяем целевое окружение
                target_env = 'green' if current_env == 'blue' else 'blue'
                print(f" Текущее окружение: {current_env.upper()}, целевое: {target_env.upper()}")
            
            # 2. Сборка нового образа
            if not self.build_new_image(target_env):
                raise Exception("Ошибка сборки образа")
            
            # 3. Деплой нового окружения
            if not self.deploy_environment(target_env, validate_model=validate):
                raise Exception("Ошибка деплоя окружения")
            
            # 4. Переключение трафика
            if not self.switch_traffic(target_env):
                if auto_rollback and current_env:
                    print("  Переключение трафика не удалось, запуск отката...")
                    self.perform_rollback()
                    raise Exception("Переключение трафика не удалось, откат выполнен")
                else:
                    raise Exception("Переключение трафика не удалось")
            
            # 5. Очистка старых ресурсов
            self.cleanup_old_containers()
            
            # 6. Обновление метрик
            deployment_time = time.time() - deploy_start
            self.metrics['successful'] += 1
            if self.metrics['successful'] > 1:
                self.metrics['avg_deployment_time'] = (
                    (self.metrics['avg_deployment_time'] * (self.metrics['successful'] - 1) + deployment_time) 
                    / self.metrics['successful']
                )
            else:
                self.metrics['avg_deployment_time'] = deployment_time
            
            print(f"\n ДЕПЛОЙ УСПЕШНО ЗАВЕРШЕН за {deployment_time:.2f} секунд")
            self._generate_deployment_report(target_env, deployment_time, True)
            
            return True
            
        except Exception as e:
            deployment_time = time.time() - deploy_start
            self.metrics['failed'] += 1
            
            print(f"\nДЕПЛОЙ ЗАВЕРШЕН С ОШИБКОЙ: {e}")
            self._generate_deployment_report(None, deployment_time, False, str(e))
            
            return False
    
    def _generate_deployment_report(self, environment, duration, success, error=None):
        """Генерация отчета о деплое"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'environment': environment,
            'duration_seconds': round(duration, 2),
            'success': success,
            'error': error,
            'active_environment': self.active_environment,
            'previous_environment': self.previous_environment,
            'metrics': self.metrics.copy(),
            'log_tail': self.deployment_log[-20:] if len(self.deployment_log) > 20 else self.deployment_log
        }
        
        # Сохраняем отчет
        reports_dir = "deployment_reports"
        os.makedirs(reports_dir, exist_ok=True)
        
        report_file = os.path.join(
            reports_dir, 
            f"deploy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            print(f"Отчет сохранен в {report_file}")
            
            # Генерируем HTML отчет
            self._generate_html_report(report, report_file.replace('.json', '.html'))
        except Exception as e:
            print(f"Ошибка сохранения отчета: {e}")
    
    def _generate_html_report(self, report, filename):
        """Генерация HTML отчета"""
        try:
            # Формируем HTML
            logs_html = ""
            for log in report['log_tail']:
                if 'ERROR' in log:
                    logs_html += f'<div style="margin: 5px 0; padding: 5px; border-left: 3px solid red;">{log}</div>'
                elif 'WARNING' in log:
                    logs_html += f'<div style="margin: 5px 0; padding: 5px; border-left: 3px solid orange;">{log}</div>'
                elif 'SUCCESS' in log:
                    logs_html += f'<div style="margin: 5px 0; padding: 5px; border-left: 3px solid green;">{log}</div>'
                else:
                    logs_html += f'<div style="margin: 5px 0; padding: 5px; border-left: 3px solid blue;">{log}</div>'
            
            error_section = ""
            if report.get('error'):
                error_section = f"""
                <div style="background: #ffebee; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="color: #721c24;">Ошибка</h3>
                    <p style="color: #721c24;">{report['error']}</p>
                </div>
                """
            
            status_color = "green" if report['success'] else "red"
            status_text = "УСПЕШНО" if report['success'] else "НЕУДАЧНО"
            
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Отчет о деплое ML приложения</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ border-bottom: 2px solid #333; padding-bottom: 20px; margin-bottom: 30px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .metric-card {{ background: #f0f0f0; padding: 15px; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1> Отчет о деплое ML приложения</h1>
            <p><strong>Время:</strong> {report['timestamp']}</p>
            <p><strong>Статус:</strong> <span style="color: {status_color}; font-weight: bold;">{status_text}</span></p>
            <p><strong>Длительность:</strong> {report['duration_seconds']} секунд</p>
            <p><strong>Активное окружение:</strong> {report.get('active_environment', 'Нет')}</p>
        </div>
        
        <div class="metrics">
            <div class="metric-card">
                <h3>Всего деплоев</h3>
                <p>{report['metrics']['deployments']}</p>
            </div>
            <div class="metric-card">
                <h3>Успешных</h3>
                <p>{report['metrics']['successful']}</p>
            </div>
            <div class="metric-card">
                <h3>Неудачных</h3>
                <p>{report['metrics']['failed']}</p>
            </div>
            <div class="metric-card">
                <h3>Откатов</h3>
                <p>{report['metrics']['rollbacks']}</p>
            </div>
        </div>
        
        {error_section}
        
        <h2> Логи деплоя</h2>
        <div id="logs">
            {logs_html}
        </div>
    </div>
</body>
</html>"""
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"HTML отчет сохранен в {filename}")
        except Exception as e:
            print(f"Ошибка генерации HTML отчета: {e}")

def main():
    """Основная функция для запуска деплоя с замещением"""
    print("=" * 80)
    print(" ЭТАП 5: BLUE-GREEN ДЕПЛОЙ ML ПРИЛОЖЕНИЯ")
    print("=" * 80)
    
    # Создаем деплоер
    deployer = BlueGreenDeployer(
        app_name="flask-ml-app",
        main_port=5000,
        blue_port=5001,
        green_port=5002,
        health_timeout=180
    )
    
    # Определяем стратегию деплоя
    import argparse
    parser = argparse.ArgumentParser(description='Blue-Green деплой ML приложения')
    parser.add_argument('--strategy', choices=['blue-green', 'canary', 'rolling'], 
                       default='blue-green', help='Стратегия деплоя')
    parser.add_argument('--validate', action='store_true', default=True,
                       help='Валидация ML модели')
    parser.add_argument('--no-validate', dest='validate', action='store_false',
                       help='Не валидировать ML модель')
    parser.add_argument('--canary-percentage', type=int, default=0,
                       help='Процент трафика для canary тестирования')
    parser.add_argument('--auto-rollback', action='store_true', default=True,
                       help='Автоматический откат при проблемах')
    parser.add_argument('--no-auto-rollback', dest='auto_rollback', action='store_false',
                       help='Не выполнять автоматический откат')
    parser.add_argument('--rollback', action='store_true',
                       help='Выполнить откат к предыдущей версии')
    
    args = parser.parse_args()
    
    if args.rollback:
        # Выполняем откат
        print("\n" + "=" * 80)
        print(" ЗАПУСК ОТКАТА")
        print("=" * 80)
        success = deployer.perform_rollback()
        
        if success:
            print("\n ОТКАТ ВЫПОЛНЕН УСПЕШНО")
        else:
            print("\n ОТКАТ НЕ УДАЛСЯ")
        
        sys.exit(0 if success else 1)
    
    # Выполняем деплой
    success = deployer.deploy_with_replacement(
        strategy=args.strategy,
        validate=args.validate,
        canary_percentage=args.canary_percentage,
        auto_rollback=args.auto_rollback
    )
    
    if success:
        print("\n" + "=" * 80)
        print("ДЕПЛОЙ ЗАВЕРШЕН УСПЕШНО!")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print(" ДЕПЛОЙ ЗАВЕРШЕН С ОШИБКАМИ")
        print("=" * 80)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()