import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from seleniumbase import Driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time 
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import os
import json
import schedule

command_channel_id = 1249116072423067718 # Replace with your channel ID for commands
confirmation_channel_id = 1258928209081274440 # Replace with your notification channel ID
buy_channel_id = 1240105481259716669 # Replace with your channel ID for buy confirmations

# Initialize Discord bot with intents
class MyBot(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scraping_running = False

intents = discord.Intents.all()
intents.messages = True
bot = MyBot(command_prefix="^", intents=intents)
discord_token = ""

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="Pondering 🔍"))
    await bot.tree.sync()
    print(f'We have logged in as {bot.user}')
    asyncio.create_task(schedule_tasks())

# Load market holidays from JSON
with open('market_holidays.json') as f:
    market_holidays = json.load(f)

# Web scraping functions
def is_reverse_split(ratio):
    parts = ratio.split(':')
    return int(parts[0]) > int(parts[1])

def is_future_date(date_str):
    split_date = datetime.strptime(date_str, '%Y-%m-%d')
    return split_date > datetime.now()

def hedgeFollowStocks(driver, current_date):
    print("Starting to scrape the HedgeFollow website...")
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
            
            if exchange == 'NASDAQ' and is_future_date(ex_date):
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
    print(f"CSV file {output_file} created successfully.")

    return df

def validate_stock(driver, stock_name):
    print(f"Validating stock: {stock_name}")
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
    keywords = ['round', 'rounding', 'cash in lieu', 'rounding up', 'additional shares']

    return any(keyword in page_text for keyword in keywords)

def get_last_trading_day(split_date):
    split_date = datetime.strptime(split_date, '%Y-%m-%d')
    last_day_to_buy = split_date - timedelta(days=1)
    
    while last_day_to_buy.strftime('%Y-%m-%d') in market_holidays or last_day_to_buy.weekday() >= 5:  # 5 and 6 correspond to Saturday and Sunday
        last_day_to_buy -= timedelta(days=1)
    
    return last_day_to_buy.strftime('%Y-%m-%d')

@bot.tree.command(name="find", description="Webscrape and find the upcoming splits that are rounding")
async def find_splits(interaction: discord.Interaction):
    if interaction.channel.id != command_channel_id:
        await interaction.response.send_message(f"This command can only be used in the designated command channel: <#{command_channel_id}>", ephemeral=True)
        return

    current_time = datetime.now()
    scheduled_time = current_time.replace(hour=8, minute=50, second=0, microsecond=0)
    if abs((current_time - scheduled_time).total_seconds()) <= 300:  # 5 minutes
        await interaction.response.send_message(f"Cannot run the command right now. The scheduler is about to run in {(scheduled_time - current_time).seconds // 60} minutes.", ephemeral=True)
        return

    if bot.scraping_running:
        await interaction.response.send_message("A scraping task is already running. Please wait until it completes.")
        return

    bot.scraping_running = True
    await interaction.response.send_message("Starting the web scraping task. This may take a few minutes...")
    
    try:
        driver = Driver(headed=True)
        driver.get("https://hedgefollow.com/upcoming-stock-splits.php")
        current_date = datetime.now().strftime('%d%b').lower()
        df = hedgeFollowStocks(driver, current_date)
        
        valid_stock = []
        for i, row_stock in df.iterrows():
            if validate_stock(driver, row_stock['stock']):
                row_stock['last_day_to_buy'] = get_last_trading_day(row_stock['ex_date'])
                valid_stock.append(row_stock)
        
        valid_stock_df = pd.DataFrame(valid_stock)
        valid_csv_file = f'valid_stock_{current_date}.csv'
        
        if os.path.isfile(valid_csv_file):
            os.remove(valid_csv_file)
        valid_stock_df.to_csv(valid_csv_file, index=False)
        print(f"Validated CSV file {valid_csv_file} created successfully.")
        driver.quit()
        
        # Create and send the embed
        embed = discord.Embed(title="Upcoming Stock Splits 📈", color=0x00ff00)
        embed.add_field(name="SPLIT DATE, TICKER SYMBOL, SPLIT:RATIO, LAST DAY TO BUY", value="\u200b", inline=False)
        stocks_to_buy_today = []
        today = datetime.now().strftime('%Y-%m-%d')
        emoji_numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']

        for idx, (_, row) in enumerate(valid_stock_df.iterrows(), start=1):
            emoji = emoji_numbers[idx - 1] if idx - 1 < len(emoji_numbers) else f"{idx}️⃣"
            embed.add_field(
                name="\u200b",
                value=f"{emoji} {row['ex_date']}, **{row['stock']}**, {row['split_ratio']}, **{row['last_day_to_buy']}**",
                inline=False
            )
            if row['last_day_to_buy'] == today:
                stocks_to_buy_today.append(row['stock'])

        stocks_message = f"Stocks to buy today: {', '.join(stocks_to_buy_today) if stocks_to_buy_today else 'NONE'}"
        embed.add_field(name="Stocks to Buy Today", value=stocks_message, inline=False)
        
        await interaction.followup.send(embed=embed)
    finally:
        bot.scraping_running = False

async def send_confirmation(channel, stocks_to_buy):
    if not stocks_to_buy:
        return

    stock = stocks_to_buy.pop(0)
    embed = discord.Embed(title="Stock Confirmation", description=f"Confirm buying **{stock}**?", color=0x00ff00)
    embed.set_footer(text="React with ✅ to confirm or ❌ to reject.")

    message = await channel.send(embed=embed)
    await message.add_reaction("✅")
    await message.add_reaction("❌")

    def check(reaction, user):
        return user != bot.user and str(reaction.emoji) in ["✅", "❌"]

    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=600.0, check=check)
        if str(reaction.emoji) == "✅":
            buy_channel = bot.get_channel(buy_channel_id)
            await buy_channel.send(f"${stock}")
            await channel.send(f"**{stock}** confirmed and sent to <#{buy_channel_id}>.")
        elif str(reaction.emoji) == "❌":
            await channel.send(f"**{stock}** rejected. Moving onto the next.")
        
        await message.delete()
        
        if stocks_to_buy:
            await send_confirmation(channel, stocks_to_buy)
        else:
            await channel.send("NONE left.")
    except asyncio.TimeoutError:
        await message.delete()
        await channel.send(f"**{stock}** confirmation timed out. Moving onto the next.")
        if stocks_to_buy:
            await send_confirmation(channel, stocks_to_buy)
        else:
            await channel.send("NONE left.")

async def scrape_and_notify():
    if bot.scraping_running:
        print("A scraping task is already running. Please wait until it completes.")
        return

    bot.scraping_running = True
    try:
        channel = bot.get_channel(confirmation_channel_id)
        await channel.send("Running web scraper for today.")
        
        driver = Driver(headed=True)
        driver.get("https://hedgefollow.com/upcoming-stock-splits.php")
        current_date = datetime.now().strftime('%d%b').lower()
        df = hedgeFollowStocks(driver, current_date)
        
        valid_stock = []
        for i, row_stock in df.iterrows():
            if validate_stock(driver, row_stock['stock']):
                row_stock['last_day_to_buy'] = get_last_trading_day(row_stock['ex_date'])
                valid_stock.append(row_stock)
        
        valid_stock_df = pd.DataFrame(valid_stock)
        valid_csv_file = f'valid_stock_{current_date}.csv'
        
        if os.path.isfile(valid_csv_file):
            os.remove(valid_csv_file)
        valid_stock_df.to_csv(valid_csv_file, index=False)
        print(f"Validated CSV file {valid_csv_file} created successfully.")
        driver.quit()
        
        # Create and send the embed
        embed = discord.Embed(title="Upcoming Stock Splits 📈", color=0x00ff00)
        embed.add_field(name="SPLIT DATE, TICKER SYMBOL, SPLIT:RATIO, LAST DAY TO BUY", value="\u200b", inline=False)
        stocks_to_buy_today = []
        today = datetime.now().strftime('%Y-%m-%d')
        emoji_numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']

        for idx, (_, row) in enumerate(valid_stock_df.iterrows(), start=1):
            emoji = emoji_numbers[idx - 1] if idx - 1 < len(emoji_numbers) else f"{idx}️⃣"
            embed.add_field(
                name="\u200b",
                value=f"{emoji} {row['ex_date']}, **{row['stock']}**, {row['split_ratio']}, **{row['last_day_to_buy']}**",
                inline=False
            )
            if row['last_day_to_buy'] == today:
                stocks_to_buy_today.append(row['stock'])

        stocks_message = f"Stocks to buy today: {', '.join(stocks_to_buy_today) if stocks_to_buy_today else 'NONE'}"
        embed.add_field(name="Stocks to Buy Today", value=stocks_message, inline=False)
        
        await channel.send(embed=embed)
        
        if stocks_to_buy_today:
            await send_confirmation(channel, stocks_to_buy_today)
    finally:
        bot.scraping_running = False

async def schedule_tasks():
    schedule.every().monday.at("08:50").do(lambda: asyncio.create_task(scrape_and_notify()))
    schedule.every().tuesday.at("08:50").do(lambda: asyncio.create_task(scrape_and_notify()))
    schedule.every().wednesday.at("08:50").do(lambda: asyncio.create_task(scrape_and_notify()))
    schedule.every().thursday.at("08:50").do(lambda: asyncio.create_task(scrape_and_notify()))
    schedule.every().friday.at("19:22").do(lambda: asyncio.create_task(scrape_and_notify()))

    while True:
        schedule.run_pending()
        await asyncio.sleep(1)

async def main():
    async with bot:
        await bot.start(discord_token)

if __name__ == "__main__":
    asyncio.run(main())
