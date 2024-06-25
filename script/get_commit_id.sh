#!/bin/sh
PROJS_NAME=$1
WORKSPACE="/workspace/$PROJS_NAME"
cd ${WORKSPACE}
echo $(git rev-parse --short HEAD)
