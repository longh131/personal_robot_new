import pytest
from c30d_driver.serial_link import SerialLink


def test_reject_ttyacm0():
    with pytest.raises(ValueError):
        SerialLink('/dev/ttyACM0', 115200)


def test_accept_c30d_path():
    link = SerialLink('/dev/c30d', 115200)
    assert link.port == '/dev/c30d'
    assert link.connected is False


def test_write_failure_disconnects():
    link = SerialLink('/dev/c30d', 115200)

    class Boom:
        def write(self, _data):
            raise OSError('gone')

        def close(self):
            pass

    link.ser = Boom()
    link.connected = True
    assert link.write(b'x') is False
    assert link.connected is False
    assert 'gone' in link.last_error
