#!/bin/bash

docker build -t husky .
docker stop husky
docker rm husky
docker run -d --name husky -p 443:443 -e DB_HOST=192.168.10.10 -v /var/run/docker.sock:/var/run/docker.sock --restart=always husky
