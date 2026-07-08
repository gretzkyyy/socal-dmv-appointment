import requests
import time
from datetime import datetime

#Discord Webhook, stored as local OS environmental var 
import os

discord_webhook_url = os.getenv("discord_webhook_url")
# create a new environmental var through user settings on your device 
# name it "discord_webhook_url" 
# in discord, add a new webhook & copy paste the url into your environmental var 

if not discord_webhook_url:
    raise RuntimeError("discord_webhook_url environment variable is not set.")
    
# Discord Message Function 
def send_discord_message(message):
    data = {
        "content": message
    }

    response = requests.post(discord_webhook_url, json=data)

    if response.status_code not in [200, 204]:
        print("Discord error:", response.status_code)
        print(response.text)
        
# number of dates to show if no new dates are found
NUMBER_OF_FEW_DATES = 1 

# Notify if dates are found before this date
FIND_DATES_BEFORE = "2026-07-23"

# Interval to check for new dates (in seconds)
LOOKUP_INTERVAL_SEC = 60 * 10 # 10 minutes

DMV_APPOINTMENT_API_ENDPOINT = "https://www.dmv.ca.gov/portal/wp-json/dmv/v1/appointment/branches/"

branch_codes = {
    "costa_mesa": "628!4bbd75c86ed4a7c60fe5b8b7d4581c89d7b14a15218776c5c999dd2baa61",
    "santa_ana": "542!7a56567b1d6b2331a42a0f405c3de459ba86c31c23329e76aecf50883697",
    "long_beach": "AT2!13be0ec4ed4b308968b69a67515d4a4cf8a3c352ec1a771e63c3c9d70542",
    "fullerton": "607!48c4e5f82e3be3881582ae164482b7b3b55085a153cf0c1fe7a7be96f005",
    "san_clemente": "648!d04cd5bf585d51a14643f28fadbb2f675a3b169ce28b8e7015ef5e5a902d",
    "westminster": "611!2a45f10734c6406e59f36396fcf6da62054d0f08880dfb97676a51bfe511"
}

last_updated_timestamp = None

dates_querystring = "services[]=DT!1857a62125c4425a24d85aceac6726cb8df3687d47b03b692e27bd8d17814&numberOfCustomers=1"

current_latest_dates = {}

def get_available_dates(city):
    # send GET request to the DMV Appointments API
    response = requests.get(f"{DMV_APPOINTMENT_API_ENDPOINT}/{branch_codes[city]}/dates?{dates_querystring}")

    print("Making request for " + city + "...")

    # check if response is valid
    if response.status_code != 200:
        print("Error: Invalid response from DMV API (HTTP Status Code: " + str(response.status_code) + ")")
        print(response.text)
        return False

    # parse response
    dates_str = response.json()

    # convert string dates to datetime objects
    dates = [datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S") for date_str in dates_str]

    return dates

def update_latest_dates(city, new_date):

    global current_latest_dates

    # check if city is in current_latest_dates
    if city not in current_latest_dates:
        current_latest_dates[city] = new_date
        return False

    # check if date is prior to of current latest date
    find_dates_before_datetime = datetime.strptime(FIND_DATES_BEFORE, "%Y-%m-%d")

    if new_date < current_latest_dates[city] and new_date < find_dates_before_datetime:
        current_latest_dates[city] = new_date
        return new_date
    
    current_latest_dates[city] = new_date
    return False

def get_dates_in_text_response(report_only_changes=False):
    full_reply_body = ""

    for city in branch_codes:
        dates = await get_available_dates(city)

        if not dates:
            return False
        
        latest_date = await update_latest_dates(city, dates[0])

        if latest_date:
            full_reply_body += f"""
‼️ New available date at {city}: {latest_date.strftime("%Y-%m-%d (%a)")}
"""
        elif not report_only_changes:
            first_few_dates = dates[:NUMBER_OF_FEW_DATES]
            first_few_dates_str = "\n".join([f"{i+1}. {date.strftime('%Y-%m-%d (%a)')}" for i, date in enumerate(first_few_dates)])

            full_reply_body += f"""
❌ No new dates found at {city}: 
{first_few_dates_str}
"""

        # wait 1 second before sending another request to DMV API
        await asyncio.sleep(1)

    return full_reply_body

def callback_minute():
    texts_to_send = []
    
    try:
        global last_updated_timestamp

        last_updated_timestamp = datetime.now()
        print("Last updated: " + str(last_updated_timestamp))

        full_reply_body = await get_dates_in_text_response(report_only_changes=True)

        if full_reply_body:
            texts_to_send.append(full_reply_body)


    except Exception as e:
        print("Error: There was an exception.")
        print(e)
        texts_to_send.append("Error: There was an exception.")
        texts_to_send.append(str(e))
        return        
    
    if texts_to_send:
        send_discord_message("\n".join(texts_to_send))        


def main():
    while True:
        await callback_minute()
        await asyncio.sleep(LOOKUP_INTERVAL_SEC)

asyncio.run(main())

try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
except requests.RequestException as e:
    print(f"Request failed: {e}")
    return False
