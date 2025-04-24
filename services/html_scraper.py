import re

import aiohttp
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from utils.logger import setup_logger
import os
from dotenv import load_dotenv
load_dotenv()

STATE = os.getenv("STATE")
logger = setup_logger("scraper")



async def fetch_company_details(url: str) -> dict:
    try:
        ua = UserAgent()
        user_agent = ua.chrome
        entity_id = url.rstrip('/').split('/')[-1]
        base_url = url[:url.rfind('/')]
        payload = f'businessId={entity_id}&businessReservationNumber=0'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': user_agent,
            'Referer': 'https://businessregistration.utah.gov/EntitySearch/OnlineBusinessAndMarkSearchResult',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Sec-Fetch-Site': 'same-origin',
            'Accept-Language': 'en-GB,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Sec-Fetch-Mode': 'navigate',
            'Origin': 'https://businessregistration.utah.gov',
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(base_url, data=payload) as response:
                response.raise_for_status()
                html = await response.text()
                return await parse_html_details(html)
    except Exception as e:
        logger.error(f"Error fetching data for query '{url}': {e}")
        return []
async def fetch_company_data(query: str) -> list[dict]:
    try:
        url = "https://businessregistration.utah.gov/EntitySearch/OnlineBusinessAndMarkSearchResult"
        ua = UserAgent()
        user_agent = ua.random
        payload = f'QuickSearch.BusinessId=&QuickSearch.NVBusinessNumber=&QuickSearch.StartsWith=true&QuickSearch.Contains=false&QuickSearch.ExactMatch=false&QuickSearch.Allwords=&QuickSearch.BusinessName={query}&QuickSearch.PrincipalName=&QuickSearch.DomicileName=&QuickSearch.AssumedName=&QuickSearch.AgentName=&QuickSearch.MarkNumber=&QuickSearch.Classification=&QuickSearch.FilingNumber=&QuickSearch.Goods=&QuickSearch.ApplicantName=&QuickSearch.All=&QuickSearch.EntitySearch=true&QuickSearch.MarkSearch=&QuickSearch.SeqNo=0&AdvancedSearch.BusinessTypeID=&AdvancedSearch.BusinessTypes=&AdvancedSearch.BusinessStatusID=0&AdvancedSearch.StatusDetails=&AdvancedSearch.BusinessSubTypes=&AdvancedSearch.JurdisctionTypeID=&AdvancedSearch.IncludeInactive=false&AdvancedSearch.EntityDateFrom=&AdvancedSearch.EntityDateTo=&AdvancedSearch.StatusDateFrom=&AdvancedSearch.StatusDateTo='
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': user_agent,
            'Referer': 'https://businessregistration.utah.gov/EntitySearch/OnlineEntitySearch',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Sec-Fetch-Site': 'same-origin',
            'Accept-Language': 'en-GB,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Sec-Fetch-Mode': 'navigate',
            'Origin': 'https://businessregistration.utah.gov',
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(url, data=payload) as response:
                response.raise_for_status()
                html = await response.text()
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
        id = raw_number.split('-')[0] if raw_number else None
        url = f"https://businessregistration.utah.gov/EntitySearch/BusinessInformation/{id}" if id else None

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