let isModelLoaded = false;
const API_URL = '';

// Функция для проверки видимости answer-block
function checkAnswerBlockVisibility() {
    const answerBlock = document.querySelector('.answer-block');
    const uploadBlock = document.querySelector('.upload-block');
    
    if (!answerBlock || !uploadBlock) return;
    
    const computedStyle = window.getComputedStyle(answerBlock);
    
    if (computedStyle.visibility === 'hidden') {
        uploadBlock.classList.add('is-centered-absolute');
    } else {
        uploadBlock.classList.remove('is-centered-absolute');
    }
}


// Проверка доступности API
async function checkAPIHealth() {
    try {
        const response = await fetch(`${API_URL}/health`);
        const data = await response.json();
        isModelLoaded = data.model_loaded;
        
        if (data.model_loaded) {
            console.log('✅ API и модель готовы к работе');
            if (data.model_info && data.model_info.input_shape) {
                const shape = data.model_info.input_shape;
                console.log(`📐 Модель ожидает изображения размером: ${shape[1]}x${shape[2]}`);
            }
        } else {
            console.error('❌ Модель не загружена на сервере');
        }
        
        return data.model_loaded;
    } catch (error) {
        console.error('❌ API недоступно:', error);
        return false;
    }
}

// Проверка, является ли файл TIFF
function isTIFFFile(file) {
    return file.type === 'image/tiff' || 
           file.name.toLowerCase().endsWith('.tiff') || 
           file.name.toLowerCase().endsWith('.tif');
}

// Создание превью для TIFF (альтернативное изображение)
function createTIFFPreview() {
    return 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2Y1ZjVmNSIvPgogIDx0ZXh0IHg9IjEwMCIgeT0iMTAwIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTQiIGZpbGw9IiM5OTkiPlRJRkYgSW1hZ2U8L3RleHQ+Cjwvc3ZnPg==';
}

// Отправка изображения на сервер для предсказания
async function processImage(file) {
    try {
        console.log(`📁 Обрабатываем файл: ${file.name}, тип: ${file.type}, размер: ${(file.size / 1024 / 1024).toFixed(2)} MB`);
        
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            
            reader.onload = async function(event) {
                try {
                    const imageData = event.target.result;
                    
                    console.log(`📤 Отправляем изображение на сервер...`);
                    
                    const response = await fetch(`${API_URL}/predict`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            image: imageData
                        })
                    });
                    
                    if (!response.ok) {
                        const errorText = await response.text();
                        throw new Error(`HTTP error! status: ${response.status}, details: ${errorText}`);
                    }
                    
                    const result = await response.json();
                    
                    if (!result.success) {
                        throw new Error(result.error);
                    }
                    
                    console.log(`✅ Предсказание получено:`, result.predictions);
                    resolve(result);
                    
                } catch (error) {
                    reject(error);
                }
            };
            
            reader.onerror = function() {
                reject(new Error('Ошибка чтения файла'));
            };
            
            // Читаем файл как Data URL
            reader.readAsDataURL(file);
        });
        
    } catch (error) {
        console.error('Ошибка при обработке изображения:', error);
        throw error;
    }
}

// Показ результатов
function displayResults(result, fileName) {
    const answerBlock = document.querySelector('.answer-block');
    const answerImg = document.getElementById('answer-img');
    const answerText = document.getElementById('answer-text');
    const answerAccuracy = document.getElementById('answer-accuracy');
    const fileInfo = document.getElementById('file-info');
    const heatmapContainer = document.getElementById('heatmap-container');
    const heatmapImg = document.getElementById('heatmap-img');

    if (!answerImg || !answerText || !answerAccuracy || !answerBlock) {
        console.error('Не найдены элементы для отображения результатов');
        return;
    }

    // Показываем оригинальное изображение
    answerImg.src = result.original_image;
    
    // Добавляем информацию о файле
    if (fileInfo) {
        fileInfo.textContent = `Файл: ${fileName}`;
    }

    // Анализируем результаты
    let accuracy, className;
    const results = result.predictions;
    
    if (results.length >= 2) {
        // Для многоклассовой классификации
        const maxIndex = results.indexOf(Math.max(...results));
        accuracy = results[maxIndex] * 100;
        className = maxIndex === 0 ? 'Есть дифференцировка' : 'Нет дифференцировки';
    } else {
        // Для бинарной классификации
        accuracy = results[0] * 100;
        className = accuracy > 50 ? 'Есть дифференцировка' : 'Нет дифференцировка';
    }

    answerText.textContent = className;
    answerAccuracy.textContent = `Вероятность: ${accuracy.toFixed(2)}%`;
    
    // Показываем heatmap если есть
    if (result.heatmap_image && heatmapContainer && heatmapImg) {
        heatmapImg.src = result.heatmap_image;
        heatmapContainer.style.display = 'block';
        console.log('🔥 Heatmap отображен');
    } else if (heatmapContainer) {
        heatmapContainer.style.display = 'none';
        console.log('ℹ️ Heatmap недоступен');
    }
    
    // Показываем блок с результатами
    answerBlock.style.visibility = 'visible';
    checkAnswerBlockVisibility();
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM загружен, инициализируем приложение...');
    
    const uploadBlock = document.getElementById('uploadBlock');
    const fileInput = document.getElementById('fileInput');
    const loadingMessage = document.getElementById('loadingMessage');

    // Проверяем существование элементов
    if (!uploadBlock || !fileInput) {
        console.error('Не найдены необходимые элементы DOM');
        return;
    }

    // Проверяем доступность API
    checkAPIHealth();

    // Обработчик клика по области загрузки
    uploadBlock.addEventListener('click', () => {
        if (isModelLoaded) {
            fileInput.click();
        } else {
            alert('Модель еще загружается. Пожалуйста, подождите...');
        }
    });
    
    // Обработчик выбора файла
    fileInput.addEventListener('change', async function(e) {
        const file = e.target.files[0];
        if (!file) return;

        // Проверяем тип файла
        const isImage = file.type.startsWith('image/');
        const isTIFF = isTIFFFile(file);
        
        if (!isImage && !isTIFF) {
            alert('Пожалуйста, выберите файл изображения (JPEG, PNG, TIFF, etc.)');
            return;
        }

        if (!isModelLoaded) {
            const isReady = await checkAPIHealth();
            if (!isReady) {
                alert('Сервер недоступен. Убедитесь, что запущен Python сервер.');
                return;
            }
        }

        // Показываем сообщение о загрузке
        if (loadingMessage) {
            loadingMessage.style.display = 'block';
            loadingMessage.textContent = 'Обрабатываем изображение...';
        }

        try {
            let previewSrc;
            
            if (isTIFF) {
                console.log('🖼️ Обнаружен TIFF файл, используем заглушку для превью');
                previewSrc = createTIFFPreview();
            } else {
                // Для других форматов создаем превью из файла
                previewSrc = URL.createObjectURL(file);
            }

            // Обрабатываем изображение моделью
            const result = await processImage(file);
            displayResults(result, file.name);
            
        } catch (error) {
            console.error('Ошибка обработки:', error);
            alert('Ошибка при обработке изображения: ' + error.message);
        } finally {
            // Скрываем сообщение о загрузке
            if (loadingMessage) {
                loadingMessage.style.display = 'none';
            }
        }
    });

    // Drag and drop функциональность
    uploadBlock.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadBlock.classList.add('drag-over');
    });

    uploadBlock.addEventListener('dragleave', () => {
        uploadBlock.classList.remove('drag-over');
    });

    uploadBlock.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadBlock.classList.remove('drag-over');
        
        const file = e.dataTransfer.files[0];
        if (file && (file.type.startsWith('image/') || isTIFFFile(file))) {
            // Создаем новый FileList
            const dt = new DataTransfer();
            dt.items.add(file);
            fileInput.files = dt.files;
            fileInput.dispatchEvent(new Event('change'));
        } else {
            alert('Пожалуйста, перетащите изображение (JPEG, PNG, TIFF)');
        }
    });

    // Начальная проверка видимости
    checkAnswerBlockVisibility();
});