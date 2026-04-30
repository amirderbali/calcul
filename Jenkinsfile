pipeline {
    agent any
    stages {
        // 1. Suppression du stage 'Checkout' manuel (Jenkins le fait déjà tout seul)
        
        stage('Install Dependencies') {
            steps {
                // Utilisation de --progress-bar off pour éviter de saturer la console Jenkins
                bat 'python -m pip install --upgrade pip'
                bat 'python -m pip install --no-cache-dir --progress-bar off -r requirements.txt'
            }
        }
        
        stage('Run Tests') {
            steps {
                catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
                    // Utilisation de l'ID Odoo si vous l'avez passé en paramètre (optionnel)
                    bat 'pytest calculatrice.py --junitxml=results.xml -v'
                }
            }
        }
    }
    
    post {
        always {
            // Vérifie si le fichier existe avant de tenter l'envoi
            script {
                if (fileExists('results.xml')) {
                    junit 'results.xml'
                }
            }
            echo "Envoi des résultats vers Odoo..."
            bat 'python send_results.py'
        }
    }
}