def test_dashboard_exibe_saldo(dashboard, driver, app_package):
    dashboard.validar_saldo_visivel()

    assert driver.current_package == app_package


def test_navegacao_para_historico(dashboard, historico, driver, app_package):
    dashboard.abrir_historico()
    historico.validar_filtros_visiveis()

    assert driver.current_package == app_package


def test_retorno_do_historico_ao_dashboard(dashboard, historico, driver, app_package):
    dashboard.abrir_historico()
    historico.validar_filtros_visiveis()
    dashboard.abrir_home()
    dashboard.validar_saldo_visivel()

    assert driver.current_package == app_package
