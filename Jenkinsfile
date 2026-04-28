pipeline {
    agent any
    stages {
        stage('Checkout') {
            steps {
                git branch: 'main', credentialsId: 'github-credentials', url: 'https://github.com/amirderbali/calcul.git'
            }
        }
        stage('Install Dependencies') {
            steps {
                bat 'python -m pip install -r requirements.txt'
            }
        }
        stage('Run Tests') {
            steps {
                // On ajoute "catchError" ici pour que le build ne soit pas stoppé net
                catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
                    bat 'pytest calculatrice.py --junitxml=results.xml -v'
                }
            }
        }
    }
    // CE BLOC EST À L'EXTÉRIEUR DES STAGES
    post {
        always {
            junit 'results.xml'
            echo "Envoi des résultats vers Odoo..."
            bat 'python send_results.py'
        }
    }
}