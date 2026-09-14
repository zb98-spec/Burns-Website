#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

IMAGE_NAME="burns-website"
CONTAINER_NAME="burns-test"
PORT=8080

echo "==> Checking Docker is running..."
if ! docker info > /dev/null 2>&1; then
  echo "Docker doesn't seem to be running. Start Docker Desktop and try again."
  exit 1
fi

echo "==> Removing any existing '${CONTAINER_NAME}' container..."
docker rm -f "${CONTAINER_NAME}" > /dev/null 2>&1 || true

echo "==> Building image '${IMAGE_NAME}'..."
docker build -t "${IMAGE_NAME}" .

echo "==> Starting container '${CONTAINER_NAME}' on port ${PORT}..."
docker run -d --rm -p "${PORT}:${PORT}" --name "${CONTAINER_NAME}" "${IMAGE_NAME}"

echo "==> Waiting for the app to respond..."
for i in $(seq 1 20); do
  if curl -s "http://localhost:${PORT}" > /dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

echo "==> Opening http://localhost:${PORT} in your browser..."
open "http://localhost:${PORT}"

echo "==> Done. Container '${CONTAINER_NAME}' is running."
echo "    View logs:   docker logs -f ${CONTAINER_NAME}"
echo "    Stop it:     docker stop ${CONTAINER_NAME}"
