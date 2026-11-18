from qa_mobile.pages.dashboard_page import DashboardPage
from qa_mobile.pages.history_page import HistoryPage


def test_dashboard_exibe_saldo(driver, app_package):
    dashboard = DashboardPage(driver)
    dashboard.abrir_home()
    dashboard.validar_saldo_visivel()

    assert driver.current_package == app_package


def test_navegacao_para_historico(driver, app_package):
    dashboard = DashboardPage(driver)
    historico = HistoryPage(driver)

    dashboard.abrir_home()
    dashboard.abrir_historico()
    historico.validar_filtros_visiveis()

    assert driver.current_package == app_package


def test_retorno_do_historico_ao_dashboard(driver, app_package):
    dashboard = DashboardPage(driver)
    historico = HistoryPage(driver)

    dashboard.abrir_home()
    dashboard.abrir_historico()
    historico.validar_filtros_visiveis()
    dashboard.abrir_home()
    dashboard.validar_saldo_visivel()

    assert driver.current_package == app_package
