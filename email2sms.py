import smtplib
from email.mime.text import MIMEText

def send_sms_email(message, recipient_number, carrier_gateway):
    # Compose the email message
    email = MIMEText(message)
    email['From'] = 'rab.send007@gmail.com'
    email['To'] = f"{recipient_number}@{carrier_gateway}"

    try:
        # Connect to the SMTP server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Start TLS encryption
        server.login('rab.send007@gmail.com', 'pwga aydw xjgl rsqq')  # Use app password here if 2FA is enabled
        # Send the email
        server.sendmail('rab.send007@gmail.com', f"{recipient_number}@{carrier_gateway}", email.as_string())
        print("SMS sent successfully!")
    except smtplib.SMTPAuthenticationError:
        print("Failed to authenticate with the SMTP server. Check your credentials and app password.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        server.quit()

# Example usage
message = "Hello from Python!"
recipient_number = "2012033888"  # Update with recipient's phone number
carrier_gateway = "tmomail.net"  # Update with recipient's carrier gateway

send_sms_email(message, recipient_number, carrier_gateway)