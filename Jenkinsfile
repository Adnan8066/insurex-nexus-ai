pipeline {
    agent any

    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
    }

    stages {
        stage('Checkout') {
            steps {
                retry(3) {
                    script {
                        try {
                            deleteDir()
                            checkout scm
                        } catch (err) {
                            sleep time: 5, unit: 'SECONDS'
                            throw err
                        }
                    }
                }
            }
        }

        stage('Frontend Checks') {
            steps {
                dir('frontend') {
                    retry(3) {
                        script {
                            try {
                                bat 'npm ci'
                            } catch (err) {
                                sleep time: 5, unit: 'SECONDS'
                                throw err
                            }
                        }
                    }
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
