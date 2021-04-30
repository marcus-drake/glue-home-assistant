import logging
from typing import Optional

import requests
from requests.auth import AuthBase, HTTPBasicAuth

from .const import GLUE_HOME_HOST
from .exceptions import GlueHomeNetworkError, GlueHomeInvalidAuth, GlueHomeServerError, GlueHomeNonSuccessfulResponse, \
    GlueHomeException

_LOGGER = logging.getLogger(__name__)


UNKNOWN_STATES = [
    'unknown'
]

LOCKED_STATES = [
    'pressAndGo',
    'localLock',
    'manualLock',
    'remoteLock',
]

UNLOCKED_STATES = [
    'localUnlock',
    'manualUnlock',
    'remoteUnlock',
]

SUCCESSFUL_CONNECTED_STATUSES = [
    'connected',
    'busy'
]


class GlueHomeApiKeysApi:
    _HOST = GLUE_HOME_HOST

    def __init__(self, username: str, password: str):
        self._username = username
        self._password = password

    def request(
            self,
            method: str,
            path: str,
            data: Optional[dict] = None,
    ) -> requests.Response:
        try:
            response = requests.request(
                method,
                GLUE_HOME_HOST + path,
                json=data,
                headers={
                    "Content-Type": "application/json"
                },
                auth=HTTPBasicAuth(self._username, self._password)
            )
        except requests.RequestException:
            raise GlueHomeNetworkError
        if response.status_code in [401, 403]:
            raise GlueHomeInvalidAuth
        if 500 <= response.status_code < 600:
            raise GlueHomeServerError
        if 200 > response.status_code >= 300:
            raise GlueHomeNonSuccessfulResponse
        return response

    def create_api_key(self):
        _LOGGER.info("Creating API key")
        response = self.request("post", "/v1/api-keys",
                                {"name": "libgluehome", "scopes": ["events.read", "locks.read", "locks.write"]})
        return response.json()["apiKey"]


class GlueHomeLocksApi:
    def __init__(self, api_key: str):
        self._api_key = api_key

    def get_locks(self):
        response = request("get", "/v1/locks", auth=HTTPApiKeyAuth(self._api_key))
        locks = []
        for lock_state in response.json():
            locks.append(GlueHomeLock(lock_state, self._api_key))
        return locks


class GlueHomeLock:
    def __init__(self, state, api_key):
        self._state = state
        self._api_key = api_key

    @property
    def id(self):
        return self._state["id"]

    @property
    def description(self):
        return self._state["description"]

    @property
    def serial_number(self):
        return self._state["serialNumber"]

    @property
    def model_name(self):
        return self.serial_number[0:4]

    @property
    def firmware_version(self):
        return self._state["firmwareVersion"]

    @property
    def battery_status(self):
        return self._state["batteryStatus"]

    @property
    def connection_status(self):
        return self._state["connectionStatus"]

    @property
    def last_lock_event_type(self):
        if "lastLockEvent" in self._state and "eventType" in self._state["lastLockEvent"]:
            return self._state["lastLockEvent"]["eventType"]
        return None

    @property
    def last_lock_event_time(self):
        if "lastLockEvent" in self._state and "eventTime" in self._state["lastLockEvent"]:
            return self._state["lastLockEvent"]["eventTime"]
        return None

    def operation(self, operation: str):
        try:
            _LOGGER.info(f"Running operation {operation} on lock {self.id}")
            response = request("post", "/v1/locks/" + self.id + "/operations", HTTPApiKeyAuth(self._api_key),
                               {"type": operation})
        except GlueHomeException as ex:
            _LOGGER.error(f"Failed to run operation {operation} on lock ${self.id}")
            raise ex
        return response.json()


def request(
        method: str,
        path: str,
        auth: AuthBase,
        data: Optional[dict] = None,
) -> requests.Response:
    try:
        response = requests.request(
            method,
            GLUE_HOME_HOST + path,
            json=data,
            headers={
                "Content-Type": "application/json"
            },
            auth=auth
        )
    except requests.RequestException:
        raise GlueHomeNetworkError
    if response.status_code in [401, 403]:
        raise GlueHomeInvalidAuth
    if 500 <= response.status_code < 600:
        raise GlueHomeServerError(response.status_code)
    return response


class HTTPApiKeyAuth(AuthBase):
    def __init__(self, api_key):
        self.api_key = api_key

    def __eq__(self, other):
        return self.api_key == getattr(other, "api_key", None)

    def __ne__(self, other):
        return not self == other

    def __call__(self, r):
        r.headers["Authorization"] = f"Api-Key {self.api_key}"
        return r
