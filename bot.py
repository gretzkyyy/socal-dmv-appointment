import requests
import time
from datetime import datetime

from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# number of dates to show if no new dates are found
NUMBER_OF_FEW_DATES = 1 

# Telegram chat IDs that are authorized to use this bot
AUTHORIZED_CHAT_IDS = [
    0 # replace with your chat ID
]

# Notify if dates are found before this date
FIND_DATES_BEFORE = "2026-07-23"

# Telegram Bot API Token
TELEGRAM_API_TOKEN = "<INSERT_TOKEN_HERE>" # replace with your Telegram Bot API Token

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

app = ApplicationBuilder().token(TELEGRAM_API_TOKEN).build()
job_queue = app.job_queue

async def get_available_dates(city):
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

async def update_latest_dates(city, new_date):

    global current_latest_dates

    # check if city is in current_latest_dates
    if city not in current_latest_dates:
        current_latest_dates[city] = new_date
        return new_date

    # check if date is prior to of current latest date
    find_dates_before_datetime = datetime.strptime(FIND_DATES_BEFORE, "%Y-%m-%d")

    if new_date < current_latest_dates[city] and new_date < find_dates_before_datetime:
        current_latest_dates[city] = new_date
        return new_date
    
    current_latest_dates[city] = new_date
    return False

async def get_dates_in_text_response(report_only_changes=False):
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
        time.sleep(1)

    return full_reply_body


async def send_welcome(update, context):
    await update.message.reply_text("""\
vroom vroom 🚙
try the /dates command to get available dates
""")
                         
app.add_handler(CommandHandler("help", send_welcome))
app.add_handler(CommandHandler("start", send_welcome))

async def send_pong(update, context):
    await update.message.reply_text(f"""pong, now: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

last updated: {str(last_updated_timestamp)}
""")

app.add_handler(CommandHandler("ping", send_pong))

# Handle dates command
async def send_dates(update, context):

    # check if chat ID is valid first
    if update.message.chat_id not in AUTHORIZED_CHAT_IDS:
        await update.message.reply_text("Sorry, you are not authorized to use this bot.")
        return

    await context.bot.send_chat_action(chat_id=update.message.chat_id, action="typing")
    await update.message.reply_text("Getting available dates...")

    try:
        full_reply_body = await get_dates_in_text_response(report_only_changes=False)

        if not full_reply_body:
            await update.message.reply_text("Sorry, there was an error getting the available dates. Please try again later.")
            return
        
        await update.message.reply_text(full_reply_body)

    except Exception as e:
        await update.message.reply_text("Sorry, there was an exception.")
        await update.message.reply_text(str(e))
        print(e)
        return


app.add_handler(CommandHandler("dates", send_dates))

async def callback_minute(context: ContextTypes.DEFAULT_TYPE):
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
        for chat_id in AUTHORIZED_CHAT_IDS:
            await context.bot.send_message(chat_id=chat_id, text="\n".join(texts_to_send))        

job_minute = job_queue.run_repeating(callback_minute, interval=LOOKUP_INTERVAL_SEC, first=5)

app.run_polling()
