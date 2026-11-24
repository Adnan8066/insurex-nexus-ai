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
                    bat 'py -3.12 --version'
                    bat 'py -3.12 -m venv .venv'
                    bat '.venv\\Scripts\\python.exe -m pip install --upgrade pip'
                    bat '.venv\\Scripts\\python.exe -m pip install -r requirements.txt'
                    bat '.venv\\Scripts\\python.exe manage.py check'
                    bat '.venv\\Scripts\\python.exe manage.py spectacular --validate --file "%TEMP%\\insurex-openapi-schema.yml"'
                    bat '.venv\\Scripts\\python.exe manage.py test'
                }
            }
        }

        stage('RL Routing Tests') {
            steps {
                dir('backend') {
                    // Reuses the backend venv (gymnasium, stable-baselines3, torch, pytest).
                    bat 'django_backend\\.venv\\Scripts\\python.exe -m pytest rl\\tests -q -p no:cacheprovider'
                }
            }
        }

        stage('Generate US Sample Data') {
            steps {
                dir('backend\\data\\us') {
                    // Lumora synthetic US book (50K policy terms), regenerated from the fixed seed in
                    // config.yaml so every build gets identical data. Generated files are not committed.
                    bat 'py -3.12 -m venv .venv'
                    bat '.venv\\Scripts\\python.exe -m pip install --upgrade pip'
                    bat '.venv\\Scripts\\python.exe -m pip install -r requirements.txt'
                    bat '.venv\\Scripts\\python.exe -m motorsynth.generate config.yaml --terms 50000 --out sample'
                    bat '.venv\\Scripts\\python.exe checks.py sample'
                }
            }
            post {
                success {
                    archiveArtifacts artifacts: 'backend/data/us/sample/VALIDATION.md,backend/data/us/sample/STORY.md', fingerprint: true
                }
            }
        }

        stage('Train ML Models') {
            steps {
                dir('backend\\django_backend') {
                    // Interim: trains on the original US-dollar files in backend/data/ until the
                    // models move to Lumora features (docs/US_MIGRATION_PLAN.md, Phase 3).
                    bat '.venv\\Scripts\\python.exe manage.py train_project_models'
                }
            }
            post {
                success {
                    archiveArtifacts artifacts: 'backend/ml/models/*.joblib,backend/ml/models/training_report.json,backend/ml/models/fraud_oracle_evaluation.png', fingerprint: true
                }
            }
        }
    }
}
