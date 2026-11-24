pipeline {
    agent any

    environment {
        PYTHONHASHSEED = '42'
        OMP_NUM_THREADS = '1'
        MKL_NUM_THREADS = '1'
        OPENBLAS_NUM_THREADS = '1'
    }

    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
        timestamps()
        timeout(time: 120, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
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
                    bat 'npm audit --audit-level=high'
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
                    bat '.venv\\Scripts\\python.exe -m pip install pip-audit'
                    bat '.venv\\Scripts\\python.exe -m pip freeze > ..\\ml\\models\\python_environment.txt'
                    bat '.venv\\Scripts\\python.exe -m ruff check apps common config'
                    bat '.venv\\Scripts\\pip-audit.exe -r requirements.txt'
                    bat '.venv\\Scripts\\python.exe manage.py check'
                    bat '.venv\\Scripts\\python.exe manage.py spectacular --validate --file "%TEMP%\\insurex-openapi-schema.yml"'
                    withEnv(['DJANGO_SETTINGS_MODULE=config.settings']) {
                        bat '.venv\\Scripts\\coverage.exe run --source=apps -m pytest --junitxml=TEST-django.xml'
                    }
                    bat '.venv\\Scripts\\coverage.exe report -m --fail-under=0'
                    bat '.venv\\Scripts\\coverage.exe xml -o coverage.xml'
                }
            }
            post {
                always {
                    script {
                        if (fileExists('backend/django_backend/TEST-django.xml')) {
                            junit testResults: 'backend/django_backend/TEST-django.xml'
                        }
                    }
                    archiveArtifacts artifacts: 'backend/django_backend/coverage.xml', allowEmptyArchive: true
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

        stage('Validate Training Data') {
            steps {
                dir('backend\\django_backend') {
                    bat '.venv\\Scripts\\python.exe manage.py mlops_ci_check --phase data'
                }
            }
        }

        stage('Bundled Data Shift Diagnostic') {
            steps {
                dir('backend\\django_backend') {
                    bat '.venv\\Scripts\\python.exe manage.py mlops_ci_check --phase drift'
                }
            }
        }

        stage('Train ML Models') {
            steps {
                dir('backend\\django_backend') {
                    // Interim: trains on the original US-dollar files in backend/data/ until the
                    // models move to Lumora features (docs/US_MIGRATION_PLAN.md, Phase 3).
                    bat '.venv\\Scripts\\python.exe manage.py train_project_models'
                    bat '.venv\\Scripts\\python.exe manage.py mlops_ci_check --phase explainability'
                }
            }
        }

        stage('Model Quality Gates and Manifest') {
            steps {
                dir('backend\\django_backend') {
                    bat '.venv\\Scripts\\python.exe manage.py mlops_ci_check --phase quality'
                }
            }
            post {
                always {
                    archiveArtifacts artifacts: 'backend/ml/models/*.joblib,backend/ml/models/*.json,backend/ml/models/*.txt,backend/ml/models/fraud_oracle_evaluation.png', allowEmptyArchive: true, fingerprint: true
                }
            }
        }
    }
}
