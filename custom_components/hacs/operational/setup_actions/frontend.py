from hacs_frontend.version import VERSION as FE_VERSION

from custom_components.hacs.share import get_hacs
from custom_components.hacs.helpers.functions.information import get_frontend_version


async def async_setup_frontend():
    """Configure the HACS frontend elements."""
    from custom_components.hacs.http import HacsFrontend

    hacs = get_hacs()

    hacs.hass.http.register_view(HacsFrontend())
    hacs.frontend.version_running = FE_VERSION
    hacs.frontend.version_expected = await hacs.hass.async_add_executor_job(
        get_frontend_version
    )

    # Add to sidepanel
    custom_panel_config = {
        "name": "hacs-frontend",
        "embed_iframe": False,
        "trust_external": False,
        "js_url": f"/hacsfiles/frontend-{hacs.frontend.version_running}.js",
    }

    config = {}
    config["_panel_custom"] = custom_panel_config

    hacs.hass.components.frontend.async_register_built_in_panel(
        component_name="custom",
        sidebar_title=hacs.configuration.sidepanel_title,
        sidebar_icon=hacs.configuration.sidepanel_icon,
        frontend_url_path="hacs",
        config=config,
        require_admin=True,
    )

    if "frontend_extra_module_url" not in hacs.hass.data:
        hacs.hass.data["frontend_extra_module_url"] = set()
    hacs.hass.data["frontend_extra_module_url"].add("/hacsfiles/iconset.js")
