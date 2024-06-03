import robin_stocks.robinhood as r
from public_invest_api import Public
from webull import webull
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
wb = webull()

# Define the file paths for credentials and JSON files
robinhood_file_path = 'C:/Users/arnav/OneDrive/Desktop/RAB/RobinPass.txt'
public_file_path = 'C:/Users/arnav/OneDrive/Desktop/RAB/PublicPass.txt'
webull_file_path = 'C:/Users/arnav/OneDrive/Desktop/RAB/WebullPass.txt'
robinhood_json_file_path = 'currentArbsRobinhood.json'
public_json_file_path = 'currentArbsPublic.json'
webull_json_file_path = 'currentArbsWebull.json'
holidays_json_file_path = 'market_holidays.json' # all 2024-2026 holdays are there (last updated: 05/20/2024)

# Initialize variables for credentials
robinhood_email = None
robinhood_password = None
public_username = None
public_password = None
webull_number = None
webull_password = None
webull_trade_token = None

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

# Read Webull credentials from file
try:
    with open(webull_file_path, 'r') as file:
        webull_number = file.readline().strip()
        webull_password = file.readline().strip()
        webull_trade_token = file.readline().strip()
except Exception as e:
    print(f"Failed to read Robinhood credentials file: {e}")

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

# Function to read holidays from JSON file
def read_holidays(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return json.load(file)
    return []

# Function to check if today is a holiday
def is_today_holiday(holidays):
    today = datetime.today().strftime('%Y-%m-%d')
    return today in holidays

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    
    # Send login messages
    login_message = []
    try:
        r.login(robinhood_email, robinhood_password)
        login_message.append("✅ Logged in successfully to RobinHood!")
    except Exception as e:
        login_message.append(f"❌ RobinHood login failed: {e}")

    try:
        public = Public()
        public.login(username=public_username, password=public_password, wait_for_2fa=True)
        login_message.append("✅ Logged in successfully to Public!")
    except Exception as e:
        login_message.append(f"❌ Public login failed: {e}")

    try:
        wb.login(webull_number, webull_password)
        login_result = wb.login(webull_number, webull_password)
        
        if 'accessToken' in login_result:
            login_message.append("✅ Logged in successfully to Webull!")
        else:
            login_message.append("❌ Webull login failed: Access token not found in the response.")
    except Exception as e:
        login_message.append(f"❌ Webull login failed: {e}")

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
        webull_result = None
        try:
            robinhood_result = buy_stock_robinhood(ticker)
        except Exception as e:
            print(f"Failed to place order for {ticker} on Robinhood: {e}")
        try:
            public_result = buy_stock_public(ticker)
        except Exception as e:
            print(f"Failed to place order for {ticker} on Public: {e}")
        try:
            webull_result = buy_stock_webull(ticker)
        except Exception as e:
            print(f"Failed to place order for {ticker} on Webull: {e}")

        await send_order_message(message.channel, ticker, robinhood_result, public_result, webull_result)

def get_stock_price(symbol: str):
    stock = yf.Ticker(symbol)
    data = stock.history(period='1d')
    if data.empty:
        print(f"No data for {symbol}")
        return None

    price = data['Close'].iloc[-1]
    return round(price, 2)

def buy_stock_robinhood(ticker):
    try:
        order_result = r.order_buy_market(ticker, 1)
        print(f"Robinhood order result: {order_result}")  # Debug log
        if 'id' in order_result:
            tickers = read_tickers(robinhood_json_file_path)
            tickers.append(ticker)
            write_tickers(robinhood_json_file_path, tickers)
        return order_result
    except Exception as e:
        print(f"Failed to place order for {ticker} on Robinhood: {e}")
        return {"detail": str(e)}

def buy_stock_public(ticker):
    # Initialize and login to Public
    public = Public()
    public.login(username=public_username, password=public_password, wait_for_2fa=True)
    
    # Place a market buy order
    try:
        response = public.place_order(
            symbol=ticker,
            quantity=1,  # Number of shares to buy
            side='buy',
            order_type='market',  # Market order
            time_in_force='gtc'  # Good 'til canceled
        )
        print(f"Public order result: {response}")  # Debug log
        if response.get('success', False):
            tickers = read_tickers(public_json_file_path)
            tickers.append(ticker)
            write_tickers(public_json_file_path, tickers)
        return response
    except Exception as e:
        error_message = str(e)
        if 'message' in error_message:
            try:
                error_message = eval(error_message).get('message', str(e))
            except:
                pass
        return {"success": False, "detail": error_message}

def buy_stock_webull(ticker):
    wb.login(webull_number, webull_password)
    wb.get_trade_token(webull_trade_token)
    price = get_stock_price(symbol=ticker)
    if price is None:
        return {"success": False, "detail": "Failed to get stock price"}

    try:
        if price <= 0.99:
            if price <= 0.1:
                order_result_buy = wb.place_order(action="BUY", stock=ticker, orderType="MKT", quant=1000, enforce="DAY")
                order_result_sell = wb.place_order(action="SELL", stock=ticker, orderType="MKT", quant=999, enforce="DAY")
            else:
                order_result_buy = wb.place_order(action="BUY", stock=ticker, orderType="MKT", quant=100, enforce="DAY")
                order_result_sell = wb.place_order(action="SELL", stock=ticker, orderType="MKT", quant=99, enforce="DAY")
        else:
            order_result_buy = wb.place_order(action="BUY", stock=ticker, orderType="MKT", quant=1, enforce="DAY")
        print(f"Webull buy order result for {ticker}: {order_result_buy}")

        if 'success' in order_result_buy and order_result_buy['success']:
            tickers = read_tickers(webull_json_file_path)
            tickers.append(ticker)
            write_tickers(webull_json_file_path, tickers)
        return order_result_buy

    except Exception as e:
        print(f"Webull order error for {ticker}: {e}")
        return {"success": False, "detail": str(e)}

async def send_order_message(channel, ticker, robinhood_result, public_result, webull_result):
    robinhood_status = "✅" if robinhood_result and 'id' in robinhood_result else f"❌ Robinhood: {robinhood_result.get('detail', 'Unknown error') if robinhood_result else 'Unknown error'}"
    public_status = "✅" if public_result and public_result.get('success', False) else f"❌ Public: {public_result.get('detail', 'Unknown error') if public_result else 'Unknown error'}"
    webull_status = "✅" if webull_result and webull_result.get('success', False) else f"❌ Webull: {webull_result.get('msg', webull_result.get('detail', 'Unknown error')) if webull_result else 'Unknown error'}"

    message_text = (
        f"Order for {ticker}:\n"
        f"Robinhood: {robinhood_status}\n"
        f"Public: {public_status}\n"
        f"Webull: {webull_status}"
    )
    await channel.send(message_text)
    print(message_text)

def buy_VOO_robinhood():
    try:
        buying_power = float(get_buying_power_robinhood())
        purchase_balance = buying_power - 5.0
        if purchase_balance < 1:
            return 'x'
        ticker = "VOO"
        order_result = r.orders.order_buy_fractional_by_price(ticker, purchase_balance, timeInForce="gfd", extendedHours=False)
        print(f"Order result: {order_result}")  # Debug log
        return buying_power - purchase_balance
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

def buy_SCHG_webull():
    try:
        wb.login(webull_number, webull_password)
        wb.get_trade_token(webull_trade_token)

        balance = float(get_cash_balance_webull())
        value_SCHG = get_stock_price("SCHG")
        money_for_SCHG = balance - value_SCHG
        money_needed_for_SCHG = money_for_SCHG - 200
        if(money_needed_for_SCHG <= 1):
            return "fail correctly"
        else:
            response = wb.place_order(stock = "SCHG", action = "BUY", orderType="MKT", quant=1, enforce="DAY")
        print(f"Public order result: {response}")  # Debug log
        new_balance = float(get_cash_balance_webull())
        return new_balance
    except Exception as e:
        print(f"Failed to buy VOO on Webull: {e}")
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

        # Fetch positions and print them for debugging
        positions = public.get_positions()
        print("Positions:", positions)  # Debug statement to print the positions

        for ticker in tickers:
            try:
                # Check if the ticker exists in the positions
                if any(position['instrument']['symbol'] == ticker for position in positions):
                    position = next(position for position in positions if position['instrument']['symbol'] == ticker)
                    shares = float(position['quantity'])
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

def sell_all_shares_webull():
    try:
        tickers = read_tickers(webull_json_file_path)
        result_messages = []
        tickers_to_remove = []

        if not tickers:
            result_messages.append("No stocks are currently bought.")
            return "\n".join(result_messages)

        wb.login(webull_number, webull_password)
        wb.get_trade_token(webull_trade_token)

        for ticker in tickers:
            try:
                positions = wb.get_positions()
                if any(position['ticker']['symbol'] == ticker for position in positions):
                    position = next(position for position in positions if position['ticker']['symbol'] == ticker)
                    shares = int(position['position'])
                    last_price = float(position['lastPrice'])
                    order_result = wb.place_order(action="SELL", stock=ticker, orderType="MKT", quant=shares, enforce="DAY")
                    if 'success' in order_result and order_result['success']:
                        message = f"Sold {shares} shares of {ticker} at ${last_price}."
                        result_messages.append(message)
                        tickers_to_remove.append(ticker)
                    else:
                        raise ValueError(f"Failed to sell shares of {ticker}. Order result: {order_result}")
                else:
                    message = f"{ticker} not in account, checking again tomorrow."
                    result_messages.append(message)
            except Exception as e:
                error_message = f"Failed to sell shares of {ticker} on Webull: {e}"
                result_messages.append(error_message)
        
        remaining_tickers = [ticker for ticker in tickers if ticker not in tickers_to_remove]
        write_tickers(webull_json_file_path, remaining_tickers)

        if not result_messages:
            result_messages.append("No stocks are currently bought.")
        
        return "\n".join(result_messages)
    except Exception as e:
        return f"Failed to process Webull shares: {e}"

async def sell_all_shares_discord():
    holidays = read_holidays(holidays_json_file_path)
    if is_today_holiday(holidays):
        await bot.get_channel(sell_channel_id).send("No sell trades for today: market holiday")
        print("No sell trades for today: market holiday")
        return

    robinhood_message = sell_all_shares_robinhood()
    public_message = sell_all_shares_public()
    webull_message = sell_all_shares_webull()
    sell_channel = bot.get_channel(sell_channel_id)
    final_message = f"Robinhood:\n{robinhood_message}\n\nPublic:\n{public_message}\n\nWebull:\n{webull_message}"
    if len(final_message) > 4000:
        await sell_channel.send("The message is too long to be displayed.")
    else:
        await sell_channel.send(final_message)
    print(final_message)

async def buy_VOO():
    holidays = read_holidays(holidays_json_file_path)
    if is_today_holiday(holidays):
        await bot.get_channel(alerts_channel_id).send("No buy trades for today: market holiday")
        print("No buy trades for today: market holiday")
        return

    robinhood_balance = None
    public_balance = None
    webull_balance = None

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

    try:
        webull_balance = buy_SCHG_webull()
    except Exception as e:
        print(f"Failed to buy SCHG on Webull: {e}")
        webull_balance = 'x'
    
    message_text = (
        f"Robinhood: Bought Daily VOO Shares with Arb Money. Balance: ${robinhood_balance}\n"
        f"Public: Bought Daily VOO Shares with Arb Money. Balance: ${public_balance}\n"
        f"Webull: Bought Daily SCHG Shares with Arb Money. Balance: ${webull_balance}"
    )
    
    output_channel = bot.get_channel(alerts_channel_id)
    await output_channel.send(message_text)
    print(message_text)

def get_buying_power_robinhood():
    try:
        account_info = r.profiles.load_account_profile()
        buying_power = account_info.get("buying_power", "N/A")
        return buying_power
    except Exception as e:
        print(f"Failed to get buying power from Robinhood: {e}")
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

def get_cash_balance_webull():
    try:
        wb.login(webull_number, webull_password)
        wb.get_trade_token(webull_trade_token)
        account = wb.get_account()
        day_buying_power = next(item['value'] for item in account['accountMembers'] if item['key'] == 'dayBuyingPower')
        return day_buying_power
    except Exception as e:
        print(f"Failed to get cash balance from Webull: {e}")
        return 'x'

# Schedule tasks, sell at 8:45 AM CST on weekdays and buy VOO at 9:00 AM CST on weekdays
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