pipeline {
    agent any
    stages {
        stage('Installation') {
            steps {
                bat 'pip install -r requirements.txt'
            }
        }
        stage('Test Python') {
            steps {
                // Lance les tests. Cela va échouer exprès à cause de ton bug (5-3=1)
                bat 'python -m unittest test.py'
            }
        }
        stage('Sync Odoo') {
            steps {
                // Envoie les résultats vers ton module Odoo
                bat 'python send_results.py'
            }
        }
    }
}
