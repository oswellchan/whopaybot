#!/bin/bash
set -e

# Might break if other web services running?
CONTAINER_ID=$(docker-compose ps -q web)
CONTAINER_NAME=$(docker ps --format "{{.Names}}" -af "id=$CONTAINER_ID")

docker logs -f $CONTAINER_ID
