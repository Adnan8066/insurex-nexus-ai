pipeline {
    agent any

    stages {
        stage('Frontend Checks') {
            steps {
                dir('frontend') {
                    bat 'npm ci'
                    bat 'npm run lint'
                    bat 'npm run build'
                }
            }
        }

        stage('Backend Checks') {
            steps {
                dir('backend\\django_backend') {
                    bat 'py -3.12 -m venv .venv'
                    bat '.venv\\Scripts\\python.exe -m pip install --upgrade pip'
                    bat '.venv\\Scripts\\python.exe -m pip install -r requirements.txt'
                    bat '.venv\\Scripts\\python.exe manage.py check'
                    bat '.venv\\Scripts\\python.exe manage.py spectacular --validate --file "%TEMP%\\insurex-openapi-schema.yml"'
                    bat '.venv\\Scripts\\python.exe manage.py test'
                }
            }
        }
    }
}