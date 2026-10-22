# 相机探测（2026-10-19）

- 批准范围：认设备 + 一张静图。未装新软件，未开电机。
- 结果：**未能拍照。** USB Yundea 不是摄像头。排线 CSI 在设备树里是 **disabled**，libcamera 看不到模组。

## 事实

- USB `Yundea 1076`（`4759:3931`）接口是 **大容量存储 + USB 声卡**，不是 UVC 摄像头。没有对应 `/dev/video*`。
- `/dev/video19–37` 全是 Pi ISP/编解码节点（`rpivid`/`pispbe-*`），OpenCV 打不开采集。
- `libcamerasrc`：`CameraMananger::cameras() is empty`（未识别 CSI 模组）。
- 无 `picamera2`、无 `rpicam-still`。旧 zip 的 Picamera2 CSI 路径在本机不成立。

## 回退

无系统改动。空目录 `hardware_test/camera/` 未写入图片。

## CSI 复测（用户说明为排线）

- `camera_auto_detect=1` 已开，但运行中 `csi@110000` / `csi@128000` 均为 **disabled**，`cam0_clk`/`cam1_clk` 也是 disabled。
- 本机无 `rpicam-still`/`picamera2`；`libcamera0.2` 且 **没有 IPA 目录**。
- 无 sudo，未能 `i2cdetect` 扫 CAM 的 I2C。
- overlay 文件有：`imx219` `imx708` `ov5647` 等。

未改 `/boot/firmware/config.txt`，未 apt。

## 对照 Debian 上曾用的命令

当时树莓派 Debian：`rpicam-hello` / `rpicam-jpeg`。本机 Ubuntu 24.04 **没有这些命令**。`dmesg` 普通用户读不了；内核日志里 **没有 imx/ov/sensor**。`/dev/video*` 仍是 ISP 节点。`dtoverlay -l` 报 no matching platform。

**不像已经证伪硬件。** 更像系统栈换了：Debian 的 rpicam/自动叠加没带到 Ubuntu，CSI 未使能。硬件好坏要在装回 rpicam 或写对 overlay 之后才能下结论。

## 已批准后的第一次 overlay（写错）

包已装：`libcamera-ipa` / `libcamera-tools` / `python3-libcamera`。`andylong` 已在 `i2c` 组。`config.txt` 曾写成 `dtoverlay=imx219`（CAM1）。

重启后：`csi@128000` okay，`csi@110000` disabled。内核 `imx219 11-0010: failed to read chip id 219`（-121）。`cam --list` 仍空。这符合 **口和芯片都不对**，不是硬件已坏。

用户补充：模组 **OV5647 / Camera Rev 1.3 500万**，插 **CAM0（近 Micro HDMI）**。需改成 `dtoverlay=ov5647,cam0` 再重启。

## 第二次重启（ov5647,cam0）

overlay 已是 `dtoverlay=ov5647,cam0`。`csi@110000` okay，`cam0_clk` okay，`csi@128000` disabled。内核 `ov5647 10-0036` I2C 读失败 **-121**，probe 失败。`i2cdetect -y 10` 全空（无 0x36）。`cam --list` 仍空。

用户称硬件已检查无大问题。复测仍是：CAM0 的 `i2c-10` 全空，`ov5647` probe -121，`cam0_reg` 现为 disabled（probe 失败后会关掉，属预期）。**CAM0 口上现在没有模组应答。** 下一步改试 CAM1：`dtoverlay=ov5647`。

## 第三次重启（ov5647 @ CAM1）

overlay：`dtoverlay=ov5647`。`csi@128000` okay。内核 **已绑定** `ov5647 11-0036`，`Using sensor ov5647 ... for capture`，注册 `/dev/video0`。`i2c-11` 的 `0x36` 为 `UU`。硬件和口都正常；实际是 **CAM1**，不是靠近 HDMI 时以为的 CAM0。

仍未能拍照：Ubuntu `libcamera 0.2` 只有 `PipelineHandlerVc4` / `ipa_rpi_vc4`，没有 Pi 5 的 PiSP pipeline。`cam --list` 与 `libcamerasrc` 为空。OpenCV 打开 `/dev/video0` 但读帧失败（CSI 需 media-controller + IPA）。

下一步（需批准）：换带 PiSP 的 libcamera/rpicam（例如 Raspberry Pi 源），或从源码编 raspberrypi libcamera。未批准不改源、不编译。

## PiSP 栈与静图（已批准）

未加第三方 PPA、未替换 Ubuntu `libcamera0.2`。运行时在 `/opt/personal_robot/tools/rpi_camera`：`libpisp` 1.7.0、`libcamera` 0.7.2（pipeline `rpi/pisp`）、`rpicam-apps` 1.14.0。

`rpicam-still --list-cameras`：`ov5647 2592x1944` @ CAM1。静图已拍：`hardware_test/camera/test.jpg`（2592×1944 JPEG，约 214KB）。调用：`scripts/rpicam.sh rpicam-jpeg -n -o ...`
