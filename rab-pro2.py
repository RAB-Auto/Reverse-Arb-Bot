import robin_stocks.robinhood as r
import discord
from discord.ext import commands
import os
import json
import schedule
import time
from datetime import datetime
import asyncio
import math

# Define the file path for the credentials and JSON file
file_path = 'C:/Users/arnav/OneDrive/Desktop/RobinPass.txt'
json_file_path = 'currentArbs.json'

# Initialize variables for credentials
robinhood_email = None
robinhood_password = None
discord_token = 'MTI0MDEwNDkyNzUxOTQ0MDk1Ng.GV3RoT.YwuqrNolLo2OIbsIYGfEGvSbxiU-gMva83tdnU'  # Replace with your Discord bot token
buy_channel_id = 1240105481259716669  # Replace with your channel ID for buy notifications
sell_channel_id = 1240109934654390382  # Replace with your channel ID for sell notifications

# Read the file and extract credentials
try:
    with open(file_path, 'r') as file:
        robinhood_email = file.readline().strip()  # Read the first line for the email
        robinhood_password = file.readline().strip()  # Read the second line for the password
except Exception as e:
    print(f"Failed to read file: {e}")

# Function to read tickers from JSON file
def read_tickers():
    if os.path.exists(json_file_path):
        with open(json_file_path, 'r') as file:
            return json.load(file)
    return []

# Function to write tickers to JSON file
def write_tickers(tickers):
    with open(json_file_path, 'w') as file:
        json.dump(tickers, file)

# Initialize Discord bot with intents
intents = discord.Intents.all()
intents.messages = True
bot = commands.Bot(command_prefix="$", intents=intents)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    await schedule_daily_sell()
    await schedule_daily_VOO()

@bot.event
async def on_message(message):
    if message.channel.id == buy_channel_id and message.content.startswith('$'):
        ticker = message.content[1:].strip().upper()
        print(f"Processing ticker: {ticker}")
        try:
            order_result = buy_stock_robinhood(ticker)
            await send_order_message(message.channel, order_result)
        except Exception as e:
            error_message = f"Failed to place order for {ticker}: {e}"
            await message.channel.send(error_message)
            print(error_message)

def buy_stock_robinhood(ticker):
    order_result = r.order_buy_market(ticker, 1)
    # Read existing tickers
    tickers = read_tickers()
    # Add new ticker to the list
    tickers.append(ticker)
    # Write updated tickers to JSON file
    write_tickers(tickers)
    return order_result

def buy_stock_robinhood_VOO(balance):
    balance = float(get_cash_balance())
    purchase_balance = balance - 5.0
    ticker = "VOO"
    r.order_buy_fractional_by_price(ticker, purchase_balance, timeInForce="gfd", extendedHours=False)

def sell_all_shares_robinhood():
    tickers = read_tickers()
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
    write_tickers(remaining_tickers)

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
    output_channel = bot.get_channel(sell_channel_id)
    await output_channel.send(message_text)
    print(message_text)

def get_cash_balance():
    account_info = r.profiles.load_account_profile()
    cash_balance = account_info.get("cash", "N/A")
    return cash_balance

async def send_order_message(channel, order_result):
    order_id = order_result.get('id', 'N/A')
    order_state = order_result.get('state', 'N/A')
    ticker = order_result.get('instrument', {}).get('symbol', 'N/A')
    message_text = f"Order placed for 1 share of {ticker}. Order ID: {order_id}, State: {order_state}"
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
    # Login using the read credentials
    if robinhood_email and robinhood_password:
        try:
            login = r.login(robinhood_email, robinhood_password)
            print("Logged in successfully to RobinHood!")
            
            await bot.start(discord_token)
            
        except Exception as e:
            print(f"Login failed: {e}")
    else:
        print("Failed to retrieve credentials.")

if __name__ == "__main__":
    asyncio.run(main())