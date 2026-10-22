"""Config flow for the Apple IR Receiver integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
)

from .const import DOMAIN
from .hidraw import HidrawDevice, find_apple_ir_devices


def _unique_id(device: HidrawDevice) -> str:
    return f"{device.vendor_id:04x}:{device.product_id:04x}:{device.phys}"


def _device_schema(devices: list[HidrawDevice]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required("path"): SelectSelector(
                SelectSelectorConfig(
                    options=[
                        SelectOptionDict(value=d.path, label=f"{d.name} ({d.path})")
                        for d in devices
                    ]
                )
            )
        }
    )


class AppleIRConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Apple IR Receiver."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user pick a detected receiver."""
        devices = await self.hass.async_add_executor_job(find_apple_ir_devices)
        by_path = {device.path: device for device in devices}

        if user_input is not None:
            device = by_path[user_input["path"]]
            await self.async_set_unique_id(_unique_id(device))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=device.name, data={"path": device.path}
            )

        if not devices:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user", data_schema=_device_schema(devices)
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user pick the receiver again, e.g. after /dev/hidraw* changed."""
        devices = await self.hass.async_add_executor_job(find_apple_ir_devices)
        by_path = {device.path: device for device in devices}

        if user_input is not None:
            device = by_path[user_input["path"]]
            await self.async_set_unique_id(_unique_id(device))
            return self.async_update_reload_and_abort(
                self._get_reconfigure_entry(),
                unique_id=_unique_id(device),
                data_updates={"path": device.path},
            )

        if not devices:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                _device_schema(devices),
                {"path": self._get_reconfigure_entry().data["path"]},
            ),
        )
