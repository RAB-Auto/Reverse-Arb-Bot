from public_invest_api import Public
import yfinance as yf
import math

# Define the file path for the credentials
file_path = 'C:/Users/arnav/OneDrive/Desktop/PublicPass.txt'

# Initialize variables for credentials
public_username = None
public_password = None

# Read the file and extract credentials
try:
    with open(file_path, 'r') as file:
        public_username = file.readline().strip()  # Read the first line for the username
        public_password = file.readline().strip()  # Read the second line for the password
except Exception as e:
    print(f"Failed to read file: {e}")
    exit(1)  # Exit if there's an error reading the credentials

# Initialize and login to Public
public = Public()
public.login(
    username=public_username,
    password=public_password,
    wait_for_2fa=True  # When logging in for the first time, you need to wait for the SMS code
)

def get_stock_price(symbol: str):
    stock = yf.Ticker(symbol)
    data = stock.history(period='1d')
    if data.empty:
        print(f"No data for {symbol}")
        return None

    price = data['Close'].iloc[-1]
    return round(price, 2)

def get_account_cash(public_instance):
    account_info = public_instance.get_portfolio()
    if account_info is None:
        return None
    return account_info["equity"]["cash"]

def buy_VOO_public():
    # Initialize and login to Public
    public_instance = Public()
    public_instance.login(username=public_username, password=public_password, wait_for_2fa=True)
    
    balance = float(get_account_cash(public_instance))
    if (balance - 5.0 < 1):
        return False
    else:
        stock_price = get_stock_price('VOO')
        if stock_price is None:
            print("Failed to get stock price")
            return False

        fractional = (balance - 5.0) / stock_price
        fractional = math.floor(fractional * 10000) / 10000  # Keep up to 4 decimal places

        response = public_instance.place_order(
            symbol='VOO',
            quantity=fractional,  # Number of shares to buy
            side='buy',
            order_type='market',  # Market order
            time_in_force='gtc'  # Good 'til canceled
        )

    print(f"Public order result: {response}")  # Debug log

print(get_account_cash(public))
buy_VOO_public()