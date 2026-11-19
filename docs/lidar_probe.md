# 雷达（商家 TOF + `lidar_pkg`）

- 日期：2026-11-17
- 资料：`doc/lidar_pkg_ros2-main.zip` → 工作空间包 `ros2_ws/src/lidar_pkg`
- USB：`34bf:ff0a` STC USB Serial（`ttyACM1`）；稳定名  
  `/dev/serial/by-id/usb-STC_STC_USB_Serial-if00`  
  udev 后：`/dev/lidar`（`scripts/99-lidar.rules`，`sudo ./setup.sh`）
- 协议：帧头 `AA 55`；波特率 **150000**（非 230400）；启动 `A5 60`；停止 `A5 65` 等
- 形态：密封 TOF 小圆饼（卖家「紫色雷达」兼容）；不是外露转头 LD14

## 验收

```bash
cd /opt/personal_robot/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch lidar_pkg lidar.launch.py
# 另开终端：
ros2 topic hz /scan
ros2 topic echo /scan --once
```

有 `/scan` 且雷达头顶在转即正常。测完 Ctrl+C，节点析构会发停转命令。

## 前后

物理上对齐车头后，可用 `LaserScan` / 后续 `angle_offset` 微调。本包默认 `frame_id: laser`。

## 已嵌入

见 `docs/lidar_assist.md`：Safety 近距刹停 + 可选跟随（`/cmd_vel_awake`）。
