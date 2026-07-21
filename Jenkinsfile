pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                // Check out source code from your configured Git repository
                checkout scm
            }
        }

        stage('Update CSV & Push') {
            steps {
                // Use withCredentials to securely handle Git authentication
                withCredentials([usernamePassword(credentialsId: 'github-credentials-id', usernameVariable: 'GITHUB_USER', passwordVariable: 'GITHUB_PAT')]) {
                    script {
                        // Dynamically pull the repo path (e.g. username/repo.git) from the checked-out Git config
                        sh '''
                            REPO_URL=$(git config --get remote.origin.url | sed -E 's|https://[^@]+@||; s|https://||; s|git@github.com:|github.com/|')
                            git remote set-url origin "https://${GITHUB_USER}:${GITHUB_PAT}@${REPO_URL}"
                            
                            # Run Python automation script
                            python3 append_csv.py
                        '''
                    }
                }
            }
        }
    }

    post {
        always {
            script {
                // Safely clean workspace only if an active agent/workspace context exists
                if (getContext(hudson.FilePath)) {
                    cleanWs()
                }
            }
        }
    }
}
