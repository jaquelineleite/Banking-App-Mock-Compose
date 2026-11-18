from selenium.webdriver.support.ui import WebDriverWait


class HistoryPage:
    FILTROS = ("All", "Send", "Request", "Top up")

    def __init__(self, driver):
        self.driver = driver

    def validar_filtros_visiveis(self):
        def filtros_presentes(driver):
            source = driver.page_source
            return all(f'text="{filtro}"' in source for filtro in self.FILTROS)

        WebDriverWait(self.driver, 20).until(
            filtros_presentes, message=f"Filtros esperados no Histórico: {self.FILTROS}"
        )
        return self
