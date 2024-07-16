import uuid
import os
import sys
import discord
from discord.ext import commands, tasks
from seleniumbase import Driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import json
import pytz
import asyncio

# Function to get the device's unique identifier
def get_device_identifier():
    # Get the MAC address
    mac = uuid.getnode()
    return mac

# Define the allowed device's identifier (replace this with your specific device's identifier)
ALLOWED_DEVICE_IDENTIFIER = 158394315091676  # Replace with real MAC Address

def check_device():
    current_device_identifier = get_device_identifier()
    if current_device_identifier != ALLOWED_DEVICE_IDENTIFIER:
        print("This program can only be run on the authorized device. Please contact us if there is an issue.")
        sys.exit(1)

# Call the device check function at the beginning of your main script
check_device()

if hasattr(sys, '_MEIPASS'):
    json_path = os.path.join(sys._MEIPASS, 'market_holidays.json')
else:
    json_path = 'market_holidays.json'

with open(json_path, 'r') as f:
    holidays = json.load(f)

def get_previous_trading_day(date):
    date -= pd.Timedelta(days=1)
    while date.weekday() >= 5 or date.strftime('%Y-%m-%d') in holidays:
        date -= pd.Timedelta(days=1)
    return date

CONFIG_FILE = 'config.json'
AUTO_TRADE_FILE = 'auto_trade.json'

def save_config(token, cmd_channel, conf_channel, buy_channel):
    config = {
        "DISCORD_TOKEN": token,
        "commands_channel_id": cmd_channel,
        "confirmations_channel_id": conf_channel,
        "buy_channel_id": buy_channel
    }
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def load_config():
    if os.path.isfile(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    else:
        return None

def save_auto_trade_setting(auto_trade):
    with open(AUTO_TRADE_FILE, 'w') as f:
        json.dump({"auto_trade": auto_trade}, f)

def load_auto_trade_setting():
    if os.path.isfile(AUTO_TRADE_FILE):
        with open(AUTO_TRADE_FILE, 'r') as f:
            return json.load(f).get("auto_trade", False)
    else:
        return False

config = load_config()
if config:
    DISCORD_TOKEN = config["DISCORD_TOKEN"]
    commands_channel_id = config["commands_channel_id"]
    confirmations_channel_id = config["confirmations_channel_id"]
    buy_channel_id = config["buy_channel_id"]
else:
    DISCORD_TOKEN = input("Enter your Discord bot token: ")
    commands_channel_id = int(input("Enter the commands channel ID: "))
    confirmations_channel_id = int(input("Enter the confirmations channel ID: "))
    buy_channel_id = int(input("Enter the buy channel ID: "))
    save_config(DISCORD_TOKEN, commands_channel_id, confirmations_channel_id, buy_channel_id)

auto_trade = load_auto_trade_setting()

# Initialize the Discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Function to check if a split ratio represents a reverse split
def is_reverse_split(ratio):
    parts = ratio.split(':')
    return int(parts[0]) < int(parts[1])

# Function to check if the date is in the future
def is_future_date(date_str):
    split_date = datetime.strptime(date_str, '%Y-%m-%d')
    return split_date > datetime.now()

def hegdgeFollowStocks(driver, current_date):
    html_content = driver.page_source  
    soup = BeautifulSoup(html_content, 'html.parser')

    table = soup.find('table', id='latest_splits')
    rows = table.find('tbody').find_all('tr')

    data = []

    for row in rows:
        try:
            stock = row.find_all('td')[0].get_text(strip=True)
            exchange = row.find_all('td')[1].get_text(strip=True)
            company_name = row.find_all('td')[2].get_text(strip=True)
            split_ratio = row.find_all('td')[3].get_text(strip=True)
            ex_date = row.find_all('td')[4].get_text(strip=True)
            ann_date = row.find_all('td')[5].get_text(strip=True)
            
            if exchange in ['NASDAQ', 'AMEX', 'NYSE'] and is_reverse_split(split_ratio) and is_future_date(ex_date):
                row_dict = {
                    'stock': stock,
                    'exchange': exchange,
                    'company_name': company_name,
                    'split_ratio': split_ratio,
                    'ex_date': ex_date,
                    'ann_date': ann_date
                }
                data.append(row_dict)
        except Exception as e:
            continue

    df = pd.DataFrame(data)
    output_file = f'upcoming_reverse_splits_{current_date}.csv'

    if os.path.isfile(output_file):
        os.remove(output_file)
    df.to_csv(output_file, index=False)

    return df

def validate_stock(driver, stock_name):
    driver.get('https://www.stocktitan.net/')
    try:
        search_btn = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "bi.bi-search"))
        )
    except Exception as e:
        print(f"An error occurred: {e}")
    time.sleep(5)

    try:
        search = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/header/div/div[3]/form/div/div/input"))
        )
        search.click()
    except Exception as e:
        print(f"An error occurred: {e}")
    search.send_keys(stock_name)
    search_btn[2].click()
    
    try:
        blog = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "symbol-link"))
        )
        blog.click()
    except Exception as e:
        print(f"An error occurred: {e}")
    
    page_text = driver.find_element(By.TAG_NAME, 'body').text
    keywords = ["rounding", "rounding up", "rounded up", "additional shares", "nearest whole share"]
    phrases = ["rounded up or canceled"]

    return any(keyword in page_text for keyword in keywords) and not any(phrase in page_text for phrase in phrases)

# Update for global declaration and auto trading
async def scrape_and_verify():
    global auto_trade
    confirmations_channel = bot.get_channel(confirmations_channel_id)
    await confirmations_channel.send("Starting auto scraping for the day")

    driver = Driver(headed=True)
    driver.get("https://hedgefollow.com/upcoming-stock-splits.php")
    current_date = datetime.now().strftime('%d%b').lower()
    
    df = hegdgeFollowStocks(driver, current_date)
    valid_stock = []

    for i, row_stock in df.iterrows():
        if validate_stock(driver, row_stock['stock']):
            valid_stock.append(row_stock)
    
    if valid_stock:
        valid_stock_df = pd.DataFrame(valid_stock)
        valid_stock_file = f'valid_stock_{current_date}.csv'
    
        if os.path.isfile(valid_stock_file):
            os.remove(valid_stock_file)
        valid_stock_df.to_csv(valid_stock_file, index=False)
    
        valid_stocks_list = []
        stocks_to_buy_today = []
        today = datetime.now().strftime('%Y-%m-%d')
        
        for _, row in valid_stock_df.iterrows():
            ex_date = datetime.strptime(row['ex_date'], '%Y-%m-%d')
            buy_date = get_previous_trading_day(ex_date)
            valid_stocks_list.append(f"${row['stock']}, SPLIT DATE: {row['ex_date']}, LAST DAY TO BUY: {buy_date.strftime('%Y-%m-%d')}")
            if buy_date.strftime('%Y-%m-%d') == today:
                stocks_to_buy_today.append(f"${row['stock']}")

        embed = discord.Embed(title="Valid Stocks", description="Stocks with upcoming splits", color=0x00ff00)
        embed.add_field(name="Stocks", value='\n'.join(valid_stocks_list), inline=False)
        
        if stocks_to_buy_today:
            embed.add_field(name="STOCKS TO BUY TODAY", value='\n'.join(stocks_to_buy_today), inline=False)
        
        await confirmations_channel.send(embed=embed)
        
        if stocks_to_buy_today:
            if auto_trade:
                buy_channel = bot.get_channel(buy_channel_id)
                for stock in stocks_to_buy_today:
                    await buy_channel.send(f"${stock}")
            else:
                for stock in stocks_to_buy_today:
                    message = await confirmations_channel.send(f"@everyone Would you like to buy {stock}? If you would like to enable auto trading, please type 'I understand and accept the risks with turning on auto trading. I am choosing to accept this and I know that the bot may not function perfectly and I do not hold the makers of the bot accountable.'")
                    await message.add_reaction("✅")
                    await message.add_reaction("❌")

                    def check(reaction, user):
                        return user != bot.user and str(reaction.emoji) in ["✅", "❌"]

                    def check_message(msg):
                        return msg.channel == confirmations_channel and msg.content.strip().lower() == 'i understand and accept the risks with turning on auto trading. i am choosing to accept this and i know that the bot may not function perfectly and i do not hold the makers of the bot accountable.'

                    try:
                        reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
                        if str(reaction.emoji) == "✅":
                            buy_channel = bot.get_channel(buy_channel_id)
                            await buy_channel.send(f"${stock}")
                        else:
                            await confirmations_channel.send(f"Ok, will not buy {stock}.")
                    except asyncio.TimeoutError:
                        await confirmations_channel.send(f"No response for {stock}, skipping.")

                    try:
                        msg = await bot.wait_for('message', timeout=60.0, check=check_message)
                        if msg:
                            save_auto_trade_setting(True)
                            auto_trade = True
                            await confirmations_channel.send("Auto trading has been enabled.")
                            break
                    except asyncio.TimeoutError:
                        pass
    else:
        await confirmations_channel.send("No valid stocks found.")
    driver.quit()

@tasks.loop(minutes=1)
async def scheduled_scrape():
    now = datetime.now(pytz.timezone('America/Chicago'))
    if now.weekday() >= 5 or now.strftime('%Y-%m-%d') in holidays:
        buy_channel = bot.get_channel(buy_channel_id)
        await buy_channel.send("Market Holiday or Weekend, not auto scraping for today. If there is an issue, contact us.")
        return
    if now.hour == 8 and now.minute == 50:
        await scrape_and_verify()

@bot.command()
async def splits(ctx):
    if ctx.channel.id != commands_channel_id:
        return await ctx.send(f"You can only use this command in the commands channel. <#{commands_channel_id}>")
    
    now = datetime.now(pytz.timezone('America/Chicago'))
    scrape_time = now.replace(hour=8, minute=50, second=0, microsecond=0)
    if now >= scrape_time - timedelta(minutes=5) and now < scrape_time:
        minutes_left = (scrape_time - now).seconds // 60
        return await ctx.send(f"You need to wait because the autoscrape starts in {minutes_left} minutes...")

    await ctx.send("Give us a minute, analyzing online now...")
    driver = Driver(headed=True)
    driver.get("https://hedgefollow.com/upcoming-stock-splits.php")
    current_date = datetime.now().strftime('%d%b').lower()
    
    df = hegdgeFollowStocks(driver, current_date)
    valid_stock = []

    for i, row_stock in df.iterrows():
        if validate_stock(driver, row_stock['stock']):
            valid_stock.append(row_stock)
    
    if valid_stock:
        valid_stock_df = pd.DataFrame(valid_stock)
        valid_stock_file = f'valid_stock_{current_date}.csv'
    
        if os.path.isfile(valid_stock_file):
            os.remove(valid_stock_file)
        valid_stock_df.to_csv(valid_stock_file, index=False)
    
        valid_stocks_list = []
        stocks_to_buy_today = []
        today = datetime.now().strftime('%Y-%m-%d')
        
        for _, row in valid_stock_df.iterrows():
            ex_date = datetime.strptime(row['ex_date'], '%Y-%m-%d')
            buy_date = get_previous_trading_day(ex_date)
            valid_stocks_list.append(f"${row['stock']}, SPLIT DATE: {row['ex_date']}, LAST DAY TO BUY: {buy_date.strftime('%Y-%m-%d')}")
            if buy_date.strftime('%Y-%m-%d') == today:
                stocks_to_buy_today.append(f"${row['stock']}")

        embed = discord.Embed(title="Valid Stocks", description="Stocks with upcoming splits", color=0x00ff00)
        embed.add_field(name="Stocks", value='\n'.join(valid_stocks_list), inline=False)
        
        if stocks_to_buy_today:
            embed.add_field(name="STOCKS TO BUY TODAY", value='\n'.join(stocks_to_buy_today), inline=False)
        
        await ctx.send(embed=embed)
    else:
        await ctx.send("No valid stocks found.")
    
    driver.quit()

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="🌐 Created by @lightness9116 and @vortex_overdrive"))

    if not scheduled_scrape.is_running():
        scheduled_scrape.start()

bot.run(DISCORD_TOKEN)
