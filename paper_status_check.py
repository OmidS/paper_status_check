from dotenv import load_dotenv
load_dotenv()  # take environment variables from .env.

import os, time, logging, json, csv
from pathlib import Path

from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chromium.service import ChromiumService
from selenium.webdriver.chromium.options import ChromiumOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)

class NatureCrawler():
    def __init__(self, username=None, password=None, driver=None, driver_path=None,
                home_url='https://mts-nn.nature.com/cgi-bin/main.plex?form_type=home', 
                login_url='https://mts-nn.nature.com/cgi-bin/main.plex?form_type=home', 
                paper_url='',
                cookie_store_file=None,
                snapshot_dir='',
                status_dir='',
                take_screenshots=True,
                implicit_wait=None
            ):
        self.home_url = home_url
        self.login_url = login_url
        self.paper_url = paper_url
        self.snapshot_dir = snapshot_dir
        self.status_dir = status_dir
        self.take_screenshots = take_screenshots
        if username is None:
            username = os.environ.get('NATURE_USERNAME', '')
        if password is None:
            password = os.environ.get('NATURE_PASSWORD', '')
        self.username = username
        self.password = password
        if driver is None:
            driver = os.environ.get('SELENIUM_DRIVER', 'chrome')
        self.driver = driver
        self.headless = os.environ.get('SELENIUM_HEADLESS', 'false').lower() == 'true'
        if cookie_store_file is None:
            cookie_store_file = str(Path(__file__).parent.resolve() / f'{self.driver}_cookies.json')
        self.cookie_store_file = cookie_store_file
        if driver_path is None:
            if self.driver == 'firefox':
                driver_path = os.environ.get('FIREFOX_DRIVER_PATH')
            elif self.driver == 'chrome':
                driver_path = os.environ.get('CHROME_DRIVER_PATH')
            elif self.driver == 'chromium':
                driver_path = os.environ.get('CHROMIUM_DRIVER_PATH')
        logger.info(f'Using Selenium with {self.driver} driver (path: {driver_path})')
        self.browser = None
        if self.driver == 'firefox':
            options = FirefoxOptions()
            if os.environ.get('FIREFOX_BINARY_PATH'):
                options.binary_location = os.environ.get('FIREFOX_BINARY_PATH')
            if self.headless:
                options.add_argument("--headless")
                options.add_argument('--disable-gpu')
            self.browser = webdriver.Firefox(service=FirefoxService(driver_path), options=options)
        elif self.driver == 'chrome':
            options = ChromeOptions()
            if self.headless:
                # options.add_argument('--headless')
                options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            if os.environ.get('CHROME_USER_DATA_DIR'):
                options.add_argument(r'--profile-directory='+os.environ.get('CHROME_PROFILE', 'Auto')+'') #e.g. Profile 3
                options.add_argument(r'--user-data-dir='+os.environ.get('CHROME_USER_DATA_DIR')+'') #e.g. C:\Users\You\AppData\Local\Google\Chrome\User Data
            if driver_path is None or driver_path == '':
                service = ChromeService(ChromeDriverManager().install())
            else:
                service = ChromeService(executable_path=driver_path)
            self.browser = webdriver.Chrome(service=service, options=options)
        elif self.driver == 'chromium':
            options = ChromiumOptions()
            if self.headless:
                options.add_argument('--headless')
                options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            self.browser = webdriver.Chrome(service=ChromeService(driver_path), options=options)
        if implicit_wait is None:
            implicit_wait = int(os.environ.get('SELENIUM_WAIT', '30'))
        self.implicit_wait = implicit_wait
        if self.implicit_wait > 0:
            self.browser.implicitly_wait(self.implicit_wait) # Wait for up to 10s when looking for DOM elements
            logger.info(f'Will wait up to {self.implicit_wait}s for elements to load')
        self.import_cookies() # Try to continue from latest cookie session
        self.logged_in = self.check_login() # Check if we are logged in

    def screenshot(self, name, save_image=True, save_html=True):
        if self.snapshot_dir is not None and self.snapshot_dir:
            screenshot_dir = self.snapshot_dir
        else:
            screenshot_dir = Path(__file__).parent.resolve() / f'screenshots'
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        name_prefix = time.strftime("%Y%m%d_%H%M%S")
        file_name = screenshot_dir / f'{name_prefix}_{name}'
        if save_image:
            self.browser.save_screenshot(file_name)
            logger.info(f'Saving screenshot as {file_name}')
        if save_html:
            save_file_html = file_name.parent / (file_name.stem+'.html')
            with open(save_file_html, "w", encoding='utf-8') as f:
                f.write(self.browser.page_source)
            logger.info(f'Saving page html as {save_file_html}')

    def save_status(self, name, data):
        if self.status_dir is not None and self.status_dir:
            status_dir = self.status_dir
        else:
            status_dir = Path(__file__).parent.resolve() / f'status'
        status_dir.mkdir(parents=True, exist_ok=True)
        file_name = status_dir / f'{name}.csv'
        with open(file_name, 'a+', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(data)
            logger.info(f'Added log line {data} to {file_name}')

    def export_cookies(self, file_path=None):
        if file_path is None:
            file_path = self.cookie_store_file
        # Store cookies in a file
        logger.info(f'Exporting cookies to {file_path}')
        cookies = self.browser.get_cookies()
        with open(file_path, 'w') as file:
            json.dump(cookies, file) 
    
    def import_cookies(self, file_path=None):
        if file_path is None:
            file_path = self.cookie_store_file
        if os.path.exists(file_path):
            logger.info(f'Importing cookies from {file_path}')
            # Load cookies to a variable from a file
            with open(file_path, 'r') as file:
                cookies = json.load(file)
            # Goto the same URL
            self.browser.get(self.home_url)
            # Set stored cookies to maintain the session
            for cookie in cookies:
                self.browser.add_cookie(cookie)
        else:        
            logger.info(f'No cookies found at {file_path}')

    def check_login(self):
        logger.info(f'Checking if we are logged in')
        self.browser.get(self.paper_url)
        try:
            username_field = self.browser.find_element(By.CSS_SELECTOR, 'input[name="login"]') # Query selector to select input field for username
            logged_in = False
        except Exception as e:
            logger.info(f'Could not locate the login button on the paper page, will assume that we are not logged in')
            logged_in = True
        if self.take_screenshots:
            self.screenshot('login_check.png')
        self.logged_in = logged_in
        return self.logged_in

    def accept_cookies(self):
        # Accept cookies
        self.browser.implicitly_wait(0.5) # Wait less since this often is not there
        try:
            lm_link = self.browser.find_element(By.PARTIAL_LINK_TEXT, 'OK')
            lm_link.click()
        except Exception as e:
            print(e)
        self.browser.implicitly_wait(self.implicit_wait) # Wait for up to 10s when looking for DOM elements

    def login(self):
        logger.info(f'Logging in as {self.username}')
        self.browser.get(self.login_url)
        self.accept_cookies()
        logger.info(f'Entering username')
        username_field = self.browser.find_element(By.CSS_SELECTOR, 'input[name="login"]') # Query selector to select input field for username
        username_field.send_keys(self.username)
        if self.take_screenshots:
            self.screenshot('login_username.png')
        logger.info(f'Entering password')
        password_field = self.browser.find_element(By.CSS_SELECTOR, 'input[type="password"]') # Query selector to select input field for password
        password_field.send_keys(self.password)
        if self.take_screenshots:
            self.screenshot('login_password.png')
        password_field.send_keys(Keys.ENTER) # Enter the password to login
        wait = WebDriverWait(self.browser, self.implicit_wait)
        wait.until(EC.any_of(EC.title_contains('Account'), EC.title_contains('Nature Neuroscience'))) # Wait up to 10s until redirected to home
        self.logged_in = 'Account' in self.browser.title or 'Nature Neuroscience' in self.browser.title
        if self.take_screenshots:
            self.screenshot('home_page.png')
        self.accept_cookies()
        # try:
        #     btn = self.browser.find_element(By.CSS_SELECTOR, 'input[value="Do not logout"]')
        #     btn.click()
        # except Exception as e:
        #     print(e)

    def check_status(self, paper_url=None, dry_run=True, log_file=None):
        if paper_url is None:
            paper_url = self.paper_url
        logger.info(f'Checking status of paper at ({paper_url} chars)')
        # self.browser.get(self.home_url)
        if self.take_screenshots:
            self.screenshot('home_page.png')

        try:
            # Option 1, using the Springer Nature account page
            lm_link = self.browser.find_element(By.PARTIAL_LINK_TEXT, 'Modify My Springer Nature Account')
            account_link = lm_link.get_attribute('href')
            self.browser.get(account_link)
            self.accept_cookies()
            if self.take_screenshots:
                self.screenshot('account.png')
            lm_link = self.browser.find_element(By.PARTIAL_LINK_TEXT, 'Manuscript(s)')
            manuscripts_link = lm_link.get_attribute('href')
            self.browser.get(manuscripts_link)
            self.accept_cookies()

            s_header = self.browser.find_element(By.PARTIAL_LINK_TEXT, 'Submitted')
            paper_links = s_header.find_elements(By.XPATH, '../../ul')
            statuses = [paper_link.find_element(By.CSS_SELECTOR, '.status').text for paper_link in paper_links]
            manuscript_ids = [paper_link.find_element(By.TAG_NAME, 'a').text for paper_link in paper_links]
            hrefs = [paper_link.find_element(By.TAG_NAME, 'a').get_attribute('href') for paper_link in paper_links]
        except Exception as e:
            # Option 2, using the journal page
            lm_link = self.browser.find_element(By.PARTIAL_LINK_TEXT, 'Live Manuscript')
            manuscripts_link = lm_link.get_attribute('href')
            self.browser.get(manuscripts_link)
            self.accept_cookies()
            paper_links = self.browser.find_elements(By.PARTIAL_LINK_TEXT, 'Manuscript')
            hrefs = [paper_link.get_attribute('href') for paper_link in paper_links]
            manuscript_ids = ['' for paper_link in paper_links]
            statuses = ['' for paper_link in paper_links]

        for href, home_man_id, home_status in zip(hrefs, manuscript_ids, statuses):
            try:
                self.browser.get(href)
                if self.take_screenshots:
                    self.screenshot('status.png')
                # Extract status
                cs_elem = self.browser.find_element(By.LINK_TEXT, "Current Stage")
                row_elem = cs_elem.find_element(By.XPATH, '../..')
                tds = row_elem.find_elements(By.TAG_NAME, "td")
                current_status = tds[0].text
                # Extract manuscript id
                tbody_elem = row_elem.find_element(By.XPATH, '..')
                tds = tbody_elem.find_elements(By.TAG_NAME, "td")
                manuscript_id = tds[0].text
            except Exception as e:
                logger.info(f'Could not go to manuscript page, will save info based on home page')
                current_status = ''
                manuscript_id = home_man_id
            self.save_status(name='status', data=[
                time.strftime("%Y%m%d_%H%M%S"), 
                manuscript_id, 
                current_status,
                home_status
            ])
        
    def close(self, export_cookies=True):
        logger.info(f'Closing browser')
        if export_cookies:
            self.export_cookies() # Export cookies before closing browser
        if self.browser:
            self.browser.close()
        
    def __del__(self):
        self.close()
        
    
if __name__ == '__main__':
    crawler = NatureCrawler(
        snapshot_dir=Path(__file__).parent.resolve() / f'screenshots',
        status_dir=Path(__file__).parent.resolve(),
        paper_url='https://mts-nn.nature.com/cgi-bin/main.plex?form_type=home'
    )
    if not crawler.logged_in:
        crawler.login()
        time.sleep(5)
    crawler.check_status()
    try:
        crawler.close()
    except Exception as e:
        print(e)
