#!/bin/bash
set -e

DB_CONTAINER_NAME=whopay_db
BOT_CONTAINER_NAME=whopay_bot

{
  docker inspect -f {{.State.Running}} $BOT_CONTAINER_NAME > /dev/null 2>&1
} && {
  echo "$BOT_CONTAINER_NAME container exists. Run nuke.sh to setup from a clean environment."
  exit 1
}

{
  docker inspect -f {{.State.Running}} $DB_CONTAINER_NAME > /dev/null 2>&1
} && {
  echo "$DB_CONTAINER_NAME container exists. Run nuke.sh to setup from a clean environment."
  exit 1
}

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [ ! -f $DIR/../.env ]
  then
    echo "\".env\" file not found in root project directory. Create one then run setup.sh again."
    exit 1
fi

export $(egrep -v '^#' $DIR/../.env | xargs)

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

echo "Checking status of db..."
sleep 5

RETRY_COUNT=0
while [  $RETRY_COUNT -lt 5 ]; do
  {
    output=$( PGPASSWORD=$DB_PASS docker exec $DB_CONTAINER_NAME psql -h localhost --username=$DB_USER --dbname=whopay )
  } || {
    output="retry"
  }
  if [ "$output" = "" ]
    then
      echo "db up and running"
      break
  fi
  if [ $RETRY_COUNT = 4 ]
    then
      echo "db has failed to run. Exiting..."
    exit 1
  fi
  echo "Retrying in 5 seconds..."
  sleep 5
  let RETRY_COUNT=RETRY_COUNT+1
done

echo "Seeding db..."	

docker exec $DB_CONTAINER_NAME mkdir -p /migrations
docker cp $DIR/../migrations $DB_CONTAINER_NAME:/.

for filepath in $DIR/../migrations/*.sql; do
  filename=$(basename $filepath)
  PGPASSWORD=$DB_PASS docker exec $DB_CONTAINER_NAME psql -h localhost --username=$DB_USER --dbname=whopay -a -f /migrations/$filename > /dev/null 2>&1
done

echo "Done"

