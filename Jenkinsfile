pipeline {
    agent any

    options {
        skipDefaultCheckout()
        disableConcurrentBuilds()
        timestamps()
    }

    triggers {
        githubPush()
    }

    environment {
        CONTAINER = 'midterm-sp23-bai-043'
        DOCKER_HUB_IMAGE = 'ramish52843/midterm-sp23-bai-043:latest'
    }

    stages {
        stage('Checkout latest data') {
            steps {
                checkout scm
                script {
                    env.MODEL_SHA = sh(script: 'git rev-parse HEAD', returnStdout: true).trim()
                    env.MODEL_IMAGE = "${env.CONTAINER}:${env.MODEL_SHA}"
                    def commitEmails = sh(
                        script: '''git show -s --format='%ce%n%ae' "$MODEL_SHA"''',
                        returnStdout: true
                    ).readLines()
                    env.COMMIT_EMAIL = commitEmails.find { email ->
                        email ==~ /[A-Za-z0-9.!_%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/ &&
                            !email.toLowerCase().endsWith('@users.noreply.github.com') &&
                            !email.equalsIgnoreCase('noreply@github.com')
                    } ?: ''
                    env.EXPECTED_ROWS = sh(
                        script: '''awk 'END { print NR - 1 }' dataset/train.csv''',
                        returnStdout: true
                    ).trim()
                }
            }
        }

        stage('Train and build Docker image') {
            steps {
                sh 'docker build --build-arg GIT_COMMIT="$MODEL_SHA" -t "$MODEL_IMAGE" .'
            }
        }

        stage('Test metrics and prediction') {
            steps {
                sh '''
                    set -eu
                    candidate=$(docker run -d "$MODEL_IMAGE")
                    trap 'docker rm -f "$candidate" >/dev/null' EXIT
                    docker exec "$candidate" python smoke_test.py "$MODEL_SHA" "$EXPECTED_ROWS"
                '''
            }
        }

        stage('Deploy to EC2 port 8000') {
            steps {
                sh '''
                    set -eu
                    previous=
                    if docker container inspect "$CONTAINER" >/dev/null 2>&1; then
                        previous=$(docker inspect --format '{{.Id}}' "$CONTAINER")
                        docker rename "$previous" "$CONTAINER-backup-$BUILD_NUMBER"
                        docker stop -t 5 "$previous"
                    fi

                    if docker run -d --restart unless-stopped --name "$CONTAINER" \
                        -p 8000:8000 "$MODEL_IMAGE" &&
                        docker exec "$CONTAINER" python smoke_test.py "$MODEL_SHA" "$EXPECTED_ROWS"; then
                        if [ -n "$previous" ]; then
                            docker rm "$previous"
                        fi
                    else
                        docker logs "$CONTAINER" 2>/dev/null || true
                        docker rm -f "$CONTAINER" 2>/dev/null || true
                        if [ -n "$previous" ]; then
                            docker rename "$previous" "$CONTAINER"
                            docker start "$previous"
                        fi
                        exit 1
                    fi
                '''
            }
        }

        stage('Publish Docker Hub image') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-sp23-bai-043',
                    usernameVariable: 'DOCKER_HUB_USER',
                    passwordVariable: 'DOCKER_HUB_TOKEN'
                )]) {
                    sh '''
                        set +x
                        set -eu
                        DOCKER_CONFIG=$(mktemp -d)
                        export DOCKER_CONFIG
                        trap 'rm -rf "$DOCKER_CONFIG"' EXIT
                        printf '%s\n' "$DOCKER_HUB_TOKEN" |
                            docker login --username "$DOCKER_HUB_USER" --password-stdin
                        docker tag "$MODEL_IMAGE" "$DOCKER_HUB_IMAGE"
                        docker push "$DOCKER_HUB_IMAGE"
                    '''
                }
            }
        }
    }

    post {
        always {
            script {
                if (env.COMMIT_EMAIL) {
                    emailext(
                        to: env.COMMIT_EMAIL,
                        subject: "SP23-BAI-043 | ${currentBuild.currentResult} | Build #${env.BUILD_NUMBER}",
                        body: """Build: ${env.BUILD_URL}
Git commit: ${env.MODEL_SHA ?: 'unavailable'}
Training rows: ${env.EXPECTED_ROWS ?: 'unavailable'}
Status: ${currentBuild.currentResult}
Docker Hub tag: ${env.DOCKER_HUB_IMAGE}"""
                    )
                } else {
                    echo 'No deliverable email address was found on the built commit.'
                }
            }
        }
    }
}
