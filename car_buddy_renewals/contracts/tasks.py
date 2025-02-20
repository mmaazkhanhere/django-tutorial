from celery import shared_task
from django.conf import settings
from contracts.models import User

from googleapiclient.discovery import build
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from email.mime.text import MIMEText
import base64
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Moves one level up
print(f"BASE_DIR: {BASE_DIR}")

# Paths to credentials files
CREDENTIALS_PATH = os.path.join(BASE_DIR, "contracts", "credentials.json")
print(f"CREDENTIALS_PATH: {CREDENTIALS_PATH}")

TOKEN_PATH = os.path.join(BASE_DIR, "contracts", "token.json")
print(f"TOKEN_PATH: {TOKEN_PATH}")

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def create_email_message(to, subject, message_text):
    """Create an email message in MIME format."""
    message = MIMEText(message_text)
    message["to"] = to
    message["subject"] = subject
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return {"raw": raw_message}


@shared_task
def send_renewal_emails():
    creds = None
    credentials_path = "./credentials.json"
    # Load credentials if token.json exists
    if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # Check if credentials are invalid/expired and refresh or reauthenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(GoogleRequest())
                print("✅ Gmail API credentials refreshed successfully.")
            except Exception as e:
                print("❌ Failed to refresh token:", e)
                creds = None  # Force re-authentication

        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)  # Opens a browser for authentication

            # Save the new credentials for future use
            with open(TOKEN_PATH, "w") as token_file:
                token_file.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds)

    users_to_contact = User.objects.filter(is_contacted=False)

    for user in users_to_contact:
        subject = "PCP Contract Renewal"
        message = """
            Hi Maaz, 
            Your contract with us will run out in 12 months!
            Please contact us to arrange an appointment
            Kind Regards,
            Automotive Dealers | Bookings Team
        """

        recipient_email = user.email

        email_message = create_email_message(recipient_email, subject, message)

        try:
            service.users().messages().send(userId="me", body=email_message).execute()
            user.is_contacted = True
            user.save()
        except Exception as error:
            print('An error occurred: %s' % error)

    return f"Renewal emails send to {users_to_contact.count()} customers"