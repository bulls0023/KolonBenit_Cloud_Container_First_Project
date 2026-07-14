pipeline {
    agent any

    environment {
        HARBOR_REGISTRY = "10.10.1.120"
        IMAGE_NAME      = "hospital/was-app"
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.GIT_SHORT_SHA = sh(script: "git rev-parse --short HEAD", returnStdout: true).trim()
                    env.IMAGE_TAG = "${HARBOR_REGISTRY}/${IMAGE_NAME}:${env.GIT_SHORT_SHA}"

                    def commitMsg = sh(script: "git log -1 --pretty=%B", returnStdout: true).trim()
                    if (commitMsg.contains('[skip ci]')) {
                        echo "Commit message contains the CI-skip marker, aborting pipeline to prevent loop."
                        currentBuild.result = 'NOT_BUILT'
                        error("Skipping build due to CI-skip marker.")
                    }
                }
            }
        }

        stage('Build Image') {
            steps {
                sh "docker build -t ${env.IMAGE_TAG} ./app"
            }
        }

        stage('Trivy Scan') {
            steps {
                sh """
                    docker run --rm \
                        -v /var/run/docker.sock:/var/run/docker.sock \
                        -v /opt/trivy-cache:/root/.cache/ \
                        aquasec/trivy:0.72.0 image \
                        --exit-code 0 \
                        --severity CRITICAL,HIGH \
                        ${env.IMAGE_TAG}
                """
                // TODO: 파이프라인 전체 검증 끝나면 --exit-code 1 로 전환 (CRITICAL/HIGH 발견 시 빌드 중단)
            }
        }

        stage('Push to Harbor') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'harbor-credentials', usernameVariable: 'HARBOR_USER', passwordVariable: 'HARBOR_PASS')]) {
                    sh '''
                        echo "$HARBOR_PASS" | docker login "$HARBOR_REGISTRY" -u "$HARBOR_USER" --password-stdin
                        docker push "$IMAGE_TAG"
                    '''
                }
            }
        }

        stage('Update Manifest & Push') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'gitlab-credentials', usernameVariable: 'GIT_USER', passwordVariable: 'GIT_PASS')]) {
                    sh '''
                        sed -i "s#image: ${HARBOR_REGISTRY}/${IMAGE_NAME}:.*#image: ${IMAGE_TAG}#" k8s/20-was-deployment.yaml
                        git config user.email "jenkins@devops.local"
                        git config user.name "Jenkins CI"
                        git add k8s/20-was-deployment.yaml
                        git commit -m "Update was-app image to ${GIT_SHORT_SHA} [skip ci]" || echo "No changes to commit"
                        git push "http://${GIT_USER}:${GIT_PASS}@10.10.1.125:8929/hospital/hospital-reservation.git" HEAD:main
                    '''
                }
            }
        }
    }

    post {
        always {
            sh 'docker logout "$HARBOR_REGISTRY" || true'
        }
    }
}
