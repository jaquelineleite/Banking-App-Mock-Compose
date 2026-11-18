import os

import pytest
from appium import webdriver

from qa_mobile.config import session_config


@pytest.fixture
def appium_config():
    return session_config(os.environ)


@pytest.fixture
def app_package(appium_config):
    _, options = appium_config
    return options.app_package


@pytest.fixture
def driver(appium_config):
    server_url, options = appium_config
    session = webdriver.Remote(server_url, options=options)
    try:
        yield session
    finally:
        session.quit()
