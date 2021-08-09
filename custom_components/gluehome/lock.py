import asyncio
import logging
from datetime import timedelta
from typing import Optional

import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_LOCKED, STATE_UNLOCKED, STATE_UNKNOWN, ATTR_BATTERY_LEVEL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed, CoordinatorEntity

from .api import GlueHomeLocksApi, GlueHomeLock, SUCCESSFUL_CONNECTED_STATUSES, LOCKED_STATES, UNLOCKED_STATES, \
    GlueHomeLockOperation
from .const import CONF_API_KEY, DOMAIN, ATTR_LAST_LOCK_EVENT_TIME, ATTR_LAST_LOCK_EVENT_TYPE, ATTR_CONNECTION_STATUS
from .exceptions import GlueHomeNetworkError, GlueHomeInvalidAuth, GlueHomeException, GlueHomeLockOperationFailed
from homeassistant.components.lock import LockEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities) -> None:
    _LOGGER.info("Setting up locks for Glue Home")

    api = GlueHomeLocksApi(config_entry.data.get(CONF_API_KEY))

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
        # Name of the data. For logging purposes.
        name="gluehome",
        update_method=async_update_data,
        # Polling interval. Will only be polled if there are subscribers.
        update_interval=timedelta(seconds=30),
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

        self._is_locking = False
        self._is_unlocking = False

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
    def is_locked(self) -> Optional[bool]:
        if self._lock().last_lock_event_type in LOCKED_STATES:
            return True
        elif self._lock().last_lock_event_type in UNLOCKED_STATES:
            return False
        else:
            return None

    @property
    def is_locking(self) -> Optional[bool]:
        return self._is_locking

    @property
    def is_unlocking(self) -> Optional[bool]:
        return self._is_unlocking

    async def async_lock(self, **kwargs) -> None:
        """Lock the device."""
        try:
            self._is_locking = True
            await self.async_update_ha_state()

            await self._run_operation("lock")
        finally:
            self._is_locking = False
            await self.async_update_ha_state()

    async def async_unlock(self, **kwargs) -> None:
        """Unlock the device."""
        try:
            self._is_unlocking = True
            await self.async_update_ha_state()

            await self._run_operation("unlock")
        finally:
            self._is_unlocking = False
            await self.async_update_ha_state()

    async def _run_operation(self, operation: str) -> None:
        _LOGGER.info(f"Requesting to run operation {operation} on {self._lock().id}")
        initial_lock_operation = await self.hass.async_add_executor_job(self._lock().create_operation, operation)

        async def poll_until_operation_completed(lock_operation: GlueHomeLockOperation, retries_left):
            if retries_left <= 0:
                _LOGGER.debug(f"Operation {lock_operation.id} ran out of retries, will stop polling")
                return None
            elif lock_operation.status == "failed":
                raise GlueHomeLockOperationFailed(self._lock().description, operation, lock_operation.reason)
            elif lock_operation.status != "pending":
                _LOGGER.info(f"Operation completed with {lock_operation.status} for lock {self._lock().id}")
                return None
            else:
                await asyncio.sleep(1)
                update = await self.hass.async_add_executor_job(lock_operation.poll)
                await poll_until_operation_completed(update, retries_left - 1)

        await poll_until_operation_completed(initial_lock_operation, 30)

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
