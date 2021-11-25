import logging

from homeassistant.components.sensor import SensorEntity, STATE_CLASS_MEASUREMENT
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import DEVICE_CLASS_BATTERY, \
    PERCENTAGE, ENTITY_CATEGORY_DIAGNOSTIC, DEVICE_CLASS_TIMESTAMP
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, Entity
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity

from .api import GlueHomeLock, SUCCESSFUL_CONNECTED_STATUSES
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config: ConfigEntry, async_add_entities) -> None:
    coordinator = hass.data[DOMAIN][config.entry_id]

    async_add_entities(
        GlueHomeBatteryLevelEntity(coordinator, index) for index, ent in enumerate(coordinator.data)
    )
    async_add_entities(
        GlueHomeLastLockEventTypeEntity(coordinator, index) for index, ent in enumerate(coordinator.data)
    )
    async_add_entities(
        GlueHomeLastLockEventTimeEntity(coordinator, index) for index, ent in enumerate(coordinator.data)
    )


class GlueHomeBaseEntity(CoordinatorEntity, Entity):
    def __init__(self, coordinator: DataUpdateCoordinator, index: int) -> None:
        super().__init__(coordinator)
        self._index = index

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.data[self._index].id)},
        )

    def _lock(self) -> GlueHomeLock:
        return self.coordinator.data[self._index]

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._lock().connection_status in SUCCESSFUL_CONNECTED_STATUSES


class GlueHomeBatteryLevelEntity(GlueHomeBaseEntity, SensorEntity):
    _attr_device_class = DEVICE_CLASS_BATTERY
    _attr_state_class = STATE_CLASS_MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_entity_category = ENTITY_CATEGORY_DIAGNOSTIC

    @property
    def name(self) -> str:
        return self._lock().description + " Battery Level"

    @property
    def unique_id(self) -> str:
        return self._lock().id + "_battery_level"

    @property
    def state(self) -> StateType:
        return self._lock().battery_status


class GlueHomeLastLockEventTypeEntity(GlueHomeBaseEntity, SensorEntity):
    @property
    def name(self) -> str:
        return self._lock().description + " Last Lock Event Type"

    @property
    def unique_id(self) -> str:
        return self._lock().id + "_last_lock_event_type"

    @property
    def state(self) -> StateType:
        return self._lock().last_lock_event_type


class GlueHomeLastLockEventTimeEntity(GlueHomeBaseEntity, SensorEntity):
    _attr_device_class = DEVICE_CLASS_TIMESTAMP
    _attr_entity_category = ENTITY_CATEGORY_DIAGNOSTIC

    @property
    def name(self) -> str:
        return self._lock().description + " Last Lock Event Time"

    @property
    def unique_id(self) -> str:
        return self._lock().id + "_last_lock_event_time"

    @property
    def state(self) -> StateType:
        return self._lock().last_lock_event_time
