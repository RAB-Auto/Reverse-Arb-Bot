import robin_stocks.robinhood as r
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Define the file path for the credentials
file_path = 'C:/Users/arnav/OneDrive/Desktop/RobinPass.txt'

# Initialize variables for credentials
email = None
password = None

# Function to send a login email
def send_email(message):
    sender_email = 'rab.send007@gmail.com'
    sender_password = 'kiui rdcy iswb mbsf'  # Use your app password here
    recipient_email = '7372242519@tmomail.net'  # Change this to your SMS gateway address

    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = recipient_email
    message['Subject'] = 'Robinhood Login Notification'
    body = "Logged in successfully to Robinhood!"
    message.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(message)
        server.quit()
        print("Login email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")
# Read the file and extract credentials
try:
    with open(file_path, 'r') as file:
        email = file.readline().strip()  # Read the first line for the email
        password = file.readline().strip()  # Read the second line for the password
except Exception as e:
    print(f"Failed to read file: {e}")

def manual_buy_stocks():
    while True:
        ticker = input("Enter a ticker symbol to buy, type 'exit' to quit: ")
        if ticker.lower() == "exit":
            break
        try:
            order_result = r.order_buy_market(ticker, 1)
            print(f"Order placed for 1 share of {ticker}: {order_result}")
        except Exception as e:
            print(f"Failed to place order for {ticker}: {e}")

def main():
    # Login using the read credentials
    if email and password:
        try:
            login = r.login(email, password)
            print("Logged in successfully!")
            send_email("Logged into RobinHood")

            manual_buy_stocks()
            
        except Exception as e:
            print(f"Login failed: {e}")
    else:
        print("Failed to retrieve credentials.")

main()