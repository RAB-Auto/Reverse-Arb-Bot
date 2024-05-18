import robin_stocks.robinhood as r

file_path = 'C:/Users/arnav/OneDrive/Desktop/RobinPass.txt'

try:
    with open(file_path, 'r') as file:
        robinhood_email = file.readline().strip()  # Read the first line for the email
        robinhood_password = file.readline().strip()  # Read the second line for the password
except Exception as e:
    print(f"Failed to read file: {e}")

def login():
    login_result = r.login(robinhood_email, robinhood_password)
    return login_result

def get_cash_balance():
    account_info = r.profiles.load_account_profile()
    cash_balance = account_info.get("cash", "N/A")
    return cash_balance

login()
cash_balance = float(get_cash_balance())
purchase_balance = cash_balance - 5.0
ticker = "VOO"
r.order_buy_fractional_by_price(ticker, purchase_balance, timeInForce="gfd", extendedHours=False)

print(f"Cash Balance: ${cash_balance}")