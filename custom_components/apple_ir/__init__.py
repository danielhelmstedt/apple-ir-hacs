"""The Apple IR Receiver integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .hidraw import HidrawReader

PLATFORMS = [Platform.INFRARED]

type AppleIRConfigEntry = ConfigEntry[HidrawReader]


async def async_setup_entry(hass: HomeAssistant, entry: AppleIRConfigEntry) -> bool:
    """Set up Apple IR Receiver from a config entry."""
    reader = HidrawReader(entry.data["path"])
    try:
        await hass.async_add_executor_job(reader.open)
    except OSError as err:
        raise ConfigEntryNotReady(
            f"Cannot open {entry.data['path']}: {err}"
        ) from err

    entry.runtime_data = reader
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AppleIRConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry.runtime_data.close()
    return unload_ok
