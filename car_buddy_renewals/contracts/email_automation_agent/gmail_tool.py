import os
import re
import uuid
import base64
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

class GmailToolsClass:
    def __init__(self):
        self.service = self._get_gmail_service()

    
    def _get_gmail_service(self):
        """
        Returns an authenticated Gmail service.  
        If token.json exists, it loads the credentials and refreshes them if needed.
        Otherwise, it runs the OAuth flow to create new credentials.
        """
        creds = None
        credentials_path = "./credentials.json"  # Ensure you have this file

        # Load credentials if they exist
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)

        # Check if credentials are invalid/expired and refresh or reauthenticate as needed
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(GoogleRequest())
                    print("Credentials refreshed successfully.")
                except Exception as e:
                    print("Failed to refresh token:", e)
                    creds = None
            if not creds:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                # Choose between console- or browser-based authentication:
                if "COLAB_GPU" in os.environ:
                    creds = flow.run_console()
                else:
                    creds = flow.run_local_server(port=0)
            # Save the new/updated token to token.json
            with open('token.json', 'w') as token_file:
                token_file.write(creds.to_json())

        return build('gmail', 'v1', credentials=creds)

    def fetch_unanswered_emails(self, max_results=1):
        """
        Fetches all emails included in unanswered threads.

        @param max_results: Maximum number of recent emails to fetch
        @return: List of dictionaries, each representing a thread with its emails
        """
        try:
            recent_emails = self.fetch_recent_emails(max_results) # fetch recent emails up to max_result
            if not recent_emails: return [] # return empty list if no recent emails
            
            # Get all draft replies
            drafts = self.fetch_draft_replies()

            # Create a set of thread IDs that have drafts and extract thread id from each draft and store them
            threads_with_drafts = {draft['threadId'] for draft in drafts}

            # Process new emails
            seen_threads = set() #skip threads that are already seens
            unanswered_emails = []
            for email in recent_emails:
                thread_id = email['threadId']
                if thread_id not in seen_threads and thread_id not in threads_with_drafts: #skip threads that already have a draft reply
                    seen_threads.add(thread_id) # mark them as seen
                    email_info = self._get_email_info(email['id']) # call the function to fetch full email details
                    if self._should_skip_email(email_info): # skip email send by the user
                        continue
                    unanswered_emails.append(email_info) # store unanswered emails
            return unanswered_emails

        except Exception as e:
            print(f"An error occurred: {e}")
            return []

    def _get_email_info(self, msg_id):
        message = self.service.users().messages().get(
            userId="me", id=msg_id, format="full"
        ).execute()

        payload = message.get('payload', {})
        headers = {header["name"].lower(): header["value"] for header in payload.get("headers", [])}

        return {
            "id": msg_id,
            "threadId": message.get("threadId"),
            "messageId": headers.get("message-id"),
            "references": headers.get("references", ""),
            "sender": headers.get("from", "Unknown"),
            "subject": headers.get("subject", "No Subject"),
            "body": self._get_email_body(payload),
        }

    def fetch_recent_emails(self, max_results=1):
        try:
            now = datetime.now()
            delay = now - timedelta(hours=1)

            after_timestamp = int(delay.timestamp())
            before_timestamp = int(now.timestamp())

            query = f"after:{after_timestamp} before:{before_timestamp}"
            results = self.service.users().messages().list(
                userId="me", q=query, maxResults=max_results
            ).execute()
            messages = results.get("messages", [])
            
            return messages

        except Exception as error:
            print(f"An error occurred while fetching emails: {error}")
            return []

    def fetch_draft_replies(self):
        """
        Fetches all draft email replies from Gmail.
        """
        try:
            drafts = self.service.users().drafts().list(userId="me").execute()
            draft_list = drafts.get("drafts", [])
            return [
                {
                    "draft_id": draft["id"],
                    "threadId": draft["message"]["threadId"],
                    "id": draft["message"]["id"],
                }
                for draft in draft_list
            ]

        except Exception as error:
            print(f"An error occurred while fetching drafts: {error}")
            return []

    def _get_email_body(self, payload):
        """
        Extract the email body, prioritizing text/plain over text/html.
        Handles multipart messages, avoids duplicating content, and strips HTML if necessary.
        """
        def decode_data(data):
            """Decode base64-encoded data."""
            return base64.urlsafe_b64decode(data).decode('utf-8').strip() if data else ""

        def extract_body(parts):
            """Recursively extract text content from parts."""
            for part in parts:
                mime_type = part.get('mimeType', '')
                data = part['body'].get('data', '')
                if mime_type == 'text/plain':
                    return decode_data(data)
                if mime_type == 'text/html':
                    html_content = decode_data(data)
                    return self._extract_main_content_from_html(html_content)
                if 'parts' in part:
                    result = extract_body(part['parts'])
                    if result:
                        return result
            return ""

        # Process single or multipart payload
        if 'parts' in payload:
            body = extract_body(payload['parts'])
        else:
            data = payload['body'].get('data', '')
            body = decode_data(data)
            if payload.get('mimeType') == 'text/html':
                body = self._extract_main_content_from_html(body)

        return self._clean_body_text(body)

    def _extract_main_content_from_html(self, html_content):
        """
        Extract main visible content from HTML.
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        for tag in soup(['script', 'style', 'head', 'meta', 'title']):
            tag.decompose()
        return soup.get_text(separator='\n', strip=True)

    def _clean_body_text(self, text):
        """
        Clean up the email body text by removing extra spaces and newlines.
        """
        return re.sub(r'\s+', ' ', text.replace('\r', '').replace('\n', '')).strip()
    
    def _create_html_email_message(self, recipient, subject, reply_text):
        """
        Creates a simple HTML email message with proper formatting and plaintext fallback.
        """
        message = MIMEMultipart("alternative")
        message["to"] = recipient
        message["subject"] = f"Re: {subject}" if not subject.startswith("Re: ") else subject

        # Simplified HTML Template
        html_text = reply_text.replace("\n", "<br>").replace("\\n", "<br>")
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body>{html_text}</body>
        </html>
        """

        html_part = MIMEText(html_content, "html")

        # message.attach(text_part)
        message.attach(html_part)
        return message

    def _should_skip_email(self, email_info):
        return os.environ['MY_EMAIL'] in email_info['sender']

    def create_draft_reply(self, initial_email, reply_text):
        try:
            # Create the reply message
            message = self._create_reply_message(initial_email, reply_text)

            # Create draft with thread information
            draft = self.service.users().drafts().create(
                userId="me", body={"message": message}
            ).execute()

            return draft
        except Exception as error:
            print(f"An error occurred while creating draft: {error}")
            return None


    def _create_reply_message(self, email, reply_text, send=False):
        # Validate email data
        if not email or not reply_text:
            print("Error: Missing email data or reply content.")
            return None

        # Create MIME message
        message = self._create_html_email_message(
            recipient=email.sender,
            subject=email.subject,
            reply_text=reply_text
        )

        if not message:
            print("Warning: Message generation failed.")
            return None

        # Set threading headers
        if email.messageId:
            message["In-Reply-To"] = email.messageId
            message["References"] = f"{email.references} {email.messageId}".strip()

        if send:
            message["Message-ID"] = f"<{uuid.uuid4()}@gmail.com>"

        try:
            # Encode the message properly for Gmail API
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            if not raw_message:
                print("Error: Encoded message is empty.")
                return None

            return {
                "raw": raw_message,
                "threadId": email.threadId
            }
        except Exception as e:
            print(f"Error encoding message: {e}")
            return None



    def send_reply(self, initial_email, reply_text):
        try:
            # Create the reply message
            message = self._create_reply_message(initial_email, reply_text, send=True)

            # Send the message with thread ID
            sent_message = self.service.users().messages().send(
                userId="me", body=message
            ).execute()
            
            return sent_message

        except Exception as error:
            print(f"An error occurred while sending reply: {error}")
            return None
