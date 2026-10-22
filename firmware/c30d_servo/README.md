# C30D 从动伺服（基于 R550 Mini 2026.08.21）

`doc/` 里的 R550 原包不要改。本目录才是要编译烧录的工程。

相对原厂 hex 的改动：写死 `Mec-V` 运动学；300ms 无帧或速度全 0 → 立刻 PWM=0（不靠 IMU、不等 2.5 秒）；关掉 APP；屏显 **`Mec-S`**。

已生成 FlyMcu 可用的 hex（树莓派 GCC 编译）：

`firmware/c30d_servo/OBJ/WHEELTEC.hex`

拷到 Windows，用 **FlyMcu** 按以前的方式烧。屏应为 **`Mec-S`**。轮子离地，SWD/串口烧录电压与以前相同。

## 编译烧录（Windows + Keil）

1. 把整个 `firmware/c30d_servo` 拷到电脑  
2. Keil 打开 `USER/WHEELTEC.uvprojx`  
3. `Project` → `Rebuild all target files`，要 **0 Error**  
4. 成功后 `OBJ/WHEELTEC.hex` 会出现  
5. 轮子离地，SWD **3.3V**，`Flash` → `Download`  
6. 复位。屏应是 **`Mec-S`**（仍是 `Mec-V` 说明烧的还是原厂包）

通电不应转。约 10 秒后才收串口。然后离地测键盘：`i` 转，松手/`k` 应停。不停立刻断电。

着地运动需另批。这不是工业级急停。
