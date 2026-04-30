pipeline {
    agent any
    
    parameters {
        string(name: 'ODOO_TEST_RUN_ID', defaultValue: '', description: 'ID du Test Run envoyé par Odoo')
    }

    stages {
        stage('Install Dependencies') {
            steps {
                // Ajout de --no-input pour éviter le blocage sur Windows
                bat 'python -m pip install --upgrade pip --no-input'
                bat 'python -m pip install --no-cache-dir --progress-bar off --no-input -r requirements.txt'
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
            
            // On force l'ID dans l'environnement pour send_results.py
            withEnv(["ODOO_TEST_RUN_ID=${params.ODOO_TEST_RUN_ID}"]) {
                bat 'python send_results.py'
            }
        }
    }
}