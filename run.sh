#!/bin/bash

docker build -t husky .
docker stop husky
docker rm husky
docker run -d --name husky -p 80:80 -e DB_HOST=192.168.8.112 -v /var/run/docker.sock:/var/run/docker.sock --restart=always husky