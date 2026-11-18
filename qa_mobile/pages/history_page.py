from selenium.webdriver.support.ui import WebDriverWait


class HistoryPage:
    FILTROS = ("All", "Send", "Request", "Top up")

    def __init__(self, driver, timeout):
        self.wait = WebDriverWait(driver, timeout)

    def validar_filtros_visiveis(self):
        def filtros_presentes(driver):
            source = driver.page_source
            return all(f'text="{filtro}"' in source for filtro in self.FILTROS)

        self.wait.until(
            filtros_presentes, message=f"Filtros esperados no Histórico: {self.FILTROS}"
        )
        return self
