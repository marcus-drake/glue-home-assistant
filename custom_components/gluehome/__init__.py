"""Glue Home"""
import logging
from datetime import timedelta

import async_timeout
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import UpdateFailed, DataUpdateCoordinator

from .api import GlueHomeLocksApi, GlueHomeLock
from .const import DOMAIN, CONF_API_KEY, DEVICE_MANUFACTURER
from .exceptions import GlueHomeInvalidAuth, GlueHomeNetworkError

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config: config_entries.ConfigEntry):
    _LOGGER.info("Setting up Glue Home")
    hass.data.setdefault(DOMAIN, {})
    if not config.data[CONF_API_KEY]:
        return False

    _LOGGER.info("Setting up locks for Glue Home")

    api = GlueHomeLocksApi(config.data.get(CONF_API_KEY))

    async def async_update_data():
        try:
            async with async_timeout.timeout(60):
                return await hass.async_add_executor_job(api.get_locks)
        except GlueHomeInvalidAuth:
            _LOGGER.error("Failed to authenticate with API key to Glue Home")
            raise ConfigEntryNotReady
        except GlueHomeNetworkError as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(seconds=30),
    )

    await coordinator.async_config_entry_first_refresh()

    locks = coordinator.data
    _LOGGER.info(f"Found {len(locks)} Glue Home locks")

    hass.data.setdefault(DOMAIN, {})[config.entry_id] = coordinator

    await hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(config, "lock")
    )

    await hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(config, "sensor")
    )

    device_registry = dr.async_get(hass)
    for lock in locks:
        add_device(device_registry, lock)

    return True


def add_device(device_registry, lock: GlueHomeLock):
    device_registry.async_get_or_create(
        config_entry_id=lock.id,
        identifiers={
            (DOMAIN, lock.id),
            (DOMAIN, lock.serial_number),
        },
        manufacturer=DEVICE_MANUFACTURER,
        name=lock.description,
        model=lock.model_name,
        sw_version=lock.firmware_version,
    )
