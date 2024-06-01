from webull import webull

webull_file_path = 'C:/Users/arnav/OneDrive/Desktop/WebullPass.txt'

webull_email = None
webull_password = None

try:
    with open(webull_file_path, 'r') as file:
        webull_email = file.readline().strip()
        webull_password = file.readline().strip()
except Exception as e:
    print(f"Failed to read Robinhood credentials file: {e}")

wb = webull()

wb.login(webull_email, webull_password) # phone must be in format +[country_code]-[your number]
# wb._set_did('p3knh61evahe1wpnfn1l0f94l97srjp3')

print(wb.get_account())