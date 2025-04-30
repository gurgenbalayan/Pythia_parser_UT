from selenium.common import WebDriverException, TimeoutException
from selenium import webdriver
from selenium.webdriver import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from utils.logger import setup_logger
import os

STATE = os.getenv("STATE")
SELENIUM_REMOTE_URL = os.getenv("SELENIUM_REMOTE_URL")
logger = setup_logger("scraper")


async def get_details_from_website(url: str, user_agent: str, entity_id: str) -> str:
    html = ""
    driver = None
    try:
        options = webdriver.ChromeOptions()
        options.headless = True
        options.page_load_strategy = 'eager'
        options.arguments.extend(["--no-sandbox", "--disable-setuid-sandbox"])
        options.add_argument('--lang=en-US')
        options.add_argument(f'--user-agent={user_agent}')
        options.add_argument("--start-maximized")
        options.add_argument("--disable-webrtc")
        options.add_argument("--disable-features=WebRtcHideLocalIpsWithMdns")
        options.add_argument("--force-webrtc-ip-handling-policy=default_public_interface_only")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-features=DnsOverHttps")
        options.add_argument("--disable-blink-features=AutomationControlled")
        driver = webdriver.Remote(
            command_executor=SELENIUM_REMOTE_URL,
            options=options
        )
        try:
            wait = WebDriverWait(driver, 10)
            driver.get(url)
            link = wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Search Business Entity Records")))
            link.click()
            wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#frm_BusinessSearch > div")))
            input_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                                                "#BusinessSearch_Index_txtEntityNumber"))
            )
            input_field.send_keys(entity_id)
            input_field.send_keys(Keys.RETURN)
            wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#grid_businessList")))
            link = wait.until(EC.presence_of_element_located((By.XPATH, "//table[@id='grid_businessList']//a[text()]")))
            link.click()
            wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "body > div.white > div > section > div.panel.panel-primary > div.panel-body > div.panel.panel-primary")))
            html = driver.page_source
            return html
        except TimeoutException as e:
            logger.error(f"Page load error {url}: {e}")
        except WebDriverException as e:
            logger.error(f"WebDriver error: {e}")
    except Exception as e:
        logger.error(f"Ошибка при запуске Selenium: {e}")
    finally:
        if driver:
            driver.quit()
    return html
async def get_search_from_website(url: str, user_agent: str, query: str) -> str:
    html = ""
    driver = None
    try:
        options = webdriver.ChromeOptions()
        options.headless = True
        options.page_load_strategy = 'eager'
        options.arguments.extend(["--no-sandbox", "--disable-setuid-sandbox"])
        options.add_argument('--lang=en-US')
        options.add_argument(f'--user-agent={user_agent}')
        options.add_argument("--headless=new")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-webrtc")
        options.add_argument("--disable-features=WebRtcHideLocalIpsWithMdns")
        options.add_argument("--force-webrtc-ip-handling-policy=default_public_interface_only")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-features=DnsOverHttps")
        options.add_argument("--disable-blink-features=AutomationControlled")
        driver = webdriver.Remote(
            command_executor=SELENIUM_REMOTE_URL,
            options=options
        )
        try:
            wait = WebDriverWait(driver, 10)
            driver.get(url)
            link = wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Search Business Entity Records")))
            link.click()
            wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#frm_BusinessSearch > div")))
            input_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                                                "#BusinessSearch_Index_txtEntityName"))
            )
            input_field.send_keys(query)
            input_field.send_keys(Keys.RETURN)
            try:
                web_table = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR,
                                                    "#grid_businessList"))
                )
                table = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#grid_businessList')))
                html = table.get_attribute('outerHTML')
                return html
            except:
                try:
                    submit = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR,
                                                        "#btnConfirmLimit"))
                    )
                    submit.click()
                    web_table = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR,
                                                        "#grid_businessList"))
                    )
                    table = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#grid_businessList')))
                    html = table.get_attribute('outerHTML')
                    return html
                except:
                    return ""
        except TimeoutException as e:
            logger.error(f"Page load error {url}: {e}")
        except WebDriverException as e:
            logger.error(f"WebDriver error: {e}")
    except Exception as e:
        logger.error(f"Ошибка при запуске Selenium: {e}")
    finally:
        if driver:
            driver.quit()
    return html

async def fetch_company_details(url: str) -> dict:
    try:
        ua = UserAgent()
        user_agent = ua.chrome
        entity_id = url.rstrip('/').split('/')[-1]
        html = await get_details_from_website("https://businessregistration.utah.gov", user_agent, entity_id)
        return await parse_html_details(html)
    except Exception as e:
        logger.error(f"Error fetching data for query '{url}': {e}")
        return {}
async def fetch_company_data(query: str) -> list[dict]:
    try:
        ua = UserAgent()
        user_agent = ua.chrome
        html = await get_search_from_website("https://businessregistration.utah.gov", user_agent, query)
        return await parse_html_search(html)
    except Exception as e:
        logger.error(f"Error fetching data for query '{query}': {e}")
        return []

async def parse_html_search(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("#grid_businessList tbody tr")[1:]
    results = []
    for row in rows:
        cols = row.find_all("td")
        if not cols or not cols[0].a:
            continue
        name_tag = cols[0].a
        name = name_tag.get_text(strip=True)
        status = cols[3].get_text(strip=True) or None
        raw_number = cols[8].get_text(strip=True) or None
        url = f"https://businessregistration.utah.gov/EntitySearch/BusinessInformation/{raw_number}" if raw_number else None

        results.append({
            "state": STATE,
            "name": name,
            "status": status,
            "id": raw_number,
            "url": url
        })
    return results


async def parse_html_details(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    if not soup.select_one("body div.white div section div.panel.panel-primary"):
        return []

    async def extract_label_value(label_text, soup=soup):
        label = soup.find("label", string=lambda t: t and label_text in t)
        if label:
            parent = label.find_parent(class_="label-side")
            if parent:
                next_td = parent.find_next_sibling()
                if next_td:
                    return next_td.get_text(strip=True)
        return None
    async def get_registered_agent():
        agent_panel = soup.find("label", string=lambda x: x and "REGISTERED AGENT INFORMATION" in x.upper()).find_parent("div").find_next_sibling("div")
        if not agent_panel:
            return None, None
        agent_name = await extract_label_value("Name", agent_panel)
        agent_address = await extract_label_value("Street Address", agent_panel)
        return agent_name, agent_address
    async def get_principals():
        principals = []
        table = soup.find("table", id="grid_principalList")
        if table:
            rows = table.find_all("tr")[1:]  # Skip header
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 3:
                    principals.append({
                        "name": cols[1].get_text(strip=True),
                        "title": cols[0].get_text(strip=True),
                        "address": cols[2].get_text(strip=True),
                    })
        return principals

    name = await extract_label_value("Entity Name")
    registration_number = await extract_label_value("Entity Number")
    entity_type = await extract_label_value("Entity Type")
    status = await extract_label_value("Entity Status")
    date_registered = await extract_label_value("Formation Date")
    mailing_address = await extract_label_value("Mailing Address")
    principal_address = await extract_label_value("Physical Address")

    agent_name, agent_address = await get_registered_agent()
    managers = await get_principals()

    return {
        "state": STATE,
        "name": name,
        "status": status,
        "registration_number": registration_number,
        "date_registered": date_registered,
        "entity_type": entity_type,
        "agent_name": agent_name,
        "agent_address": agent_address,
        "principal_address": principal_address,
        "mailing_address": mailing_address,
        "managers": managers,
        "documents": []
    }