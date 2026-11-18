from collections.abc import Mapping

from appium.options.android import UiAutomator2Options


DEFAULT_APP_PACKAGE = "by.alexandr7035.banking.debug"


def session_config(env: Mapping[str, str]) -> tuple[str, UiAutomator2Options]:
    server_url = env.get("BANKING_APPIUM_URL", "http://127.0.0.1:4723")
    udid = env.get("BANKING_ANDROID_UDID", "emulator-5554")
    app_package = env.get("BANKING_APP_PACKAGE", DEFAULT_APP_PACKAGE)

    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.automation_name = "UiAutomator2"
    options.device_name = udid
    options.udid = udid
    options.app_package = app_package
    options.no_reset = True
    return server_url, options
