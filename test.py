from webull import webull
import yfinance as yf
import math

webull_number = None
webull_password = None
webull_file_path = '/Users/karthikkurapati/Desktop/Credentials/webullpass.txt'

try:
    with open(webull_file_path, 'r') as file:
        webull_number = file.readline().strip()
        webull_password = file.readline().strip()
        webull_trade_token = file.readline().strip()
except Exception as e:
    print(f"Failed to read Webull credentials file: {e}")

wb = webull()
wb.login(webull_number, webull_password)
wb.get_trade_token(webull_trade_token)

def get_stock_price(symbol: str):
    stock = yf.Ticker(symbol)
    data = stock.history(period='1d')
    if data.empty:
        print(f"No data for {symbol}")
        return None

    price = data['Close'].iloc[-1]
    return round(price, 2)

def get_cash_balance_webull():
    wb.login(webull_number, webull_password)
    wb.get_trade_token(webull_trade_token)
    account = wb.get_account()
    day_buying_power = next(item['value'] for item in account['accountMembers'] if item['key'] == 'dayBuyingPower')
    return day_buying_power

def buy_SCHG_webull():
    try:
        wb.login(webull_number, webull_password)
        wb.get_trade_token(webull_trade_token)

        balance = float(get_cash_balance_webull())
        value_SCHG = get_stock_price("NVOS")
        money_for_SCHG = balance - value_SCHG
        money_needed_for_SCHG = money_for_SCHG - 100
        if(money_needed_for_SCHG <= 1):
            return "fail correctly"
        else:
            response = wb.place_order(stock = "NVOS", action = "BUY", orderType="MKT", quant=1, enforce="DAY")
        print(f"Public order result: {response}")  # Debug log
        new_balance = float(get_cash_balance_webull())
        return new_balance
    except Exception as e:
        print(f"Failed to buy VOO on Webull: {e}")
        return 'x'

print(buy_SCHG_webull())