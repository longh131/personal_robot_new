"""C30D 串口连接。设备用 /dev/c30d 或 by-id，不写死 ttyACM0。"""

from __future__ import annotations


class SerialLink:
    def __init__(self, port: str, baud: int) -> None:
        if port.strip() in ('', '/dev/ttyACM0'):
            raise ValueError('port must be /dev/c30d or a by-id path, not ttyACM0')
        self.port = port
        self.baud = baud
        self.ser = None
        self.connected = False
        self.last_error = ''

    def open(self) -> bool:
        try:
            import serial
            self.close()
            self.ser = serial.Serial(self.port, self.baud, timeout=0.05)
            self.connected = True
            self.last_error = ''
            return True
        except Exception as e:
            self.ser = None
            self.connected = False
            self.last_error = str(e)
            return False

    def close(self) -> None:
        if self.ser is not None:
            try:
                self.ser.close()
            except Exception:
                pass
        self.ser = None
        self.connected = False

    def write(self, data: bytes) -> bool:
        if not self.connected or self.ser is None:
            if not self.open():
                return False
        try:
            self.ser.write(data)
            return True
        except Exception as e:
            self.last_error = str(e)
            self.close()
            return False

    def read(self, max_bytes: int = 256) -> bytes:
        if not self.connected or self.ser is None:
            return b''
        try:
            n = int(getattr(self.ser, 'in_waiting', 0) or 0)
            if n <= 0:
                return b''
            return self.ser.read(min(n, max_bytes))
        except Exception as e:
            self.last_error = str(e)
            self.close()
            return b''
