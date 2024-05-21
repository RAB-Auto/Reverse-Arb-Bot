import robin_stocks.robinhood as r
from public_invest_api import Public
import yfinance as yf
import math
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
    try:
        r.login(robinhood_email, robinhood_password)
        login_message.append("Logged in successfully to RobinHood!")
    except Exception as e:
        login_message.append(f"RobinHood login failed: {e}")

    try:
        public = Public()
        public.login(username=public_username, password=public_password, wait_for_2fa=True)
        login_message.append("Logged in successfully to Public!")
    except Exception as e:
        login_message.append(f"Public login failed: {e}")

    for message in login_message:
        print(message)
        await bot.get_channel(alerts_channel_id).send(message)
    
    asyncio.create_task(schedule_tasks())

@bot.event
async def on_message(message):
    if message.channel.id == buy_channel_id and message.content.startswith('$'):
        ticker = message.content[1:].strip().upper()
        print(f"Processing ticker: {ticker}")
        robinhood_result = None
        public_result = None
        try:
            robinhood_result = buy_stock_robinhood(ticker)
        except Exception as e:
            print(f"Failed to place order for {ticker} on Robinhood: {e}")
        try:
            public_result = buy_stock_public(ticker)
        except Exception as e:
            print(f"Failed to place order for {ticker} on Public: {e}")
        await send_order_message(message.channel, ticker, robinhood_result, public_result)

def get_stock_price(symbol: str):
    stock = yf.Ticker(symbol)
    data = stock.history(period='1d')
    if data.empty:
        print(f"No data for {symbol}")
        return None

    price = data['Close'].iloc[-1]
    return round(price, 2)

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

def buy_VOO_robinhood():
    try:
        balance = float(get_cash_balance_robinhood())
        purchase_balance = balance - 5.0
        ticker = "VOO"
        r.order_buy_fractional_by_price(ticker, purchase_balance, timeInForce="gfd", extendedHours=False)
        return balance - purchase_balance
    except Exception as e:
        print(f"Failed to buy VOO on Robinhood: {e}")
        return 'x'

def buy_VOO_public():
    try:
        public_instance = Public()
        public_instance.login(username=public_username, password=public_password, wait_for_2fa=True)
        
        balance = float(get_cash_balance_public(public_instance))
        if (balance - 5.0 < 1):
            return 'x'
        else:
            stock_price = get_stock_price('VOO')
            if stock_price is None:
                print("Failed to get stock price")
                return 'x'

            fractional = (balance - 5.0) / stock_price
            fractional = math.floor(fractional * 10000) / 10000  # Keep up to 4 decimal places

            response = public_instance.place_order(
                symbol='VOO',
                quantity=fractional,  # Number of shares to buy
                side='buy',
                order_type='market',
                time_in_force='gtc'
            )

        print(f"Public order result: {response}")  # Debug log
        return balance - (fractional * stock_price)
    except Exception as e:
        print(f"Failed to buy VOO on Public: {e}")
        return 'x'

def sell_all_shares_robinhood():
    tickers = read_tickers(robinhood_json_file_path)
    result_messages = []
    tickers_to_remove = []

    if not tickers:
        result_messages.append("No stocks are currently bought.")
        return "\n".join(result_messages)

    for ticker in tickers:
        try:
            positions = r.build_holdings()
            if ticker in positions:
                shares = float(positions[ticker]['quantity'])
                last_price = float(positions[ticker]['price'])
                order_result = r.order_sell_market(ticker, shares, timeInForce='gfd')
                if order_result and order_result.get('id'):
                    message = f"Sold {shares} shares of {ticker} at ${last_price}."
                    result_messages.append(message)
                    tickers_to_remove.append(ticker)
                else:
                    raise ValueError(f"Failed to sell shares of {ticker}. Order result: {order_result}")
            else:
                message = f"{ticker} not in account, checking again tomorrow."
                result_messages.append(message)
        except Exception as e:
            error_message = f"Failed to sell shares of {ticker} on Robinhood: {e}"
            result_messages.append(error_message)
    
    remaining_tickers = [ticker for ticker in tickers if ticker not in tickers_to_remove]
    write_tickers(robinhood_json_file_path, remaining_tickers)

    if not result_messages:
        result_messages.append("No stocks are currently bought.")
    
    return "\n".join(result_messages)

def sell_all_shares_public():
    try:
        tickers = read_tickers(public_json_file_path)
        result_messages = []
        tickers_to_remove = []

        if not tickers:
            result_messages.append("No stocks are currently bought.")
            return "\n".join(result_messages)

        public = Public()
        public.login(username=public_username, password=public_password, wait_for_2fa=True)

        for ticker in tickers:
            try:
                positions = public.get_positions()
                if ticker in positions:
                    shares = float(positions[ticker]['quantity'])
                    last_price = public.get_symbol_price(ticker)
                    order_result = public.place_order(
                        symbol=ticker,
                        quantity=shares,
                        side='sell',
                        order_type='market',
                        time_in_force='gtc'
                    )
                    if order_result.get('orderId'):
                        message = f"Sold {shares} shares of {ticker} at ${last_price}."
                        result_messages.append(message)
                        tickers_to_remove.append(ticker)
                    else:
                        raise ValueError(f"Failed to sell shares of {ticker}. Order result: {order_result}")
                else:
                    message = f"{ticker} not in account, checking again tomorrow."
                    result_messages.append(message)
            except Exception as e:
                error_message = f"Failed to sell shares of {ticker} on Public: {e}"
                result_messages.append(error_message)
        
        remaining_tickers = [ticker for ticker in tickers if ticker not in tickers_to_remove]
        write_tickers(public_json_file_path, remaining_tickers)

        if not result_messages:
            result_messages.append("No stocks are currently bought.")
        
        return "\n".join(result_messages)
    except Exception as e:
        return f"Failed to process Public shares: {e}"

async def sell_all_shares_discord():
    robinhood_message = sell_all_shares_robinhood()
    public_message = sell_all_shares_public()
    sell_channel = bot.get_channel(sell_channel_id)
    final_message = f"Robinhood:\n{robinhood_message}\n\nPublic:\n{public_message}"
    if len(final_message) > 4000:
        await sell_channel.send("The message is too long to be displayed.")
    else:
        await sell_channel.send(final_message)
    print(final_message)

async def buy_VOO():
    robinhood_balance = None
    public_balance = None

    try:
        robinhood_balance = buy_VOO_robinhood()
    except Exception as e:
        print(f"Failed to buy VOO on Robinhood: {e}")
        robinhood_balance = 'x'

    try:
        public_balance = buy_VOO_public()
    except Exception as e:
        print(f"Failed to buy VOO on Public: {e}")
        public_balance = 'x'
    
    message_text = (
        f"Robinhood: Bought Daily VOO Shares with Arb Money. Balance: ${robinhood_balance}\n"
        f"Public: Bought Daily VOO Shares with Arb Money. Balance: ${public_balance}"
    )
    
    output_channel = bot.get_channel(alerts_channel_id)
    await output_channel.send(message_text)
    print(message_text)

def get_cash_balance_robinhood():
    try:
        account_info = r.profiles.load_account_profile()
        cash_balance = account_info.get("cash", "N/A")
        return cash_balance
    except Exception as e:
        print(f"Failed to get cash balance from Robinhood: {e}")
        return 'x'

def get_cash_balance_public(public_instance):
    try:
        account_info = public_instance.get_portfolio()
        if account_info is None:
            return None
        return account_info["equity"]["cash"]
    except Exception as e:
        print(f"Failed to get cash balance from Public: {e}")
        return 'x'

async def send_order_message(channel, ticker, robinhood_result, public_result):
    robinhood_status = "✅" if robinhood_result and 'id' in robinhood_result else f"❌ Robinhood: {robinhood_result.get('detail', 'Unknown error') if robinhood_result else 'Unknown error'}"
    public_status = "✅" if public_result and public_result.get('success', False) else f"❌ Public: {public_result.get('detail', 'Unknown error') if public_result else 'Unknown error'}"
    
    message_text = (
        f"Order for {ticker}:\n"
        f"Robinhood: {robinhood_status}\n"
        f"Public: {public_status}"
    )
    await channel.send(message_text)
    print(message_text)

# Schedule daily sell at 8:45 AM CST on weekdays
async def schedule_tasks():
    if datetime.today().weekday() < 5:
        schedule.every().day.at("08:45").do(lambda: asyncio.create_task(sell_all_shares_discord()))
        schedule.every().day.at("09:00").do(lambda: asyncio.create_task(buy_VOO()))
    while True:
        schedule.run_pending()
        await asyncio.sleep(1)

async def main():
    await bot.start(discord_token)

if __name__ == "__main__":
    asyncio.run(main())