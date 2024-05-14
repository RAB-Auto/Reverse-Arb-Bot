import robin_stocks.robinhood as r
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Define the file path for the credentials
file_path = r'C:/Users/arnav/OneDrive/Desktop/RobinPass.txt'

# Initialize variables for credentials
email = None
password = None

# Read the file and extract credentials
with open(file_path, 'r') as file:
    email = file.readline().strip()  # Read the first line for the email
    password = file.readline().strip()  # Read the second line for the password

# Function to send a login email
def send_login_email():
    message = MIMEMultipart()
    message['From'] = 'rab.send007@gmail.com'
    message['To'] = email
    message['Subject'] = 'Reverse Arbitrage Alerts'
    body = "Logged in successfully to Robinhood!"
    message.attach(MIMEText(body, 'plain'))

    # Connect to the SMTP server
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login('rab.send007@gmail.com', 'pwga aydw xjgl rsqq')  # Use your app password here
    server.send_message(message)
    server.quit()

# Login using the read credentials
if email and password:
    login = r.login(email, password)
    print("Logged in successfully!")
    send_login_email()
else:
    print("Failed to retrieve credentials.")