pipeline {
    agent any
    parameters {
        // C'est ici qu'on définit le paramètre reçu d'Odoo
        string(name: 'TESTE', defaultValue: '', description: 'ID du Test Run envoyé par Odoo')
    }

    environment {
        // On expose l'ID d'Odoo comme variable d'environnement pour les scripts Python
        ODOO_TEST_ID = "${params.TESTE}"
    }

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
