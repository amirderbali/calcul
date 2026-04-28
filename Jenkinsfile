pipeline {
    agent any
    
    stages {
        stage('Checkout') {
            steps {
                // Utilisation des identifiants GitHub pour éviter les erreurs de permission
                git branch: 'main', 
                    credentialsId: 'github-credentials', 
                    url: 'https://github.com/amirderbali/calcul.git'
            }
        }

        stage('Install Dependencies') {
            steps {
                // Utilisation de python -m pip pour plus de stabilité sur Windows
                bat 'python -m pip install -r requirements.txt'
            }
        }

        stage('Run Tests') {
            steps {
                // ON LANCE calculatrice.py car c'est lui qui contient les "def test_..."
                bat 'pytest calculatrice.py --junitxml=results.xml -v'
            }
            post {
                always {
                    junit 'results.xml'
                }
            }
        }

        stage('Send Results to Test Management') {
            steps {
                bat 'python send_results.py'
            }
        }
    }
}
