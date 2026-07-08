import os
import time
import requests
from datetime import datetime

# ==========================
# Configuration
# ==========================

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

if not DISCORD_WEBHOOK_URL:
    raise RuntimeError("DISCORD_WEBHOOK_URL environment variable is not set.")

NUMBER_OF_FEW_DATES = 1

# Notify only if appointment is before this date
FIND_DATES_BEFORE = "2026-07-23"
FIND_DATES_BEFORE_DT = datetime.strptime(FIND_DATES_BEFORE, "%Y-%m-%d")

DMV_APPOINTMENT_API_ENDPOINT = (
    "https://www.dmv.ca.gov/portal/wp-json/dmv/v1/appointment/branches/"
)

HEADERS = {
    "User-Agent": "DMV Appointment Checker"
}

branch_codes = {
    "costa_mesa": "628!4bbd75c86ed4a7c60fe5b8b7d4581c89d7b14a15218776c5c999dd2baa61",
    "santa_ana": "542!7a56567b1d6b2331a42a0f405c3de459ba86c31c23329e76aecf50883697",
    "long_beach": "AT2!13be0ec4ed4b308968b69a67515d4a4cf8a3c352ec1a771e63c3c9d70542",
    "fullerton": "607!48c4e5f82e3be3881582ae164482b7b3b55085a153cf0c1fe7a7be96f005",
    "san_clemente": "648!d04cd5bf585d51a14643f28fadbb2f675a3b169ce28b8e7015ef5e5a902d",
    "westminster": "611!2a45f10734c6406e59f36396fcf6da62054d0f08880dfb97676a51bfe511",
}

dates_querystring = (
    "services[]=DT!1857a62125c4425a24d85aceac6726cb8df3687d47b03b692e27bd8d17814"
    "&numberOfCustomers=1"
)

# Used only during one execution
current_latest_dates = {}


# ==========================
# Discord
# ==========================

def send_discord_message(message):
    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": message},
            timeout=10,
        )

        if response.status_code not in (200, 204):
            print(f"Discord error: {response.status_code}")
            print(response.text)

    except requests.RequestException as e:
        print(f"Failed to send Discord message: {e}")


# ==========================
# DMV API
# ==========================

def get_available_dates(city):
    url = (
        f"{DMV_APPOINTMENT_API_ENDPOINT}"
        f"{branch_codes[city]}/dates?{dates_querystring}"
    )

    print(f"Checking {city}...")

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=10,
        )
        response.raise_for_status()

    except requests.RequestException as e:
        print(f"Error contacting DMV API: {e}")
        return None

    dates_str = response.json()

    if not dates_str:
        return []

    return [
        datetime.strptime(date, "%Y-%m-%dT%H:%M:%S")
        for date in dates_str
    ]


def update_latest_dates(city, new_date):
    if city not in current_latest_dates:
        current_latest_dates[city] = new_date
        return False

    if (
        new_date < current_latest_dates[city]
        and new_date < FIND_DATES_BEFORE_DT
    ):
        current_latest_dates[city] = new_date
        return new_date

    current_latest_dates[city] = new_date
    return False


def get_dates_in_text_response(report_only_changes=False):
    full_reply_body = ""

    for city in branch_codes:
        dates = get_available_dates(city)

        if dates is None:
            continue

        if len(dates) == 0:
            continue

        latest_date = update_latest_dates(city, dates[0])

        if latest_date:
            full_reply_body += (
                f"‼️ New available date at **{city.replace('_', ' ').title()}**: "
                f"{latest_date.strftime('%Y-%m-%d (%a)')}\n\n"
            )

        elif not report_only_changes:
            first_few = dates[:NUMBER_OF_FEW_DATES]

            first_few_dates = "\n".join(
                f"{i+1}. {date.strftime('%Y-%m-%d (%a)')}"
                for i, date in enumerate(first_few)
            )

            full_reply_body += (
                f"❌ {city.replace('_',' ').title()}\n"
                f"{first_few_dates}\n\n"
            )

        time.sleep(1)

    return full_reply_body.strip()


# ==========================
# Main
# ==========================

def main():
    print(f"Started: {datetime.now()}")

    message = get_dates_in_text_response(report_only_changes=True)

    if message:
        send_discord_message(message)
        print("Notification sent.")
    else:
        print("No new appointments found.")


if __name__ == "__main__":
    main()
