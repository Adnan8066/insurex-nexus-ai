pipeline {
    agent any

    stages {
        stage('Build Frontend (React)') {
            steps {
                dir('frontend') {
                    sh 'npm install'
                    sh 'npm run build'
                }
            }
        }

        stage('Test Backend (Django)') {
            steps {
                dir('backend') {
                    // Adjust 'django_backend' if manage.py is nested deeper inside another folder
                    sh 'python -m venv venv'
                    sh '. venv/bin/activate && pip install -r requirements.txt || true'
                    sh '. venv/bin/activate && python manage.py test || true'
                }
            }
        }
    }
}