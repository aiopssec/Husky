#!/bin/sh

set -o nounset
set -o errexit
set -o pipefail

function try() {
    echo "$@"
    eval "$@"
}

function prepare_git() {
    try [ -d ${WORKSPACE} ] || git clone -q "${REPO}" "${WORKSPACE}"
    try git -C ${WORKSPACE} clean -dfx
    try git -C ${WORKSPACE} reset --hard HEAD
    try git -C ${WORKSPACE} checkout -q $(git -C ${WORKSPACE} rev-parse HEAD)
    try git -C ${WORKSPACE} fetch -q -p -t origin
    if git -C ${WORKSPACE} show-ref -q --verify refs/heads/${REF}; then
        try git -C ${WORKSPACE} branch -D ${REF}
    fi
    try cd ${WORKSPACE}
    try git checkout -q ${REF}
    try ID=$(git rev-parse --short HEAD)
}

function build() {
    case $PROJS_NAME in
        apollo|gaea)
            try mvn -T 2C clean install -f ${WORKSPACE}/pom.xml -Drepository.env=real -Dmaven.test.skip=true -Dmaven.compile.fork=true &&
            try mv -f ${WORKSPACE}/target/*.jar /dockerfiles/${PROJS_NAME}/app.jar
            ;;
        venus)
            if [ -d /dockerfiles/${PROJS_NAME}/dist ]; then
                try rm -rf /dockerfiles/${PROJS_NAME}/dist
            fi
            try cd ${WORKSPACE}
            try cnpm install &&
            try npm run build &&
            try mv -f dist /dockerfiles/${PROJS_NAME}/dist
            ;;
        zeus)
            try mvn -T 2C clean install -f ${WORKSPACE}/pom.xml -Drepository.env=real -Dmaven.test.skip=true -Dmaven.compile.fork=true &&
            try mv -f ${WORKSPACE}/webapp/target/*.jar /dockerfiles/${PROJS_NAME}/app.jar
            ;;
    esac
}

function build_docker() {
    try cd /dockerfiles/${PROJS_NAME}
    try docker build -t ${TAG}-${ID} . &&
    try docker push ${TAG}-${ID} &&
    try docker rmi ${TAG}-${ID}
}

function assignment() {
    TAG=$1
    PROJS_NAME=$2
    WORKSPACE="/husky/$PROJS_NAME"
    REF=$3
    REPO=$4
    eval "prepare_git"
    eval "build"
    eval "build_docker"
}

assignment $1 $2 $3 $4
