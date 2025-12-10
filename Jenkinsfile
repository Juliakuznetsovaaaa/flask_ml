pipeline {
    agent any
    
    parameters {
        choice(
            name: 'DEPLOYMENT_STRATEGY',
            choices: ['blue-green', 'canary', 'rolling'],
            description: 'Стратегия деплоя'
        )
        booleanParam(
            name: 'VALIDATE_MODEL',
            defaultValue: true,
            description: 'Валидировать ML модель'
        )
        booleanParam(
            name: 'AUTO_ROLLBACK',
            defaultValue: true,
            description: 'Автоматический откат при проблемах'
        )
    }
    
    environment {
        APP_NAME = 'flask-ml-app'
        DOCKER_REGISTRY = 'registry.example.com'
        DOCKER_IMAGE = "${DOCKER_REGISTRY}/${APP_NAME}"
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Test ML Model') {
            steps {
                script {
                    echo 'Запуск тестов ML модели...'
                    sh 'python tests/test_model.py'
                }
            }
        }
        
        stage('Build Docker Image') {
            steps {
                script {
                    echo 'Сборка Docker образа...'
                    sh 'docker build -t ${DOCKER_IMAGE}:${BUILD_ID} .'
                    sh 'docker tag ${DOCKER_IMAGE}:${BUILD_ID} ${DOCKER_IMAGE}:latest'
                }
            }
        }
        
        stage('Push to Registry') {
            steps {
                script {
                    echo 'Загрузка образа в registry...'
                    withCredentials([usernamePassword(
                        credentialsId: 'docker-registry',
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_PASS'
                    )]) {
                        sh 'docker login -u $DOCKER_USER -p $DOCKER_PASS ${DOCKER_REGISTRY}'
                        sh 'docker push ${DOCKER_IMAGE}:${BUILD_ID}'
                        sh 'docker push ${DOCKER_IMAGE}:latest'
                    }
                }
            }
        }
        
        stage('Blue-Green Deployment') {
            steps {
                script {
                    echo 'Запуск Blue-Green деплоя...'
                    sh """
                    python blue_green_deploy.py \
                        --strategy ${params.DEPLOYMENT_STRATEGY} \
                        --validate ${params.VALIDATE_MODEL} \
                        --auto-rollback ${params.AUTO_ROLLBACK}
                    """
                }
            }
            post {
                success {
                    echo 'Деплой успешно завершен'
                    slackSend(
                        color: 'good',
                        message: "Деплой ${APP_NAME} успешно завершен (Build: ${BUILD_ID})"
                    )
                }
                failure {
                    echo 'Деплой завершен с ошибками'
                    slackSend(
                        color: 'danger',
                        message: "Деплой ${APP_NAME} провален (Build: ${BUILD_ID})"
                    )
                }
            }
        }
        
        stage('Post-Deployment Tests') {
            steps {
                script {
                    echo 'Запуск пост-деплойных тестов...'
                    sh 'python tests/post_deploy_validation.py'
                }
            }
        }
    }
    
    post {
        always {
            echo 'Очистка рабочих пространств...'
            cleanWs()
        }
    }
}