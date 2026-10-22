"""Access to Apple IR receivers through the Linux hidraw interface."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
import os
from pathlib import Path

from .const import APPLE_IR_PRODUCT_IDS, APPLE_VENDOR_ID, DEFAULT_DEVICE_NAME

_LOGGER = logging.getLogger(__name__)

HIDRAW_CLASS_DIR = Path("/sys/class/hidraw")


@dataclass(frozen=True, slots=True)
class HidrawDevice:
    """A hidraw device node."""

    path: str
    name: str
    vendor_id: int
    product_id: int
    phys: str


def _parse_uevent(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        key, sep, value = line.partition("=")
        if sep:
            result[key.strip()] = value.strip()
    return result


def find_apple_ir_devices() -> list[HidrawDevice]:
    """Find Apple IR receivers exposed via hidraw (blocking)."""
    devices: list[HidrawDevice] = []
    if not HIDRAW_CLASS_DIR.is_dir():
        return devices
    for node in sorted(HIDRAW_CLASS_DIR.iterdir()):
        try:
            info = _parse_uevent((node / "device" / "uevent").read_text())
            _bus, vid, pid = info["HID_ID"].split(":")
            vendor_id, product_id = int(vid, 16), int(pid, 16)
        except (OSError, KeyError, ValueError):
            continue
        if vendor_id != APPLE_VENDOR_ID or product_id not in APPLE_IR_PRODUCT_IDS:
            continue
        devices.append(
            HidrawDevice(
                path=f"/dev/{node.name}",
                name=DEFAULT_DEVICE_NAME,
                vendor_id=vendor_id,
                product_id=product_id,
                phys=info.get("HID_PHYS", ""),
            )
        )
    return devices


class HidrawReader:
    """Reads reports from a hidraw node using the event loop."""

    def __init__(self, path: str) -> None:
        """Initialize the reader."""
        self.path = path
        self._fd: int | None = None
        self._loop = None
        self._report_cb: Callable[[bytes], None] | None = None
        self._error_cb: Callable[[Exception], None] | None = None

    def open(self) -> None:
        """Open the device (blocking)."""
        self._fd = os.open(self.path, os.O_RDONLY | os.O_NONBLOCK)

    def start(
        self,
        loop,
        report_cb: Callable[[bytes], None],
        error_cb: Callable[[Exception], None],
    ) -> None:
        """Start delivering reports in the given event loop."""
        assert self._fd is not None
        self._loop = loop
        self._report_cb = report_cb
        self._error_cb = error_cb
        loop.add_reader(self._fd, self._on_readable)

    def _on_readable(self) -> None:
        assert self._fd is not None
        assert self._report_cb is not None
        assert self._error_cb is not None
        while True:
            try:
                data = os.read(self._fd, 64)
            except BlockingIOError:
                return
            except OSError as err:
                self.close()
                self._error_cb(err)
                return
            if not data:
                self.close()
                self._error_cb(OSError("hidraw device closed"))
                return
            self._report_cb(data)

    def close(self) -> None:
        """Stop reading and close the device (non-blocking)."""
        if self._fd is None:
            return
        if self._loop is not None:
            self._loop.remove_reader(self._fd)
        try:
            os.close(self._fd)
        except OSError:
            _LOGGER.debug("Error closing %s", self.path, exc_info=True)
        self._fd = None
