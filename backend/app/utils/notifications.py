import time
from datetime import datetime

def send_email(
        to: str, 
        subject: str, 
        body: str
        ):
    """Simulate sending an email"""
    print(f"[EMAIL] Sending to {to}")
    time.sleep(2) # Simulated netword delay
    print(f"[EMAIL] Sent: '{subject}' to {to}")

    with open("email_log.txt", "a") as f:
        f.write(f"{datetime.now()}  |  To: {to}  | Subject: {subject}\n")