import smtplib
from email.mime.text import MIMEText

SMTP_SERVER = "smtp.office365.com"
SMTP_PORT = 587
SMTP_USER = "bl.en.u4cse23255@bl.students.amrita.edu"
SMTP_PASS = "Bhavitha@28"

def test_smtp():
    try:
        msg = MIMEText("Test email")
        msg["Subject"] = "SMTP Test"
        msg["From"] = SMTP_USER
        msg["To"] = SMTP_USER

        print("Connecting to server...")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            print("Starting TLS...")
            server.starttls()
            print("Logging in...")
            server.login(SMTP_USER, SMTP_PASS)
            print("Sending message...")
            server.send_message(msg)
        print("Success!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_smtp()
