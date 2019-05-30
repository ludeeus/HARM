"""
Custom element manager for community created elements.

For more details about this component, please refer to the documentation at
https://custom-components.github.io/hacs/
"""
# pylint: disable=not-an-iterable, unused-argument
import logging
import os.path
import json
import asyncio
import aiohttp
from datetime import datetime, timedelta
from pkg_resources import parse_version
import voluptuous as vol
from homeassistant.const import EVENT_HOMEASSISTANT_START, __version__ as HAVERSION
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.event import async_track_time_interval, async_call_later
from custom_components.hacs.blueprints import HacsBase as hacs, HacsRepositoryIntegration
from custom_components.hacs.const import (
    CUSTOM_UPDATER_LOCATIONS,
    STARTUP,
    PROJECT_URL,
    ISSUE_URL,
    CUSTOM_UPDATER_WARNING,
    NAME_LONG,
    NAME_SHORT,
    DOMAIN_DATA,
    ELEMENT_TYPES,
    VERSION,
    IFRAME,
    BLACKLIST,
    STORAGE_VERSION,
)
from custom_components.hacs.handler.storage import (
    data_migration,
)

from custom_components.hacs.frontend.views import (
    HacsStaticView,
    HacsErrorView,
    HacsPluginView,
    HacsOverviewView,
    HacsStoreView,
    HacsSettingsView,
    HacsRepositoryView,
    HacsAPIView,
)

DOMAIN = "{}".format(NAME_SHORT.lower())

_LOGGER = logging.getLogger('custom_components.hacs')

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({vol.Required("token"): cv.string})}, extra=vol.ALLOW_EXTRA
)


async def async_setup(hass, config):  # pylint: disable=unused-argument
    """Set up this component."""
    _LOGGER.info(STARTUP)
    config_dir = hass.config.path()
    github_token = config[DOMAIN]["token"]
    commander = HacsCommander()

    # Configure HACS
    await configure_hacs(hass, github_token, config_dir)

    for item in hacs.url_path:
        _LOGGER.critical(f"{item}: {hacs.url_path[item]}")

    # Check if custom_updater exists
    for location in CUSTOM_UPDATER_LOCATIONS:
        if os.path.exists(location.format(config_dir)):
            msg = CUSTOM_UPDATER_WARNING.format(location.format(config_dir))
            _LOGGER.critical(msg)
            return False

    # Check if HA is the required version.
    if parse_version(HAVERSION) < parse_version('0.92.0'):
        _LOGGER.critical("You need HA version 92 or newer to use this integration.")
        return False

    # Setup startup tasks
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, hacs().startup_tasks())

    # Register the views
    hass.http.register_view(HacsStaticView())
    hass.http.register_view(HacsErrorView())
    hass.http.register_view(HacsPluginView())
    hass.http.register_view(HacsStoreView())
    hass.http.register_view(HacsOverviewView())
    hass.http.register_view(HacsSettingsView())
    hass.http.register_view(HacsRepositoryView())
    hass.http.register_view(HacsAPIView())

    hacs.data["commander"] = commander

    # Add to sidepanel
    await hass.components.frontend.async_register_built_in_panel(
        "iframe",
        IFRAME["title"],
        IFRAME["icon"],
        IFRAME["path"],
        {"url": hacs.url_path["overview"]},
        require_admin=IFRAME["require_admin"],
    )

    # Mischief managed!
    return True


async def configure_hacs(hass, github_token, hass_config_dir):
    """Configure HACS."""
    from custom_components.hacs.aiogithub import AIOGitHub
    from custom_components.hacs.hacsmigration import HacsMigration
    from custom_components.hacs.hacsstorage import HacsStorage

    hacs.migration = HacsMigration()
    hacs.storage = HacsStorage()

    hacs.aiogithub = AIOGitHub(github_token, hass.loop, aiohttp.ClientSession())

    hacs.hass = hass
    hacs.config_dir = hass_config_dir
    hacs.blacklist = hacs.const.BLACKLIST

class HacsCommander(hacs):
    """HACS Commander class."""

    async def check_for_hacs_update(self, notarealargument=None):
        """Check for hacs update."""
        _LOGGER.debug("Checking for HACS updates...")
        try:
            repository = await self.aiogithub.get_repo("custom-components/hacs")
            release = await repository.get_releases(True)
            self.data["hacs"]["remote"] = release.tag_name

        except Exception as error:  # pylint: disable=broad-except
            _LOGGER.debug(error)

    async def setup_recuring_tasks(self):
        """Setup recuring tasks."""

        hacs_scan_interval = timedelta(minutes=10)
        full_element_scan_interval = timedelta(minutes=30)

        async_track_time_interval(self.hass, self.check_for_hacs_update, hacs_scan_interval)
        async_track_time_interval(self.hass, self.update_repositories, full_element_scan_interval)
