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

ft_ss = account.FTSession(username=firstrade_username, password=firstrade_password, pin=firstrade_pin)
ft_order = order.Order(ft_ss)

# Get account data
ft_accounts = account.FTAccountData(ft_ss)
if len(ft_accounts.account_numbers) < 1:
    raise Exception("No accounts found or an error occured exiting...")

def get_stock_price(symbol: str):
    stock = yf.Ticker(symbol)
    data = stock.history(period='1d')
    if data.empty:
        print(f"No data for {symbol}")
        return None

    price = data['Close'].iloc[-1]
    return round(price, 2)

def buy_VUG_firstrade():
    try:
        buying_power = float(get_buying_power_firstrade())
        purchase_balance = buying_power - 5.0
        balance_needed = purchase_balance - 5.0
        VUG_price = get_stock_price("VUG")
        quantity = purchase_balance / VUG_price
        if balance_needed < 1:
            return 'x'
        ticker = "VUG"
        ft_order.place_order(
            ft_accounts.account_numbers[0],
            symbol=ticker,
            price_type=order.PriceType.MARKET,
            order_type=order.OrderType.BUY,
            quantity=quantity,
            duration=order.Duration.DAY,
            dry_run=True,
        )
        new_buying_power = float(get_buying_power_firstrade())
        return new_buying_power
    except Exception as e:
        print(f"Failed to buy VUG on Firstrade: {e}")
        return 'x'
    
print(ft_order.order_confirmation)

def get_buying_power_firstrade():
    try:
        ft_accounts = account.FTAccountData(ft_ss)
        if len(ft_accounts.account_numbers) < 1:
            raise Exception("No accounts found or an error occurred exiting...")
        cash = ft_accounts.account_balances[0]
        cash_float = float(cash.replace('$', ''))
        return cash_float
    except Exception as e:
        print(f"Failed to get cash balance from Firstrade: {e}")
        return 'x'

print(buy_VUG_firstrade())