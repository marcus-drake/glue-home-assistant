import asyncio
import logging
from typing import Optional

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import LOCKED_STATES, UNLOCKED_STATES, \
    GlueHomeLockOperation
from .const import DOMAIN, ATTR_CONNECTION_STATUS
from .exceptions import GlueHomeLockOperationFailed
from .sensor import GlueHomeBaseEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][config.entry_id]

    async_add_entities(
        GlueHomeLockEntity(coordinator, index) for index, ent in enumerate(coordinator.data)
    )


class GlueHomeLockEntity(GlueHomeBaseEntity, LockEntity):
    _is_locking = False
    _is_unlocking = False

    @property
    def name(self) -> str:
        return self._lock().description

    @property
    def unique_id(self) -> str:
        return self._lock().id

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
            ATTR_CONNECTION_STATUS: self._lock().connection_status
        }
