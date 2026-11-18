from qa_mobile.config import session_config


def test_configuracao_padrao_preserva_estado_e_seleciona_emulador():
    url, options = session_config({})

    assert url == "http://127.0.0.1:4723"
    assert options.to_w3c()["capabilities"]["alwaysMatch"] == {
        "platformName": "Android",
        "appium:automationName": "UiAutomator2",
        "appium:deviceName": "emulator-5554",
        "appium:udid": "emulator-5554",
        "appium:appPackage": "by.alexandr7035.banking.debug",
        "appium:noReset": True,
    }


def test_configuracao_alternativa_nao_depende_do_ambiente_do_processo():
    url, options = session_config({
        "BANKING_APPIUM_URL": "http://127.0.0.1:4725",
        "BANKING_ANDROID_UDID": "emulator-5556",
        "BANKING_APP_PACKAGE": "by.alexandr7035.banking",
    })

    assert url == "http://127.0.0.1:4725"
    assert options.udid == "emulator-5556"
    assert options.app_package == "by.alexandr7035.banking"


def test_configuracoes_sao_independentes_entre_sessoes():
    _, first = session_config({})
    first.udid = "emulator-5556"

    _, second = session_config({})

    assert second.udid == "emulator-5554"
