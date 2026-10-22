#!/bin/bash
# 使用项目内 Raspberry Pi libcamera/PiSP（不覆盖 Ubuntu 的 libcamera 0.2）
PREFIX=/opt/personal_robot/tools/rpi_camera
export LD_LIBRARY_PATH="$PREFIX/lib/aarch64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export LIBCAMERA_IPA_MODULE_PATH="$PREFIX/lib/aarch64-linux-gnu/libcamera/ipa"
export LIBCAMERA_IPA_CONFIG_PATH="$PREFIX/share/libcamera/ipa"
export LIBCAMERA_IPA_PROXY_PATH="$PREFIX/libexec/libcamera"
cmd=${1:-rpicam-still}
shift || true
exec "$PREFIX/bin/$cmd" "$@"
