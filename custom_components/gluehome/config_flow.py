import logging
from typing import Optional

from homeassistant import config_entries

from .api import GlueHomeApiKeysApi
from .exceptions import GlueHomeInvalidAuth
from .const import DOMAIN, CONF_API_KEY

import voluptuous as vol

_LOGGER = logging.getLogger(__name__)

CONF_USERNAME = "username"
CONF_PASSWORD = "password"

class GlueHomeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: Optional[dict] = None):
        errors = {}
        if user_input is not None:
            username = user_input[CONF_USERNAME]
            await self.async_set_unique_id(username)
            api = GlueHomeApiKeysApi(username, user_input[CONF_PASSWORD])
            try:
                api_key = await self.hass.async_add_executor_job(api.create_api_key)
            except GlueHomeInvalidAuth:
                errors["base"] = "invalid_auth"
            else:
                return self.async_create_entry(
                    title=username,
                    data={
                        CONF_API_KEY: api_key,
                    }
                )

        data_schema = vol.Schema({
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )
