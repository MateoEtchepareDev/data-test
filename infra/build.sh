#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$ROOT/infra/build"

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

cp -r "$ROOT/services/api/src/api" "$BUILD_DIR/api"
cp -r "$ROOT/packages/shared/src/shared" "$BUILD_DIR/shared"

pip install --quiet --target "$BUILD_DIR" flask mangum psycopg2-binary

echo "Build dir listo en $BUILD_DIR"