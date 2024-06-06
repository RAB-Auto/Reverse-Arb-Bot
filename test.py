from firstrade import account, order, symbols
import yfinance as yf

firstrade_file_path = 'C:/Users/arnav/OneDrive/Desktop/RAB/FirstradePass.txt'

firstrade_username = None
firstrade_password = None
firstrade_pin = None

try:
    with open(firstrade_file_path, 'r') as file:
        firstrade_username = file.readline().strip()
        firstrade_password = file.readline().strip()
        firstrade_pin = file.readline().strip()
except Exception as e:
    print(f"Failed to read Firstrade credentials file: {e}")

def get_stock_price(symbol: str):
    stock = yf.Ticker(symbol)
    data = stock.history(period='1d')
    if data.empty:
        print(f"No data for {symbol}")
        return None

    price = data['Close'].iloc[-1]
    return round(price, 2)

ft_ss = account.FTSession(username=firstrade_username, password=firstrade_password, pin=firstrade_pin)
ft_order = order.Order(ft_ss)

# Get account data
ft_accounts = account.FTAccountData(ft_ss)

def get_buying_power_firstrade():
    try:
        cash = ft_accounts.account_balances[0]
        cash_float = float(cash.replace('$', '').replace(',', ''))
        
        positions = ft_accounts.get_positions(ft_accounts.account_numbers[0])
        
        total_stock_value = 0.0
        
        for symbol, data in positions.items():
            quantity = float(data['quantity'].replace(',', ''))
            price = float(data['price'].replace('+', '').replace(',', ''))
            stock_value = quantity * price
            total_stock_value += stock_value
        
        cash_balance = cash_float - total_stock_value
        return cash_balance
    
    except Exception as e:
        print(f"Failed to get cash balance from Firstrade: {e}")
        return 'x'

print(get_buying_power_firstrade())