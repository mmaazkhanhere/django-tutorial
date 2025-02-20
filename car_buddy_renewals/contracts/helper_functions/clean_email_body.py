import re

def clean_email_body(email_body: str) -> str:
    """Clean the email body by removing metadata, symbols, and extra spaces."""
    email_body = re.sub(r"(?i)(From:.*|Sent:.*|To:.*|Subject:.*)", "", email_body).strip()
    email_body = re.sub(r"\n+", " ", email_body)  # Convert newlines to single spaces
    email_body = re.sub(r"\s{2,}", " ", email_body)  # Remove excessive spaces
    email_body = re.sub(r"[•✔️✅🚗🎉\ud83d\ude97\ud83d\ude0a\ud83d\udcc5\ud83d\udcde]", "", email_body)  # Remove emojis & symbols
    return email_body.replace("\n", " ").strip()