from webull import webull
import yfinance as yf

webull_file_path = 'C:/Users/arnav/OneDrive/Desktop/WebullPass.txt'

webull_email = None
webull_password = None
trade_token = None

def get_stock_price(symbol: str):
    stock = yf.Ticker(symbol)
    data = stock.history(period='1d')
    if data.empty:
        print(f"No data for {symbol}")
        return None

    price = data['Close'].iloc[-1]
    return round(price, 2)

try:
    with open(webull_file_path, 'r') as file:
        webull_email = file.readline().strip()
        webull_password = file.readline().strip()
        webull_trade_token = file.readline().strip()
except Exception as e:
    print(f"Failed to read Robinhood credentials file: {e}")

try:
    wb = webull()
    login_result = wb.login(webull_email, webull_password)
    
    # Check if login was successful by verifying if 'accessToken' is in the result
    if 'accessToken' in login_result:
        print("Logged in successfully to Webull!")
    else:
        print("Webull login failed: Access token not found in the response.")
except Exception as e:
    print(f"Webull login failed: {e}")

def buy_stock_webull(ticker):
    wb.get_trade_token(webull_trade_token)  # Ensure the trade token is obtained once
    price = float(get_stock_price(symbol=ticker))
    try:
        if price <= 0.99:
            if price <= 0.1:
                order_result_buy = wb.place_order(action="BUY", stock=ticker, orderType="LMT", quant=1000, price=price)
                order_result_sell = wb.place_order(action="SELL", stock=ticker, orderType="LMT", quant=999, price=price)
            else:
                order_result_buy = wb.place_order(action="BUY", stock=ticker, orderType="LMT", quant=100, price=price)
                order_result_sell = wb.place_order(action="SELL", stock=ticker, orderType="LMT", quant=99, price=price)
        else:
            order_result_buy = wb.place_order(action="BUY", stock=ticker, orderType="LMT", quant=1, price=price)
        print(f"Webull buy order result for {ticker}: {order_result_buy}")
        return order_result_buy

    except Exception as e:
        print(f"Webull order error for {ticker}: {e}")
        return None

ticker = input("What ticker: ")

buy_stock_webull(ticker)