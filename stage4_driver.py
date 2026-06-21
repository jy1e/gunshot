import json
import time
from abc import ABC, abstractmethod


def _load_serial_module():
    try:
        import serial
        return serial
    except ImportError as exc:
        raise ImportError(
            "pyserial is required for RCCarDriver. Install with `pip install pyserial`."
        ) from exc


def _load_selenium_modules():
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.service import Service as ChromeService
        from selenium.webdriver.edge.service import Service as EdgeService
        from webdriver_manager.chrome import ChromeDriverManager
        from webdriver_manager.microsoft import EdgeChromiumDriverManager
        return webdriver, By, WebDriverWait, EC, ChromeService, EdgeService, ChromeDriverManager, EdgeChromiumDriverManager
    except ImportError as exc:
        raise ImportError(
            "Selenium and webdriver-manager are required for Web/App driver. "
            "Install with `pip install selenium webdriver-manager`."
        ) from exc


def _load_selenium_modules():
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.service import Service as ChromeService
        from selenium.webdriver.edge.service import Service as EdgeService
        from webdriver_manager.chrome import ChromeDriverManager
        from webdriver_manager.microsoft import EdgeChromiumDriverManager
        return webdriver, By, WebDriverWait, EC, ChromeService, EdgeService, ChromeDriverManager, EdgeChromiumDriverManager
    except ImportError as exc:
        raise ImportError(
            "Selenium and webdriver-manager are required for Web/App driver. "
            "Install with `pip install selenium webdriver-manager`."
        ) from exc


class BaseDriver(ABC):
    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def send_command(self, cmd):
        pass

    @abstractmethod
    def scan_ports(self):
        pass


class RCCarDriver(BaseDriver):
    def __init__(self, port=None, baudrate=9600, timesleep=2):
        self.port = port
        self.baudrate = baudrate
        self.timesleep = timesleep
        self.ser = None

    def connect(self):
        if not self.port:
            raise ValueError("Serial port is required for RCCarDriver.")
        if self.ser and self.ser.is_open:
            return self.ser
        serial = _load_serial_module()
        self.ser = serial.Serial(self.port, self.baudrate, timeout=2)
        time.sleep(self.timesleep)
        return self.ser

    def send_command(self, cmd):
        self.connect()
        self.ser.write(json.dumps({"cmd": cmd}).encode("utf-8"))
        raw = self.ser.readline().decode("utf-8").strip()
        if not raw:
            return None
        return json.loads(raw)

    def scan_ports(self):
        serial = _load_serial_module()
        try:
            from serial.tools import list_ports
        except ImportError:
            raise ImportError(
                "pyserial is required for RCCarDriver port scanning. "
                "Install with `pip install pyserial`."
            )
        return [port.device for port in list_ports.comports()]

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()


class WebAppDriver(BaseDriver):
    def __init__(self, base_url=None, browser="chrome", driver_instance=None):
        self.base_url = base_url
        self.browser = browser
        self.driver = driver_instance

    def connect(self):
        if self.driver is not None:
            return self.driver
        (
            webdriver,
            By,
            WebDriverWait,
            EC,
            ChromeService,
            EdgeService,
            ChromeDriverManager,
            EdgeChromiumDriverManager,
        ) = _load_selenium_modules()

        self.webdriver = webdriver
        self.By = By
        self.WebDriverWait = WebDriverWait
        self.EC = EC

        if self.browser.lower() == "chrome":
            self.driver = webdriver.Chrome(
                service=ChromeService(ChromeDriverManager().install())
            )
        elif self.browser.lower() == "edge":
            self.driver = webdriver.Edge(
                service=EdgeService(EdgeChromiumDriverManager().install())
            )
        else:
            raise ValueError(f"Unsupported browser: {self.browser}")

        if self.base_url:
            self.driver.get(self.base_url)
        time.sleep(1)
        return self.driver

    def send_command(self, cmd):
        driver = self.connect()
        wait = self.WebDriverWait(driver, 5)

        if cmd == "go_to_board":
            btn = wait.until(self.EC.element_to_be_clickable(
                (self.By.XPATH, "//button[contains(text(),'게시판 바로가기')]")))
            btn.click()
            time.sleep(1)
            visible = driver.find_element(self.By.ID, "listScreen").is_displayed()
            return {"screen": "listScreen" if visible else "unknown"}

        if cmd == "write_post":
            driver.find_element(self.By.XPATH, "//button[contains(text(),'작성')]").click()
            time.sleep(0.5)
            driver.find_element(self.By.ID, "author").send_keys("테스터")
            driver.find_element(self.By.ID, "title").send_keys("테스트 제목")
            driver.find_element(self.By.ID, "content").send_keys("테스트 내용입니다.")
            driver.find_element(self.By.XPATH, "//button[contains(text(),'작성완료')]").click()
            time.sleep(0.5)
            visible = driver.find_element(self.By.ID, "listScreen").is_displayed()
            return {"screen": "listScreen" if visible else "unknown"}

        if cmd == "list_posts":
            visible = driver.find_element(self.By.ID, "listScreen").is_displayed()
            rows = driver.find_elements(self.By.CLASS_NAME, "post-item")
            return {"screen": "listScreen" if visible else "unknown", "post_count": len(rows)}

        if cmd == "view_post":
            rows = driver.find_elements(self.By.CLASS_NAME, "post-item")
            if not rows:
                return {"error": "error"}
            rows[0].find_element(self.By.TAG_NAME, "a").click()
            time.sleep(0.5)
            visible = driver.find_element(self.By.ID, "readScreen").is_displayed()
            views = driver.find_element(self.By.ID, "readViews").text
            return {"screen": "readScreen" if visible else "unknown", "views": int(views)}

        if cmd == "cancel_write":
            driver.find_element(self.By.XPATH, "//button[contains(text(),'작성완료')]" ).click()
            time.sleep(0.5)
            visible = driver.find_element(self.By.ID, "cancelConfirmScreen").is_displayed()
            return {"screen": "cancelConfirmScreen" if visible else "unknown"}

        if cmd == "go_to_home":
            driver.find_element(self.By.XPATH, "//button[contains(text(),'Home')]" ).click()
            time.sleep(0.5)
            visible = driver.find_element(self.By.ID, "homeScreen").is_displayed()
            return {"screen": "homeScreen" if visible else "unknown"}

        return {"error": "error"}

    def scan_ports(self):
        return []

    def close(self):
        if self.driver is not None:
            self.driver.quit()
            self.driver = None


class NullDriver(BaseDriver):
    def connect(self):
        return None

    def send_command(self, cmd):
        return None

    def scan_ports(self):
        return []

    def close(self):
        return None


def create_driver(driver_type, **kwargs):
    normalized = (driver_type or "").strip().lower()
    if normalized in ("rc_car", "rc car", "rccar"):
        return RCCarDriver(
            port=kwargs.get("port"),
            baudrate=kwargs.get("baudrate", 9600),
            timesleep=kwargs.get("timesleep", 2),
        )
    if normalized in ("web_app", "web/app", "web", "app"):
        return WebAppDriver(
            base_url=kwargs.get("base_url"),
            browser=kwargs.get("browser", "chrome"),
            driver_instance=kwargs.get("driver_instance"),
        )
    if normalized in ("none", "null", "tc_only", "tc generation only"):
        return NullDriver()
    raise ValueError(f"Unsupported driver type: {driver_type}")