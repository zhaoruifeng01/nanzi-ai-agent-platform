#!/bin/bash
# 构建 ARM64 Linux 镜像（鲲鹏、Ampere、树莓派 64 位等）
# 平台标识: linux/arm64
set -e
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export PLATFORM=linux/arm64
exec "$SCRIPT_DIR/_build_common.sh"
