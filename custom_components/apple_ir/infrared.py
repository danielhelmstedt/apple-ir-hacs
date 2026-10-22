"""Infrared receiver platform for the Apple IR Receiver integration."""

from __future__ import annotations

import logging
import time
from typing import override

from homeassistant.components.infrared import (
    InfraredReceiverEntity,
    InfraredReceiverEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import AppleIRConfigEntry
from .const import DEFAULT_DEVICE_NAME, DEFAULT_ENTITY_ID, DOMAIN
from .protocol import AppleIRReport, ReportType, parse_report, report_to_signal

_LOGGER = logging.getLogger(__name__)

REPEAT_WINDOW = 0.25


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AppleIRConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the infrared receiver entity."""
    async_add_entities([AppleIRReceiver(entry)])


class AppleIRReceiver(InfraredReceiverEntity):
    """Infrared receiver backed by an Apple IR HID device."""

    entity_description = InfraredReceiverEntityDescription(key="receiver")
    _attr_has_entity_name = False
    _attr_name = None

    def __init__(self, entry: AppleIRConfigEntry) -> None:
        """Initialize the receiver."""
        self._entry = entry
        self._last_frame: bytes | None = None
        self._last_time = 0.0
        self.entity_id = DEFAULT_ENTITY_ID
        self._attr_unique_id = entry.unique_id or entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            manufacturer="Apple",
            model="IR Receiver",
            name=DEFAULT_DEVICE_NAME,
        )

    @override
    async def async_added_to_hass(self) -> None:
        """Start reading reports once added."""
        await super().async_added_to_hass()
        self._entry.runtime_data.start(
            self.hass.loop, self._handle_report, self._handle_error
        )

    @callback
    def _handle_report(self, data: bytes) -> None:
        report = parse_report(data)
        if report is None:
            _LOGGER.debug("Ignoring unknown report: %s", data.hex())
            return
        if report.type is ReportType.BATTERY:
            _LOGGER.warning("Apple Remote reports a possible flat battery")
            return
        now = time.monotonic()
        # A held key resends the identical frame every ~108ms; emit that as an
        # NEC repeat frame, as the original remote would.
        if (
            report.type is ReportType.KEY
            and report.data == self._last_frame
            and now - self._last_time < REPEAT_WINDOW
        ):
            report = AppleIRReport(ReportType.REPEAT, report.data)
        if report.type is ReportType.KEY:
            self._last_frame = report.data
        self._last_time = now
        signal = report_to_signal(report)
        if signal is not None:
            self._handle_received_signal(signal)

    @callback
    def _handle_error(self, err: Exception) -> None:
        _LOGGER.error("Lost connection to Apple IR receiver: %s", err)
        self._attr_available = False
        self.async_write_ha_state()
        self.hass.config_entries.async_schedule_reload(self._entry.entry_id)
