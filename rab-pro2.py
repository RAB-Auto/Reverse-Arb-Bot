import robin_stocks.robinhood as r
import discord
from discord.ext import commands
import os
import json
import schedule
import time
from datetime import datetime
import asyncio

# Define the file path for the credentials and JSON file
file_path = 'C:/Users/arnav/OneDrive/Desktop/RobinPass.txt'
json_file_path = 'currentArbs.json'

# Initialize variables for credentials
robinhood_email = None
robinhood_password = None
discord_token = 'YOUR_DISCORD_TOKEN'  # Replace with your Discord bot token
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

@bot.event
async def on_message(message):
    if message.channel.id == buy_channel_id and message.content.startswith('$'):
        ticker = message.content[1:].strip().upper()
        print(f"Processing ticker: {ticker}")
        try:
            order_result = r.order_buy_market(ticker, 1)
            # Read existing tickers
            tickers = read_tickers()
            # Add new ticker to the list
            tickers.append(ticker)
            # Write updated tickers to JSON file
            write_tickers(tickers)
            # Extract relevant information from order_result
            order_id = order_result.get('id', 'N/A')
            order_state = order_result.get('state', 'N/A')
            await message.channel.send(f"Order placed for 1 share of {ticker}. Order ID: {order_id}, State: {order_state}")
            print(f"Order placed for 1 share of {ticker}. Order ID: {order_id}, State: {order_state}")
        except Exception as e:
            await message.channel.send(f"Failed to place order for {ticker}: {e}")
            print(f"Failed to place order for {ticker}: {e}")

async def sell_all_shares():
    tickers = read_tickers()
    for ticker in tickers:
        try:
            positions = r.build_holdings()
            if ticker in positions:
                shares = float(positions[ticker]['quantity'])
                price = positions[ticker]['average_buy_price']
                print(f"Attempting to sell {shares} shares of {ticker} at ${price} each.")
                order_result = r.order_sell_market(ticker, shares)
                # Notify in the sell channel
                sell_channel = bot.get_channel(sell_channel_id)
                await sell_channel.send(f"Sold {shares} shares of {ticker} at ${price} each. Order ID: {order_result.get('id', 'N/A')}, State: {order_result.get('state', 'N/A')}")
                print(f"Sold {shares} shares of {ticker} at ${price} each. Order ID: {order_result.get('id', 'N/A')}, State: {order_result.get('state', 'N/A')}")
                # Remove ticker from list after successful sell
                tickers.remove(ticker)
                write_tickers(tickers)
        except Exception as e:
            print(f"Failed to sell shares of {ticker}: {e}")

async def schedule_daily_sell():
    # Schedule the sell_all_shares function to run at 8:30 AM CST every weekday
    if datetime.today().weekday() < 5:  # Check if today is a weekday (Monday to Friday)
        schedule.every().day.at("09:30").do(lambda: asyncio.ensure_future(sell_all_shares()))

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