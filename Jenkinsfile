pipeline {
    agent any

    stages {
        stage('Frontend Checks') {
            steps {
                dir('frontend') {
                    sh 'npm ci'
                    sh 'npm run lint'
                    sh 'npm run build'
                }
            }
        }

        stage('Backend Checks') {
            steps {
                dir('backend/django_backend') {
                    sh '''
                        python3 -m venv .venv
                        . .venv/bin/activate
                        python -m pip install --upgrade pip
                        pip install -r requirements.txt
                        python manage.py check
                        python manage.py spectacular --validate --file /tmp/insurex-openapi-schema.yml
                        python manage.py test
                    '''
                }
            }
        }
    }
}
