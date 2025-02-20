import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "car_buddy_renewals.settings")
django.setup()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from contracts.models import EmailTranscript, User


from contracts.email_automation_agent.agent import email_agent


app = FastAPI()

# CORS middleware (if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get('/')
def run_agent():
    """
    Automatically fetch users from the DB and run the agent without passing user_email.
    """
    try:
        # Fetch the user (Example: first user who hasn't been contacted)
        user = User.objects.filter(is_contacted=False).first()

        if not user:
            raise HTTPException(status_code=404, detail="No users found for processing")

        # Build the initial state dynamically
        initial_state = {
            "emails": [],
            "current_email": {
                "id": "",
                "threadId": "",
                "messageId": "",
                "references": "",
                "sender": "",
                "subject": "",
                "body": ""
            },
            "email_category": "",
            "generated_email": "",
            "user_details": {
                "name": f"{user.first_name} {user.last_name}",
                "email": user.email,
                "phone": user.mobile_number,
                "availability": "",
                "car": user.pcp_contract.car if hasattr(user, 'pcp_contract') else "",
            },
            "writer_messages": [],
            "transcript": [],
            "current_status": user.classification,
            "sendable": False,
            "trials": 0,
        }

        # Fetch associated email transcripts
        transcripts = list(user.email_transcripts.values_list('transcript', flat=True))
        initial_state["emails"] = transcripts
        initial_state["current_email"] = transcripts[-1] if transcripts else initial_state["current_email"]
        initial_state["transcript"] = transcripts

        # Run the AI agent with the prepared state
        result = email_agent(initial_state)

        # Optionally, mark user as contacted after processing
        user.is_contacted = True
        user.save()

        return {"status": "success", "data": result}

    except HTTPException as http_err:
        return {"status": "error", "message": http_err.detail}

    except Exception as e:
        return {"status": "error", "message": str(e)}