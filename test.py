from webull import webull

webull_file_path = 'C:/Users/arnav/OneDrive/Desktop/RAB/WebullPass.txt'

webull_number = None
webull_password = None
webull_trade_token = None

try:
    with open(webull_file_path, 'r') as file:
        webull_number = file.readline().strip()
        webull_password = file.readline().strip()
        webull_trade_token = file.readline().strip()
except Exception as e:
    print(f"Failed to read Webull credentials file: {e}")

wb = webull()

try:
    login_result = wb.login(webull_number, webull_password)
    if 'accessToken' in login_result:
        wb.get_trade_token(webull_trade_token)  # Ensure the trade token is obtained
        positions = wb.get_positions()
        print("Positions:", positions)
    else:
        print("Webull login failed: Access token not found in the response.")
except Exception as e:
    print(f"Failed to login to Webull: {e}")
