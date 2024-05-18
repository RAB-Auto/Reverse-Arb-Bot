from public_invest_api import Public

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

# Prompt the user for a ticker symbol
ticker_symbol = input("Enter the ticker symbol you want to buy: ").upper()

# Place a market buy order
try:
    response = public.place_order(
        symbol=ticker_symbol,
        quantity=1,  # Number of shares to buy
        side='BUY',
        order_type='MARKET',  # Market order
        time_in_force='DAY'  # Good for the day
    )
    print(f"Order placed successfully: {response}")
except Exception as e:
    print(f"Failed to place order: {e}")
