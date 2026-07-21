pipeline {
    agent any

    environment {
        // Retrieve credentials configured in Jenkins
        GITHUB_CREDS = credentials('github-credentials-id')
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Update CSV & Push') {
            steps {
                script {
                    // Update the remote URL with embedded PAT for push permissions
                    sh '''
                        git remote set-url origin https://${GITHUB_CREDS_USR}:${GITHUB_CREDS_PSW}@github.com/${GIT_KEY}.git
                    '''
                    
                    // Run Python automation script
                    sh 'python3 append_csv.py'
                }
            }
        }
    }

    post {
        always {
            cleanWs() // Clean up workspace after run
        }
    }
}
