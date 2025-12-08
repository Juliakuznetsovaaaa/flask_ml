# run_all_tests.py
import subprocess
import sys
import os

def run_tests(test_category=None):
    """Запуск всех тестов или определенной категории"""
    
    test_categories = {
        'unit': 'tests/unit/',
        'api': 'tests/api/',
        'image': 'tests/image_processing/',
        'ml': 'tests/ml/',
        'mock': 'tests/mock/',
        'all': 'tests/'
    }
    
    if test_category and test_category not in test_categories:
        print(f"❌ Неизвестная категория тестов: {test_category}")
        print(f"   Доступные категории: {', '.join(test_categories.keys())}")
        return False
    
    test_path = test_categories.get(test_category, 'tests/')
    
    print(f"🔧 Запуск тестов: {test_category or 'all'}")
    print(f"📁 Путь: {test_path}")
    print("-" * 50)
    
    cmd = [
        sys.executable, '-m', 'pytest',
        test_path,
        '-v',
        '--cov=app',
        '--cov-report=term-missing',
        '--cov-report=html'
    ]
    
    result = subprocess.run(cmd)
    
    print("-" * 50)
    
    if result.returncode == 0:
        print(f"✅ Тесты {test_category or 'all'} пройдены успешно!")
        return True
    else:
        print(f"❌ Тесты {test_category or 'all'} провалены!")
        return False

if __name__ == '__main__':
    if len(sys.argv) > 1:
        category = sys.argv[1]
        success = run_tests(category)
    else:
        success = run_tests('all')
    
    sys.exit(0 if success else 1)