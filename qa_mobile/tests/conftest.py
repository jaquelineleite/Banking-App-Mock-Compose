import os

import pytest
from appium import webdriver
from selenium.common.exceptions import TimeoutException

from qa_mobile.config import session_config, ui_wait_seconds
from qa_mobile.pages.dashboard_page import DashboardPage
from qa_mobile.pages.history_page import HistoryPage


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


@pytest.fixture
def ui_timeout():
    return ui_wait_seconds(os.environ)


@pytest.fixture
def dashboard(driver, ui_timeout):
    page = DashboardPage(driver, ui_timeout)
    try:
        page.abrir_home()
        page.validar_saldo_visivel()
    except TimeoutException as error:
        pytest.fail(
            "O Dashboard não ficou disponível na preparação do cenário. "
            "Confira o idioma inglês, o onboarding e se o app está desbloqueado. "
            f"Detalhe: {error.msg or 'a aba Home não ficou disponível.'}",
            pytrace=False,
        )
    return page


@pytest.fixture
def historico(driver, ui_timeout):
    return HistoryPage(driver, ui_timeout)
