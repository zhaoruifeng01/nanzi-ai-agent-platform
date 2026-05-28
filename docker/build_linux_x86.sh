#!/bin/bash
# 构建 x86_64 Linux 镜像（常见云服务器 / 传统 PC 服务器）
# 平台标识: linux/amd64
set -e
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export PLATFORM=linux/amd64
exec "$SCRIPT_DIR/_build_common.sh"
