#!/bin/sh
set -eu

until mc alias set local "$S3_ENDPOINT_URL" "$S3_ACCESS_KEY" "$S3_SECRET_KEY"; do
  sleep 2
done

mc mb --ignore-existing "local/$S3_BUCKET"
mc anonymous set private "local/$S3_BUCKET"

