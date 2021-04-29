"""Glue Home"""

import logging
from datetime import timedelta

import async_timeout
from homeassistant.components.sesame.lock import ATTR_SERIAL_NO
from homeassistant.components.zha.core.discovery import async_add_entities
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_LOCKED, STATE_UNLOCKED, STATE_UNKNOWN, ATTR_BATTERY_LEVEL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed, CoordinatorEntity

from api import GlueHomeLocksApi, GlueHomeLock, SUCCESSFUL_CONNECTED_STATUSES, LOCKED_STATES, UNLOCKED_STATES
from const import ATTR_FIRMWARE_VERSION
from exceptions import GlueHomeNetworkError
from homeassistant.components.lock import LockEntity

_LOGGER = logging.getLogger(__name__)


def async_setup_entry(hass: HomeAssistant, config: ConfigEntry) -> bool:
    api = GlueHomeLocksApi(config.data.get("apiKey"))

    try:
        api.get_locks()
    except GlueHomeNetworkError:
        _LOGGER.error("Cannot connect to Dyson cloud service.")
        raise ConfigEntryNotReady

    async def async_update_data():
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            async with async_timeout.timeout(10):
                return await api.get_locks()
        except GlueHomeNetworkError as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        # Name of the data. For logging purposes.
        name="gluehome",
        update_method=async_update_data,
        # Polling interval. Will only be polled if there are subscribers.
        update_interval=timedelta(seconds=30),
    )

    await coordinator.async_config_entry_first_refresh()

    async_add_entities(
        GlueHomeLockEntity(coordinator, ent) for idx, ent in enumerate(coordinator.data)
    )

    return True


class GlueHomeLockEntity(CoordinatorEntity, LockEntity):
    """Representation of a Glue Home Lock."""

    def __init__(self, coordinator: DataUpdateCoordinator, lock: GlueHomeLock) -> None:
        super().__init__(coordinator)

        self._lock = lock

        self._serial = lock.serialNumber
        self._battery = lock.batteryStatus
        self._firmware_version = lock.firmwareVersion

    @property
    def name(self) -> str:
        return self._lock.description

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._lock.connectionStatus in SUCCESSFUL_CONNECTED_STATUSES

    @property
    def is_locked(self) -> bool:
        return self._lock.lastLockEventType in LOCKED_STATES

    @property
    def state(self) -> str:
        """Get the state of the device."""
        if self.is_locked:
            return STATE_LOCKED
        elif self._lock.lastLockEventType in UNLOCKED_STATES:
            return STATE_UNLOCKED
        else:
            return STATE_UNKNOWN

    def lock(self, **kwargs) -> None:
        """Lock the device."""
        self._lock.operation("lock")

    def unlock(self, **kwargs) -> None:
        """Unlock the device."""
        self._lock.operation("unlock")

    @property
    def extra_state_attributes(self) -> dict:
        return {
            ATTR_SERIAL_NO: self._serial,
            ATTR_BATTERY_LEVEL: self._battery,
            ATTR_FIRMWARE_VERSION: self._firmware_version
        }
