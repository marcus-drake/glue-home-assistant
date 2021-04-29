from typing import Optional

import requests
from requests.auth import AuthBase, HTTPBasicAuth

from const import GLUE_HOME_HOST
from exceptions import GlueHomeNetworkError, GlueHomeInvalidAuth, GlueHomeServerError

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
        return response

    def create_api_key(self):
        response = self.request("post", "/v1/api-keys",
                                {"name": "libgluehome", "scopes": ["events.read", "locks.read", "locks.write"]})
        return response.json().apiKey


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
        return self._state.id

    @property
    def description(self):
        return self._state.description

    @property
    def serialNumber(self):
        return self._state.serialNumber

    @property
    def firmwareVersion(self):
        return self._state.firmwareVersion

    @property
    def batteryStatus(self):
        return self._state.batteryStatus

    @property
    def connectionStatus(self):
        return self._state.connectionStatus

    @property
    def lastLockEventType(self):
        return self._state.lastLockEvent.eventType

    @property
    def lastLockEventDate(self):
        return self._state.lastLockEvent.lastLockEventDate

    def operation(self, operation: str):
        response = request("post", "/v1/locks/" + self._state.id + "/operations", HTTPApiKeyAuth(self._api_key),
                           {type: operation})
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
        raise GlueHomeServerError
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
