import robin_stocks.robinhood as r
from public_invest_api import Public
import discord
from discord.ext import commands
import os
import json
import schedule
import time
from datetime import datetime
import asyncio
from dotenv import load_dotenv

load_dotenv()

# Define the file paths for credentials and JSON files
robinhood_file_path = 'C:/Users/arnav/OneDrive/Desktop/RobinPass.txt'
public_file_path = 'C:/Users/arnav/OneDrive/Desktop/PublicPass.txt'
robinhood_json_file_path = 'currentArbsRobinhood.json'
public_json_file_path = 'currentArbsPublic.json'

# Initialize variables for credentials
robinhood_email = None
robinhood_password = None
public_username = None
public_password = None

# Initialize Discord bot with intents
intents = discord.Intents.all()
intents.messages = True
bot = commands.Bot(command_prefix="$", intents=intents)
discord_token = os.getenv('DISCORD_BOT_TOKEN')
buy_channel_id = 1240105481259716669  # Replace with your channel ID for buy notifications
sell_channel_id = 1240109934654390382  # Replace with your channel ID for sell notifications
alerts_channel_id = 1241468924034416691  # Replace with your channel ID for alerts

# Read Robinhood credentials from file
try:
    with open(robinhood_file_path, 'r') as file:
        robinhood_email = file.readline().strip()
        robinhood_password = file.readline().strip()
except Exception as e:
    print(f"Failed to read Robinhood credentials file: {e}")

# Read Public credentials from file
try:
    with open(public_file_path, 'r') as file:
        public_username = file.readline().strip()
        public_password = file.readline().strip()
except Exception as e:
    print(f"Failed to read Public credentials file: {e}")

# Function to read tickers from JSON file
def read_tickers(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return json.load(file)
    return []

# Function to write tickers to JSON file
def write_tickers(file_path, tickers):
    with open(file_path, 'w') as file:
        json.dump(tickers, file)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    
    # Send login messages
    login_message = []
    if robinhood_email and robinhood_password:
        try:
            r.login(robinhood_email, robinhood_password)
            login_message.append("Logged in successfully to RobinHood!")
        except Exception as e:
            login_message.append(f"RobinHood login failed: {e}")
    else:
        login_message.append("Failed to retrieve RobinHood credentials.")

    if public_username and public_password:
        try:
            public = Public()
            public.login(username=public_username, password=public_password, wait_for_2fa=True)
            login_message.append("Logged in successfully to Public!")
        except Exception as e:
            login_message.append(f"Public login failed: {e}")
    else:
        login_message.append("Failed to retrieve Public credentials.")

    if login_message:
        for message in login_message:
            print(message)
            await bot.get_channel(alerts_channel_id).send(message)
    
    await schedule_daily_sell()
    await schedule_daily_VOO()

@bot.event
async def on_message(message):
    if message.channel.id == buy_channel_id and message.content.startswith('$'):
        ticker = message.content[1:].strip().upper()
        print(f"Processing ticker: {ticker}")
        try:
            robinhood_result = buy_stock_robinhood(ticker)
            public_result = buy_stock_public(ticker)
            await send_order_message(message.channel, ticker, robinhood_result, public_result)
        except Exception as e:
            error_message = f"Failed to place order for {ticker}: {e}"
            await message.channel.send(error_message)
            print(error_message)

def buy_stock_robinhood(ticker):
    order_result = r.order_buy_market(ticker, 1)
    print(f"Robinhood order result: {order_result}")  # Debug log
    tickers = read_tickers(robinhood_json_file_path)
    tickers.append(ticker)
    write_tickers(robinhood_json_file_path, tickers)
    return order_result

def buy_stock_public(ticker):
    # Initialize and login to Public
    public = Public()
    public.login(username=public_username, password=public_password, wait_for_2fa=True)
    
    # Place a market buy order
    response = public.place_order(
        symbol=ticker,
        quantity=1,  # Number of shares to buy
        side='buy',
        order_type='market',  # Market order
        time_in_force='gtc'  # Good 'til canceled
    )
    print(f"Public order result: {response}")  # Debug log
    tickers = read_tickers(public_json_file_path)
    tickers.append(ticker)
    write_tickers(public_json_file_path, tickers)
    return response

def buy_stock_robinhood_VOO(balance):
    balance = float(get_cash_balance())
    purchase_balance = balance - 5.0
    ticker = "VOO"
    r.order_buy_fractional_by_price(ticker, purchase_balance, timeInForce="gfd", extendedHours=False)

def sell_all_shares_robinhood():
    tickers = read_tickers(robinhood_json_file_path)
    result_messages = []
    tickers_to_remove = []

    if not tickers:
        message = "No tickers to sell today. Checking again tomorrow."
        result_messages.append(message)
        return message

    for ticker in tickers:
        try:
            positions = r.build_holdings()
            if ticker in positions:
                shares = float(positions[ticker]['quantity'])
                message = f"Attempting to sell {shares} shares of {ticker}."
                result_messages.append(message)
                order_result = r.order_sell_market(ticker, shares, timeInForce='gfd')
                result_messages.append(f"Order Result: {order_result}")
                if order_result and order_result.get('id'):
                    order_id = order_result['id']
                    order_state = order_result['state']
                    message = f"Sold {shares} shares of {ticker}. Order ID: {order_id}, State: {order_state}"
                    result_messages.append(message)
                    tickers_to_remove.append(ticker)
                else:
                    raise ValueError(f"Failed to sell shares of {ticker}. Order result: {order_result}")
            else:
                message = f"{ticker} is not in the account. Checking again tomorrow."
                result_messages.append(message)
        except Exception as e:
            error_message = f"Failed to sell shares of {ticker}: {e}"
            result_messages.append(error_message)
    
    # Update the tickers list to remove only successfully sold tickers
    remaining_tickers = [ticker for ticker in tickers if ticker not in tickers_to_remove]
    write_tickers(robinhood_json_file_path, remaining_tickers)

    if not result_messages:
        result_messages.append("No shares were sold.")
    
    final_message = "\n".join(result_messages)
    return final_message

async def sell_all_shares_discord():
    result_message = sell_all_shares_robinhood()
    sell_channel = bot.get_channel(sell_channel_id)
    await sell_channel.send(result_message)
    print(result_message)

async def buy_VOO():
    balance = get_cash_balance()
    buy_stock_robinhood_VOO(balance)
    message_text = f"Bought Daily VOO Shares with Arb Money. Balance: ${balance}"
    output_channel = bot.get_channel(alerts_channel_id)
    await output_channel.send(message_text)
    print(message_text)

def get_cash_balance():
    account_info = r.profiles.load_account_profile()
    cash_balance = account_info.get("cash", "N/A")
    return cash_balance

async def send_order_message(channel, ticker, robinhood_result, public_result):
    robinhood_status = "✅" if 'id' in robinhood_result else "❌"
    public_status = "✅" if public_result.get('success', False) else "❌"
    
    message_text = (
        f"Order for {ticker}:\n"
        f"Robinhood: {robinhood_status}\n"
        f"Public: {public_status}"
    )
    await channel.send(message_text)
    print(message_text)

# Schedule daily sell at 8:45 AM CST on weekdays
async def schedule_daily_sell():
    if datetime.today().weekday() < 5:
        schedule.every().day.at("08:45").do(lambda: asyncio.create_task(sell_all_shares_discord()))
        while True:
            schedule.run_pending()
            await asyncio.sleep(1)

# Schedule daily VOO buy at 9:00 AM CST on weekdays
async def schedule_daily_VOO():
    if datetime.today().weekday() < 5:
        schedule.every().day.at("09:00").do(lambda: asyncio.create_task(buy_VOO()))
        while True:
            schedule.run_pending()
            await asyncio.sleep(1)

async def main():
    await bot.start(discord_token)

if __name__ == "__main__":
    asyncio.run(main())