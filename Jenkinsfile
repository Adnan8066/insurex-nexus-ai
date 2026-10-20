pipeline {
    agent any
<<<<<<< HEAD
 
=======

>>>>>>> 119704a7a711943a9ae0da29a0ea6125a5eb65ca
    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
    }
<<<<<<< HEAD
 
=======

>>>>>>> 119704a7a711943a9ae0da29a0ea6125a5eb65ca
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
<<<<<<< HEAD
 
=======

>>>>>>> 119704a7a711943a9ae0da29a0ea6125a5eb65ca
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
                    bat 'python3 --version'
                    bat 'python3 -m venv .venv'
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
