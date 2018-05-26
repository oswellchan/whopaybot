#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [ ! -f $DIR/../.env ]
  then
    echo "\".env\" file not found in root project directory. Create one then run setup.sh again."
    exit 1
fi

export $(egrep -v '^#' .env | xargs)

if [ -f $DIR/../web.env ]
  then
    rm -rf $DIR/../web.env
fi
cp $DIR/../.env $DIR/../web.env
echo "DB_HOST=db" >> $DIR/../web.env
echo "DB_NAME=whopay" >> $DIR/../web.env
echo "DB_PORT=5432" >> $DIR/../web.env

if [ -f $DIR/../db.env ]
  then
    rm -rf $DIR/../db.env
fi
echo "POSTGRES_USER=${DB_USER}" >> $DIR/../db.env
echo "POSTGRES_PASSWORD=${DB_PASS}" >> $DIR/../db.env
echo "POSTGRES_DB=whopay" >> $DIR/../db.env

docker-compose up --build -d

# Might break if other db services running?
CONTAINER_ID=$(docker-compose ps -q db)
CONTAINER_NAME=$(docker ps --format "{{.Names}}" -af "id=$CONTAINER_ID")

docker exec $CONTAINER_ID mkdir /migrations
docker cp $DIR/../migrations $CONTAINER_NAME:/.
for filepath in $DIR/../migrations/*.sql; do
  filename=$(basename $filepath)
  PGPASSWORD=$POSTGRES_PASSWORD docker exec $CONTAINER_ID psql -h localhost --username=$POSTGRES_USER --dbname=whopay -a -f /migrations/$filename > /dev/null 2>&1
done

