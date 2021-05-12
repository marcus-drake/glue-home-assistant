import asyncio
import logging
from datetime import timedelta

import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_LOCKED, STATE_UNLOCKED, STATE_UNKNOWN, ATTR_BATTERY_LEVEL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed, CoordinatorEntity

from .api import GlueHomeLocksApi, GlueHomeLock, SUCCESSFUL_CONNECTED_STATUSES, LOCKED_STATES, UNLOCKED_STATES
from .const import CONF_API_KEY, DOMAIN, ATTR_LAST_LOCK_EVENT_TIME, ATTR_LAST_LOCK_EVENT_TYPE, ATTR_CONNECTION_STATUS
from .exceptions import GlueHomeNetworkError, GlueHomeInvalidAuth
from homeassistant.components.lock import LockEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities) -> None:
    _LOGGER.info("Setting up locks for Glue Home")

    api = GlueHomeLocksApi(config_entry.data.get(CONF_API_KEY))

    try:
        await hass.async_add_executor_job(api.get_locks)
    except GlueHomeInvalidAuth:
        _LOGGER.error("Failed to authenticate with API key to Glue Home")
        raise ConfigEntryNotReady

    async def async_update_data():
        try:
            async with async_timeout.timeout(10):
                return await hass.async_add_executor_job(api.get_locks)
        except GlueHomeNetworkError as err:
            raise UpdateFailed(f"Error communicating with API: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        # Name of the data. For logging purposes.
        name="gluehome",
        update_method=async_update_data,
        # Polling interval. Will only be polled if there are subscribers.
        update_interval=timedelta(seconds=20),
    )

    await coordinator.async_config_entry_first_refresh()

    _LOGGER.info(f"Found {len(coordinator.data)} locks")

    async_add_entities(
        GlueHomeLockEntity(coordinator, index) for index, ent in enumerate(coordinator.data)
    )


class GlueHomeLockEntity(CoordinatorEntity, LockEntity):
    """Representation of a Glue Home Lock."""

    def __init__(self, coordinator: DataUpdateCoordinator, index: int) -> None:
        super().__init__(coordinator)
        self._index = index

    def _lock(self) -> GlueHomeLock:
        return self.coordinator.data[self._index]

    @property
    def name(self) -> str:
        return self._lock().description

    @property
    def unique_id(self) -> str:
        return self._lock().id

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._lock().connection_status in SUCCESSFUL_CONNECTED_STATUSES

    @property
    def is_locked(self) -> bool:
        return self._lock().last_lock_event_type in LOCKED_STATES

    @property
    def state(self) -> str:
        """Get the state of the device."""
        if self.is_locked:
            return STATE_LOCKED
        elif self._lock().last_lock_event_type in UNLOCKED_STATES:
            return STATE_UNLOCKED
        else:
            return STATE_UNKNOWN

    async def async_lock(self, **kwargs) -> None:
        """Lock the device."""
        await self.hass.async_add_executor_job(self._lock().operation, "lock")

        await asyncio.sleep(15_000)
        await self.coordinator.async_request_refresh()

    async def async_unlock(self, **kwargs) -> None:
        """Unlock the device."""
        await self.hass.async_add_executor_job(self._lock().operation, "unlock")

        await asyncio.sleep(15_000)
        await self.coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict:
        return {
            ATTR_BATTERY_LEVEL: self._lock().battery_status,
            ATTR_CONNECTION_STATUS: self._lock().connection_status,
            ATTR_LAST_LOCK_EVENT_TYPE: self._lock().last_lock_event_type,
            ATTR_LAST_LOCK_EVENT_TIME: self._lock().last_lock_event_time
        }

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.entity_id)},
            "manufacturer": "Glue Home",
            "name": self.name,
            "model": self._lock().model_name,
            "sw_version": self._lock().firmware_version
        }