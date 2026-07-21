pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Update CSV & Push') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'github-credentials-id', usernameVariable: 'GITHUB_USER', passwordVariable: 'GITHUB_PAT')]) {
            script {
                bat '''
                    @echo off
                    rem Reconfigure remote origin with credentials
                    git config --get remote.origin.url > temp.txt
                    set /p RAW_URL=<temp.txt
                    del temp.txt

                    rem Update git URL safely
                    git remote set-url origin "https://%GITHUB_USER%:%GITHUB_PAT%@github.com/YOUR_USER/YOUR_REPO.git"
                    
                    rem Use the absolute path to python.exe
                    "C:\\Users\\YourUser\\AppData\\Local\\Programs\\Python\\Python311\\python.exe" append_csv.py
                '''
                    }
                }
            }
        }
    }

    post {
        always {
            script {
                if (getContext(hudson.FilePath)) {
                    cleanWs()
                }
            }
        }
    }
}
