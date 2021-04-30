"""Glue Home"""
import logging

from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_API_KEY

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config: config_entries.ConfigEntry):
    _LOGGER.info("Setting up Glue Home")
    hass.data.setdefault(DOMAIN, {})
    if not config.data[CONF_API_KEY]:
        return False

    await hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(config, "lock")
    )
    return True
