#!/bin/bash

docker rm $(docker ps -a -q)
docker rmi $(docker image ls -q)
docker volume rm $(docker volume ls -q)