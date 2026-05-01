pipeline {
    agent any
    
    parameters {
        string(name: 'ODOO_TEST_RUN_ID', defaultValue: '', description: 'ID du Test Run envoyé par Odoo')
    }

    stages {
        stage('Install Dependencies') {
            steps {
                bat 'python --version'
                bat 'python -m pip --version'
                bat 'python -m pip install --no-cache-dir --progress-bar off -r requirements.txt'
            }
        }
        
        stage('Run Tests') {
            steps {
                catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
                    bat 'pytest calculatrice.py --junitxml=results.xml -v'
                }
            }
        }
    }
    
    post {
        always {
            script {
                if (fileExists('results.xml')) {
                    junit 'results.xml'
                }
            }
            echo "Envoi des résultats vers Odoo pour le Run ID: ${params.ODOO_TEST_RUN_ID}"
            
            withEnv(["ODOO_TEST_RUN_ID=${params.ODOO_TEST_RUN_ID}"]) {
                bat 'python send_results.py'
            }
        }
    }
}