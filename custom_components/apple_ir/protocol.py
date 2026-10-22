"""Decode Apple Remote HID reports into raw IR timings.

The receiver delivers each IR frame as a 5 byte HID report (see https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/plain/drivers/hid/hid-appleir.c):

    25 87 ee <remote id> <key>   key press (NEC-style frame)
    26 ...                       key repeat
    25 87 e0 ...                 flat battery notice

The report bytes 1..4 are exactly the 32 bits of the original NEC-style frame
(LSB first), so the original pulse train can be reconstructed from them.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from homeassistant.components.infrared import InfraredReceivedSignal

MODULATION = 38000

REPORT_KEY = 0x25
REPORT_REPEAT = 0x26
REPORT_IDS = (0x24, REPORT_KEY, REPORT_REPEAT)
REPORT_LENGTH = 5
APPLE_PREFIX = bytes((0x87, 0xEE))
BATTERY_PREFIX = bytes((0x87, 0xE0))

LEADER_HIGH = 9000
LEADER_LOW = 4500
BIT_HIGH = 562
ZERO_LOW = 562
ONE_LOW = 1687
REPEAT_LOW = 2250


class ReportType(StrEnum):
    """Kind of report received from the receiver."""

    KEY = "key"
    REPEAT = "repeat"
    BATTERY = "battery"


@dataclass(frozen=True, slots=True)
class AppleIRReport:
    """A decoded HID report."""

    type: ReportType
    data: bytes


def parse_report(report: bytes) -> AppleIRReport | None:
    """Classify a raw HID report, returning None if it is not recognised."""
    if len(report) != REPORT_LENGTH or report[0] not in REPORT_IDS:
        return None
    frame = bytes(report[1:])
    if report[0] == REPORT_KEY and report[1:3] == BATTERY_PREFIX:
        return AppleIRReport(ReportType.BATTERY, frame)
    # The firmware forwards any NEC frame (not only Apple Remote ones); an
    # all-zero payload is the bare repeat marker.
    if report[0] == REPORT_REPEAT and not any(frame):
        return AppleIRReport(ReportType.REPEAT, frame)
    return AppleIRReport(ReportType.KEY, frame)


def frame_timings(frame: bytes) -> list[int]:
    """Build raw timings (positive = mark, negative = space) for a 4 byte frame."""
    timings = [LEADER_HIGH, -LEADER_LOW]
    for byte in frame:
        for bit in range(8):
            timings.append(BIT_HIGH)
            timings.append(-ONE_LOW if byte >> bit & 1 else -ZERO_LOW)
    timings.append(BIT_HIGH)
    return timings


def repeat_timings() -> list[int]:
    """Build raw timings for an NEC repeat frame."""
    return [LEADER_HIGH, -REPEAT_LOW, BIT_HIGH]


def report_to_signal(report: AppleIRReport) -> InfraredReceivedSignal | None:
    """Convert a decoded report to an infrared signal, if it carries one."""
    if report.type is ReportType.KEY:
        timings = frame_timings(report.data)
    elif report.type is ReportType.REPEAT:
        timings = repeat_timings()
    else:
        return None
    return InfraredReceivedSignal(timings=timings, modulation=MODULATION)
