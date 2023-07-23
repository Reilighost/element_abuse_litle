import random
import pandas as pd
import colorlog
import requests
import time
import json
from selenium.common.exceptions import NoSuchElementException
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import StaleElementReferenceException
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import sys
import os



if not os.path.isfile('config_user.json'):

    print("You need to set parameter, they can be change any time in 'config_user' file")
    Invite_per_linc = input("Enter how mach ref you need per linc: ")
    print("New you need you metamask identificator, it look like this:")
    print("chrome-extension://hpbbepbnmcaoajhapnmjfjakmaacabni/home.html#")
    print("You need only this parth 'hpbbepbnmcaoajhapnmjfjakmaacabni'")
    identificator = input("Enter you personal metamask identificator: ")
    max_workers = input("Enter how mach profile should run at one moment: ")
    config_user = {
        'Invite_per_linc': Invite_per_linc,
        'identificator': identificator,
        'max_workers': max_workers,
    }

    with open('config_user.json', 'w') as f:
        json.dump(config_user, f)

    print("Configuration saved successfully.")
else:
    print("Configuration file already exists, it can be change any time in 'config_user' file")

with open('config_user.json', 'r') as f:
    config_user = json.load(f)


Invite_per_linc = int(config_user['Invite_per_linc'])
identificator = str(config_user['identificator'])
max_workers = int(config_user['max_workers'])





metamask_url = f"chrome-extension://{identificator}/home.html#"
data_path = "Data.xlsx"


data = pd.read_excel(data_path, engine='openpyxl', dtype={"Profile ID": str, "Password": str})
start_idx = int(input("Enter the starting index of the profile range: ")) - 1
end_idx = int(input("Enter the ending index of the profile range: ")) - 1



class ReferralSystem:
    def __init__(self, filename, usage_file='link_usage.json'):
        self.filename = filename
        self.usage_file = usage_file
        with open(filename, 'r') as f:
            self.links = f.read().splitlines()
        if os.path.exists(usage_file):
            with open(usage_file, 'r') as f:
                self.link_usage = json.load(f)
        else:
            self.link_usage = {}

    def get_link(self):
        for link in self.links:
            if link not in self.link_usage:
                self.link_usage[link] = 0
            if self.link_usage[link] < Invite_per_linc:
                self.link_usage[link] += 1
                self.save_link_usage()
                if self.link_usage[link] == Invite_per_linc:
                    self.cleanup_links()
                return link
        return None

    def save_link_usage(self):
        with open(self.usage_file, 'w') as f:
            json.dump(self.link_usage, f)

    def cleanup_links(self):
        self.links = [link for link in self.links if self.link_usage.get(link, 0) < Invite_per_linc]
        with open(self.filename, 'w') as f:
            for link in self.links:
                f.write(link + '\n')

ref_sys = ReferralSystem('ref_links.txt')



def setup_logger(logger_name):
    logger = colorlog.getLogger(logger_name)

    # Removes previous handlers, if they exist.
    while logger.hasHandlers():
        logger.removeHandler(logger.handlers[0])

    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter(
            "|%(log_color)s%(asctime)s| - Profile [%(name)s] - %(levelname)s - %(message)s",
            datefmt=None,
            reset=True,
            log_colors={
                'DEBUG':    'cyan',
                'INFO':     'green',
                'WARNING':  'yellow',
                'ERROR':    'red',
                'CRITICAL': 'red,bg_white',
            },
            secondary_log_colors={},
            style='%'
        )
    )
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    return logger
def click_if_exists(driver, locator):
    max_attempts = 3
    attempts = 0
    while attempts < max_attempts:
        try:
            element = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.XPATH, locator))
            )
            element.click()
            time.sleep(random.uniform(1.3, 2.1))
            return True
        except TimeoutException:
            return False
        except StaleElementReferenceException:
            attempts += 1
            time.sleep(3)
    return False
def confirm_transaction(driver, logger):

    metamask_window_handle = find_metamask_notification(driver, logger)

    if metamask_window_handle:
        find_confirm_button_js = '''
        function findConfirmButton() {
          return document.querySelector('[data-testid="page-container-footer-next"]');
        }
        return findConfirmButton();
        '''
        confirm_button = driver.execute_script(find_confirm_button_js)

        if confirm_button:
            driver.execute_script("arguments[0].scrollIntoView(true);", confirm_button)
            for i in range(5):
                if metamask_window_handle not in driver.window_handles:
                    logger.info("Action is approve")
                    return True
                logger.info(f"Click attempt {i + 1}")
                driver.execute_script("arguments[0].click();", confirm_button)
                time.sleep(3)
            logger.info("Action is approve")
            return True
        else:
            logger.warning("Confirm button not found")
            return False
    else:
        logger.warning(f"MetaMask Notification window not found after 5 attempts")
        return False
def input_text_if_exists(driver, locator, text):
    max_attempts = 3
    attempts = 0
    while attempts < max_attempts:
        try:
            element = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, locator))
            )
            # Clearing the input field
            element.clear()
            # Write the new text into the field
            for character in text:
                element.send_keys(character)
                time.sleep(random.uniform(0.075, 0.124))
            return True
        except TimeoutException:
            return False
        except StaleElementReferenceException:
            attempts += 1
            time.sleep(3)
    return False
def metamask_login(driver, password, logger):
    driver.get(metamask_url)
    password_input = '//*[@id="password"]'
    input_text_if_exists(driver, password_input, password)
    click_if_exists(driver, '//*[@id="app-content"]/div/div[3]/div/div/button')
    click_if_exists(driver, '/html/body/div[1]/div/div[1]/div/div[2]/div/div')
    try:
        time.sleep(5)
        element = driver.find_element(By.XPATH, "//*[contains(text(), 'zkSync Era Mainnet')]")
        element.click()
        value_zk = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH,
                 '//*[@id="app-content"]/div/div[3]/div/div/div/div[2]/div/div[1]/div/div/div/div[1]/div/span[2]')))
        its_value = float(value_zk.text)
        if its_value > 0.001:
            logger.info("You have 2$ on Zk-era chain, good...")
            return 1
    except NoSuchElementException:
        logger.info("Look like you don't add ZK network, dumbass...")
        driver.get(f"chrome-extension://{identificator}/home.html#settings/networks/add-network")
        input_text_if_exists(driver,
                             '//*[@id="app-content"]/div/div[3]/div/div[2]/div[2]/div/div[2]/div/div[2]/div[1]/label/input',
                             "zkSync Era Mainnet")
        input_text_if_exists(driver,
                             '//*[@id="app-content"]/div/div[3]/div/div[2]/div[2]/div/div[2]/div/div[2]/div[2]/label/input',
                             "https://mainnet.era.zksync.io")
        input_text_if_exists(driver,
                             '//*[@id="app-content"]/div/div[3]/div/div[2]/div[2]/div/div[2]/div/div[2]/div[3]/label/input',
                             "324")
        input_text_if_exists(driver,
                             '//*[@id="app-content"]/div/div[3]/div/div[2]/div[2]/div/div[2]/div/div[2]/div[4]/label/input',
                             "ETH")
        input_text_if_exists(driver,
                             '//*[@id="app-content"]/div/div[3]/div/div[2]/div[2]/div/div[2]/div/div[2]/div[5]/label/input',
                             "https://explorer.zksync.io/")
        click_if_exists(driver, '/html/body/div[1]/div/div[3]/div/div[2]/div[2]/div/div[2]/div/div[3]/button[2]')

        value_zk = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH,
                 '//*[@id="app-content"]/div/div[3]/div/div/div/div[2]/div/div[1]/div/div/div/div[1]/div/span[2]')))
        its_value = float(value_zk.text)
    if its_value > 0.001:
        logger.info("You have 2$ on Zk-era chain, good...")
        return 1
    elif its_value < 0.001:
        logger.info("Look like you didn't have 2$ on Zk-era chain, sad, Checking BNB...")
        try:
            click_if_exists(driver, '/html/body/div[1]/div/div[1]/div/div[2]/div/div')
            time.sleep(5)
            element = driver.find_element(By.XPATH, "//*[contains(text(), 'BNB Smart Chain (previously Binance Smart Chain Mainnet)')]")
            element.click()
            value_bnb = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH,
                     '//*[@id="app-content"]/div/div[3]/div/div/div/div[2]/div/div[1]/div/div/div/div[1]/div/span[2]')))
            its_value2 = float(value_bnb.text)
            if its_value2 > 0.01:
                logger.info("You have 2$ on BNB chain, good...")
                return 2
            elif its_value < 0.01:
                logger.info("Look like you didn't have 2$ on Zk-era and BNB chain...")
                logger.warning("You broke bro, go find some money")
                return 0
        except NoSuchElementException:
            logger.info("Look like you don't add BNB network, dumbass...")
            driver.get(f"chrome-extension://{identificator}/home.html#settings/networks/add-network")
            input_text_if_exists(driver,
                                 '//*[@id="app-content"]/div/div[3]/div/div[2]/div[2]/div/div[2]/div/div[2]/div[1]/label/input',
                                 "BNB Smart Chain (previously Binance Smart Chain Mainnet)")
            input_text_if_exists(driver,
                                 '//*[@id="app-content"]/div/div[3]/div/div[2]/div[2]/div/div[2]/div/div[2]/div[2]/label/input',
                                 "https://bsc-dataseed.binance.org/")
            input_text_if_exists(driver,
                                 '//*[@id="app-content"]/div/div[3]/div/div[2]/div[2]/div/div[2]/div/div[2]/div[3]/label/input',
                                 "56")
            input_text_if_exists(driver,
                                 '//*[@id="app-content"]/div/div[3]/div/div[2]/div[2]/div/div[2]/div/div[2]/div[4]/label/input',
                                 "BNB")
            input_text_if_exists(driver,
                                 '//*[@id="app-content"]/div/div[3]/div/div[2]/div[2]/div/div[2]/div/div[2]/div[5]/label/input',
                                 "https://bscscan.com/")
            click_if_exists(driver,
                            '/html/body/div[1]/div/div[3]/div/div[2]/div[2]/div/div[2]/div/div[3]/button[2]')
            value_bnb = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH,
                            '//*[@id="app-content"]/div/div[3]/div/div/div/div[2]/div/div[1]/div/div/div/div[1]/div/span[2]')))
            its_value2 = float(value_bnb.text)
            if its_value2 > 0.01:
                logger.info("You have 2$ on BNB chain, good...")
                return 2
            elif its_value < 0.01:
                logger.info("Look like you didn't have 2$ on Zk-era and BNB chain...")
                logger.warning("You broke bro, go find some money")
                return 0
    logger.info("Done with this shit")
def find_metamask_notification(driver, logger):
    metamask_window_handle = None

    for attempt in range(5):
        time.sleep(5)

        for handle in driver.window_handles:
            driver.switch_to.window(handle)
            if 'MetaMask Notification' in driver.title:
                metamask_window_handle = handle
                logger.info("MetaMask window found!")
                break

        if metamask_window_handle:
            break

    return metamask_window_handle
def process_profile(idx):
    profile_id = data.loc[idx, "Profile ID"]
    password = data.loc[idx, "Password"]

    nugger = setup_logger(f'{idx + 1}')

    open_url = f"http://local.adspower.net:50325/api/v1/browser/start?user_id={profile_id}"
    resp = requests.get(open_url).json()

    if resp["code"] != 0:
        print(resp["msg"])
        print("Failed to start a driver")
        sys.exit()

    chrome_driver = resp["data"]["webdriver"]
    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", resp["data"]["ws"]["selenium"])
    driver = webdriver.Chrome(service=Service(chrome_driver), options=chrome_options)
    initial_window_handle = driver.current_window_handle
    time.sleep(1.337)

    for tab in driver.window_handles:
        if tab != initial_window_handle:
            driver.switch_to.window(tab)
            nugger.info("Cleaning tabs...")
            driver.close()


    driver.switch_to.window(initial_window_handle)

    result_metamask = metamask_login(driver, password, nugger)
    if result_metamask == 0:
        nugger.error(f"No money detected. exiting...")
        exit("System termination")
    elif result_metamask == 1:
        nugger.info("Using Zk era for mint...")
    elif result_metamask == 2:
        nugger.info("Using BNB for mint...")

    link = ref_sys.get_link()
    if link is None:
        nugger.error("You have no link man, go find some more...")
        exit("System termination")
    driver.get(link)

    try:
        time.sleep(5)
        element = driver.find_element(By.XPATH, '//*[@id="elementAppLayoutHeader"]/div[2]/div[2]/div[7]/div')
        nugger.info("Look like already connected before...")
    except NoSuchElementException:
        nugger.warning("Start connecting to 'Element' page...")
        click_if_exists(driver, '//*[@id="elementAppLayoutHeader"]/div[2]/div[2]/div[7]')
        click_if_exists(driver, '//*[@id="root"]/div[1]/div/div/div/div[1]')

        metamask_window_handle = find_metamask_notification(driver, nugger)
        if metamask_window_handle:
            click_if_exists(driver, '//*[@id="app-content"]/div/div[2]/div/div[3]/div[2]/button[2]')
            click_if_exists(driver, '//*[@id="app-content"]/div/div[2]/div/div[2]/div[2]/div[2]/footer/button[2]')
            click_if_exists(driver, '//*[@id="app-content"]/div/div[2]/div/div[2]/div[2]/button[1]')

            metamask_window_handle = find_metamask_notification(driver, nugger)
            if metamask_window_handle:
                click_if_exists(driver, '//*[@id="app-content"]/div/div[2]/div/div[3]/button[2]')
                click_if_exists(driver, '//*[@id="app-content"]/div/div[2]/div/div[3]/button[2]')
                driver.switch_to.window(initial_window_handle)
            else:
                driver.switch_to.window(initial_window_handle)
                nugger.warning("Metamask window handle don't found, may be you system can't handel so much profile...")
        else:
            driver.switch_to.window(initial_window_handle)
            nugger.warning("Metamask window handle don't found, may be you system can't handel so much profile...")
    nugger.info("Done with connection to 'Element' page...")

    nugger.info("Accepting invite...")
    click_if_exists(driver, '//*[@id="root"]/div[1]/div/div[5]/div[1]/button')

    # click_if_exists(driver, '//*[@id="dialog-7"]/div/div/div[3]/button[2]')
    # click_if_exists(driver, '//*[@id="dialog-8"]/div/div/div[3]/button')
    click_if_exists(driver, '/html/body/div[3]/div[2]/div/div/div[3]/button[2]')
    click_if_exists(driver, '/html/body/div[3]/div[2]/div/div/div[3]/button')

    click_if_exists(driver, '//*[@id="elementAppLayoutHeader"]/div[2]/div[2]/div[2]')

    number = round(random.uniform(1, 6))

    if result_metamask == 1:
        click_if_exists(driver, '//*[@id="layout-header-popover"]/div[2]/div[6]')
    elif result_metamask == 2:
        click_if_exists(driver, '//*[@id="layout-header-popover"]/div[2]/div[2]')
    nugger.info("Jump straight to NFT market")
    driver.get("https://element.market/assets")
    click_if_exists(driver, '//*[@id="root"]/div[1]/div/div/div[2]/div[1]/div/div/div[2]')
    input_text_if_exists(driver, '//*[@id="root"]/div[1]/div/div/div[2]/div[1]/div/div/div[2]/div[2]/div/div[2]/div[3]/input', "0.001")
    click_if_exists(driver, '//*[@id="root"]/div[1]/div/div/div[2]/div[1]/div/div/div[2]/div[2]/div/button')
    time.sleep(2)

    click_if_exists(driver, f'//*[@id="root"]/div[1]/div/div/div[2]/div[2]/div[2]/div/div[1]/div[1]/div/div/div[{number}]')
    click_if_exists(driver,
                    f'//*[@id="root"]/div[1]/div/div/div[2]/div[2]/div[2]/div/div[1]/div[1]/div/div/div[{number}]/div/div[7]/button[1]')
    try:
        time.sleep(4)
        element = driver.find_element(By.XPATH, '/html/body/div[5]/div[2]/div/div/div[3]/div/div/button')
        element.click()
    except NoSuchElementException:
        math = 1-3

    confirm_transaction(driver, nugger)
    driver.switch_to.window(initial_window_handle)
    if click_if_exists(driver, '/html/body/div[5]/div[2]/div/div/div[3]/div/div/div/button') is True:
        nugger.info("Job is done ref buy NFT...")
        driver.close()
    else:
        nugger.info("Purchase is failed, use you hand...")
        driver.quit()

nugger_junior = setup_logger("Thread Loging")


with ThreadPoolExecutor(max_workers=max_workers) as executor:  # Adjust max_workers as needed
    # Submit tasks to executor
    for idx in range(start_idx, end_idx + 1):
        futures = {executor.submit(process_profile, idx): idx}
        time.sleep(20)

    # Collect results as they become available
    for future in concurrent.futures.as_completed(futures):
        idx = futures[future]
        try:
            future.result()
        except Exception:
            nugger_junior.error("Something go wrong, system left this profile for you hand...")
            nugger_junior.info("But no worry skript is still able to perform...")