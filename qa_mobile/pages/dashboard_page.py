from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support import expected_conditions as conditions
from selenium.webdriver.support.ui import WebDriverWait


class DashboardPage:
    HOME = 'new UiSelector().text("Home")'
    HISTORY = 'new UiSelector().text("History")'

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 20)

    def abrir_home(self):
        self.wait.until(
            conditions.element_to_be_clickable((AppiumBy.ANDROID_UIAUTOMATOR, self.HOME))
        ).click()
        return self

    def validar_saldo_visivel(self):
        self.wait.until(
            lambda driver: "My Balance" in driver.page_source,
            message="O rótulo My Balance não apareceu no Dashboard.",
        )
        return self

    def abrir_historico(self):
        self.wait.until(
            conditions.element_to_be_clickable((AppiumBy.ANDROID_UIAUTOMATOR, self.HISTORY))
        ).click()
        return self
