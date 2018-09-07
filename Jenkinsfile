// JOB_BASE_NAME is not reliably available in Multibranch Pipeline
def clientName = "ingest-samples-json"
pipeline {
    agent any
    options {
        disableConcurrentBuilds()
    }
    environment {
        ACTOR_ID_PROD     = '5DmaBb07qKNXr'
        ACTOR_ID_STAGING  = 'D0bvrrM4qLwgr'
        PYTEST_OPTS       = '-s -vvv'
        ABACO_DEPLOY_OPTS = ''
        CI                = "true"
        AGAVE_CACHE_DIR   = "${HOME}/credentials_cache/${clientName}"
        AGAVE_JSON_PARSER = "jq"
        AGAVE_TENANTID    = "sd2e"
        AGAVE_APISERVER   = "https://api.sd2e.org"
        AGAVE_USERNAME    = credentials('sd2etest-tacc-username')
        AGAVE_PASSWORD    = credentials('sd2etest-tacc-password')
        REGISTRY_USERNAME = "sd2etest"
        REGISTRY_PASSWORD = credentials('sd2etest-dockerhub-password')
        REGISTRY_ORG      = credentials('sd2etest-dockerhub-org')
        PATH = "${HOME}/bin:${HOME}/sd2e-cloud-cli/bin:${env.PATH}"
        SECRETS_FILE = credentials('etl-pipeline-support-secrets-json')
        SECRETS_FILE_STAGING = credentials('etl-pipeline-support-secrets-json')
        CONFIG_LOCAL_FILE = credentials('etl-pipeline-support-config-local-yml')
        CONFIG_LOCAL_FILE = credentials('etl-pipeline-support-config-local-yml')
        }
    stages {
        stage('Build from master') {
            when {
                branch 'master'
            }
            steps {
                sh "get-job-client ${clientName}-${BRANCH_NAME} ${BUILD_ID}"
                sh "cat ${SECRETS_FILE} > secrets.json"
                sh "cat ${CONFIG_LOCAL_FILE} > config-local.yml"
                sh "make clean || true"
                sh "make image"
            }
        }
        stage('Build from develop') {
            when {
                branch 'develop'
            }
            steps {
                sh "get-job-client ${clientName}-${BRANCH_NAME} ${BUILD_ID}"
                sh "cat ${SECRETS_FILE_STAGING} > secrets.json"
                sh "cat ${CONFIG_LOCAL_FILE_STAGING} > config-local.yml"
                sh "make clean || true"
                sh "make image"
            }
        }
        stage('Run integration tests') {
            steps {
                sh "NOCLEANUP=1 make tests-integration"
            }
        }
        stage('Deploy to staging') {
            when {
                branch 'develop'
            }
            environment {
                AGAVE_USERNAME    = 'sd2eadm'
                AGAVE_PASSWORD    = credentials('sd2eadm-password')
            }
            steps {
                script {
                    sh "get-job-client ${clientName}-deploy ${BUILD_ID}"
                    reactorName = sh(script: 'cat reactor.rc | egrep -e "^REACTOR_NAME=" | sed "s/REACTOR_NAME=//"', returnStdout: true).trim()
                    sh(script: "abaco deploy -U ${ACTOR_ID_STAGING}", returnStdout: false)
                    // TODO - update alias
                    println("Deployed ${reactorName}:staging with actorId ${ACTOR_ID_STAGING}")
                    slackSend ":tacc: Deployed *${reactorName}:staging* with actorId *${ACTOR_ID_STAGING}*"
                }
            }
        }
        stage('Deploy to production') {
            when {
                branch 'master'
            }
            environment {
                AGAVE_USERNAME    = 'sd2eadm'
                AGAVE_PASSWORD    = credentials('sd2eadm-password')
            }
            steps {
                script {
                    sh "get-job-client ${clientName}-deploy ${BUILD_ID}"
                    reactorName = sh(script: 'cat reactor.rc | egrep -e "^REACTOR_NAME=" | sed "s/REACTOR_NAME=//"', returnStdout: true).trim()
                    sh(script: "abaco deploy -U ${ACTOR_ID_PROD}", returnStdout: false)
                    // TODO - update alias
                    println("Deployed ${reactorName}:production with actorId ${ACTOR_ID_PROD}")
                    slackSend ":tacc: Deployed *${reactorName}:prod* with actorId *${ACTOR_ID_PROD}*"
                }
            }
        }
    }
    post {
        always {
            sh "release-job-client ${clientName}-${BRANCH_NAME} ${BUILD_ID}"
            sh "release-job-client ${clientName}-deploy ${BUILD_ID}"
            archiveArtifacts artifacts: 'input, output, create_mapped_name_failures.csv', fingerprint: true, excludes: 'secrets.json', allowEmptyArchive: true
            deleteDir()
        }
        success {
            slackSend ":white_check_mark: *${env.JOB_NAME}/${env.BUILD_NUMBER}* completed"
            emailext (
                    subject: "${env.JOB_NAME}/${env.BUILD_NUMBER} completed",
                    body: """<p>Build: ${env.BUILD_URL}</p>""",
                    recipientProviders: [[$class: 'DevelopersRecipientProvider']],
                    replyTo: "jenkins@sd2e.org",
                    from: "jenkins@sd2e.org"
            )
        }
        failure {
            slackSend ":bomb: *${env.JOB_NAME}/${env.BUILD_NUMBER}* failed"
            emailext (
                    subject: "${env.JOB_NAME}/${env.BUILD_NUMBER} failed",
                    body: """<p>Build: ${env.BUILD_URL}</p>""",
                    recipientProviders: [[$class: 'DevelopersRecipientProvider']],
                    replyTo: "jenkins@sd2e.org",
                    from: "jenkins@sd2e.org"
            )
        }
    }
}
