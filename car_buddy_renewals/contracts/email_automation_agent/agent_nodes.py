from colorama import Fore, Style
from dotenv import load_dotenv
import os
import logging
from ..helper_functions import clean_email_body

# from sendgrid import SendGridAPIClient
# from sendgrid.helpers.mail import *

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate

from .gmail_tool import GmailToolsClass

from .agent_state import *
from .prompts import *

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("FROM_EMAIL")
TEMPLATE_ID = os.getenv("TEMPLATE_ID")

llm: ChatGroq = ChatGroq(
    model="deepseek-r1-distill-llama-70b",
    api_key= os.getenv("GROQ_API_KEY"),
    temperature=0.5
)

gmail_tools = GmailToolsClass()

def load_new_emails(state: GraphState)->GraphState:
    """Loads new emails from Gmail and updates the state."""
    logger.info(Fore.YELLOW + "Loading new emails...\n" + Style.RESET_ALL)
    try:
        recent_emails = gmail_tools.fetch_unanswered_emails()
        emails = [Email(**email) for email in recent_emails]
    except Exception as e:
        logger.error(f"Failed to load new emails: {e}")
        emails=[]
    return {"emails": emails}


def check_new_emails(state: GraphState) -> str:
    """Checks if there are new emails to process."""
    if len(state['emails']) == 0:
        logger.info(Fore.RED + "No new emails" + Style.RESET_ALL)
        return "empty"
    else:
        logger.info(Fore.GREEN + "New emails to process" + Style.RESET_ALL)
        return "process"

def is_email_inbox_empty(state: GraphState) -> GraphState:
        return state


def categorize_email(state: GraphState) -> GraphState:
    """Categorizes the current email using the categorize_email agent."""
    logger.info(Fore.YELLOW + "Checking email category...\n" + Style.RESET_ALL)
    
    # Get the last email
    current_email = state["emails"][-1]
    user_details = state.get("user_details", {})
    user_details['email'] = current_email.sender

    customer_name = user_details.get("name", "")


    transcript = state.get("transcript", [])
    new_message =  clean_email_body(current_email.body)


    entry = {
        'sender': customer_name,
        'message': new_message,
    }

    transcript.append(entry)

    logger.info(Fore.MAGENTA + "Transcript updated with new customer message.\n" + Style.RESET_ALL)

    email_category_prompt = PromptTemplate(
        template=CATEGORIZE_EMAIL_PROMPT,
        input_variables=["email"]
    )
    formatted_prompt = email_category_prompt.format(email=current_email.body)
    
    structure_llm = llm.with_structured_output(CategorizeEmailOutput)
    result = structure_llm.invoke(formatted_prompt)
    
    logger.info(Fore.MAGENTA + f"Email category: {result.category.value}" + Style.RESET_ALL)
    
    return {
        "email_category": result.category.value,
        "current_email": current_email,
        "transcript": transcript,
        "user_details": user_details
    }



def route_email_based_on_category(state: GraphState) -> str:
    """Routes the email based on its category."""
    print(Fore.YELLOW + "Routing email based on category...\n" + Style.RESET_ALL)

    category = state["email_category"]
    if category == "car_enquiry":
        return "car enquiry"
    elif category == "general_enquiry":
        return "general enquiry"
    elif category == "service_booking":
        return "service booking"
    elif category == "test_drive_booking":
        return "test drive booking"
    else:
        return "spam"
    


def extract_user_information(state: GraphState):
    """Extract user information from the email"""
    logger.info(Fore.YELLOW + "Extracting user details...\n" + Style.RESET_ALL)

    # Ensure emails exist before accessing the last one
    if not state["emails"]:
        logger.error("No emails found in state.")
        return {"user_details": state.get("user_details", {})}  # Preserve existing user details

    current_email = state["emails"][-1]  # Get the latest email

    # Ensure existing_user_details is always a dictionary
    existing_user_details = state.get("user_details", {})

    # Convert existing_user_details to a UserDetails model if it isn't already
    try:
        if isinstance(existing_user_details, dict):
            existing_user_details = UserDetails(**existing_user_details)
    except Exception as e:
        logger.error(f"Failed to parse existing_user_details: {e}")
        existing_user_details = UserDetails(name="", email="", phone="", availability="", car="", status=None)

    # Prepare the prompt for LLM extraction
    user_extraction_prompt = PromptTemplate(
        template=USER_EXTRACTION_PROMPT,
        input_variables=["email"]
    )
    formatted_prompt = user_extraction_prompt.format(email=current_email.body)

    # Invoke LLM to extract user information
    try:
        structure_llm = llm.with_structured_output(UserDetails, method="function_calling")
        result = structure_llm.invoke(formatted_prompt)
    except Exception as e:
        logger.error(f"LLM extraction failed: {e}")
        result = UserDetails(name="", email="", phone="", availability="", car="", status=None)

    logger.info(Fore.CYAN + f"Extracted User Details from LLM: {result.dict()}" + Style.RESET_ALL)

    # Ensure phone number has a fallback if missing
    result.phone = result.phone if result.phone else ""

    updated_user_details = UserDetails(
        name=result.name if result.name else existing_user_details.name,
        email=result.email if result.email else existing_user_details.email,
        phone=result.phone if result.phone else existing_user_details.phone,
        availability=result.availability if result.availability else existing_user_details.availability,
        car=result.car if result.car else existing_user_details.car,
    )

    logger.info(Fore.MAGENTA + f"Final User Details: \n{updated_user_details.dict()}" + Style.RESET_ALL)

    return {"user_details": updated_user_details}




def classifying_user(state: GraphState):
    """Classifies the user and updates only the status."""
    logger.info(Fore.YELLOW + "Classifying user...\n" + Style.RESET_ALL)

    previous_emails = state["previous_emails"]
    emails_send = state["emails_send"]
    user_details = state["user_details"]
    user_status = state["current_status"]

    user_classification_prompt = PromptTemplate(
        template=USER_CLASSIFICATION_PROMPT,
        input_variables=["emails", "user_details"]
    )
    formatted_prompt = user_classification_prompt.format(emails=previous_emails, user_details=user_details)
    structure_llm = llm.with_structured_output(UserClassification)
    classification_result = structure_llm.invoke(formatted_prompt)

    # Normalize the status value (strip whitespace and convert to lower case)
    normalized_status = classification_result.status.strip().lower()

    print(f"User classification: {normalized_status}")

    # Convert user_details dictionary to a Pydantic model
    user_status = normalized_status

    logger.info(Fore.MAGENTA + f"Updated user classification: {normalized_status}" + Style.RESET_ALL)

    # Increment emails_send only when the status is "unsure"
    if normalized_status == "unsure":
        emails_send += 1
        logger.info(Fore.YELLOW + f"Updating emails send: {emails_send}" + Style.RESET_ALL)

    return {
        "user_status": user_status,
        "emails_send": emails_send
    }



def write_email(state: GraphState)->str:
    user_status = state["current_status"]

    if user_status == "approved":
        return "approved"
    
    elif user_status == "refused":
        return "refused"
    
    elif user_status == "unsure":
        return "unsure"


def write_draft_email(state: GraphState) -> GraphState:
    """Writes a draft email based on the current email and retrieved information."""
    logger.info(Fore.YELLOW + "Writing draft email...\n" + Style.RESET_ALL)

    previous_emails = state["previous_emails"]
    category = state["email_category"]
    user_details = state["user_details"]  # This is a `UserDetails` object, not a dict
    user_status = user_details.status.status if user_details.status else "unsure"  # Fix: Use dot notation

    writer_messages = state.get('writer_messages', [])
    writer_prompt = None

    # Custom email responses for Approved and Refused cases
    if user_status == "approved":
        writer_prompt = ChatPromptTemplate.from_messages([
            ("system", APPROVED_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            ("user", "{email_information}")
        ])
    elif user_status == "refused":
        writer_prompt = ChatPromptTemplate.from_messages([
            ("system", REFUSED_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            ("user", "{email_information}")
        ])
    else:
        # Standard category-based email responses
        category_prompts = {
            "car_enquiry": CAR_ENQUIRY_PROMPT,
            "service_booking": SERVICE_BOOKING_PROMPT,
            "test_drive_booking": TEST_DRIVE_BOOKING_PROMPT,
            "general_enquiry": GENERAL_ENQUIRY_PROMPT
        }
        if category in category_prompts:
            writer_prompt = ChatPromptTemplate.from_messages([
                ("system", category_prompts[category]),
                MessagesPlaceholder(variable_name="history"),
                ("user", "{email_information}")
            ])

    # If writer_prompt is not found, return the original state
    if not writer_prompt:
        logger.warning("No writer prompt found for the given category/status.")
        return state

    # Format input to the writer agent
    inputs = (
        f'# **EMAIL CATEGORY:** {state["email_category"]}\n\n'
        f'# **USER DETAILS:** {user_details}\n\n'
        f'# **EMAIL CONTENT:**\n{previous_emails}\n\n'
    )

    formatted_prompt = writer_prompt.format(
        email_information=inputs,
        history=writer_messages
    )

    structure_llm = llm.with_structured_output(WriterOutput)

    # Write email
    draft_result = structure_llm.invoke(formatted_prompt)
    logger.info(f"Draft Result: {draft_result}")  # Debugging

    email = draft_result.email
    trials = state.get('trials', 0) + 1

    # Append writer's draft to the message list
    writer_messages.append(f"**Draft {trials}:**\n{email}")

    return {
        "generated_email": email,
        "trials": trials,
        "writer_messages": writer_messages
    }



def verify_generated_email(state: GraphState) -> GraphState:
    """Verifies the generated email using the proofreader agent."""
    logger.info(Fore.YELLOW + "Verifying generated email...\n" + Style.RESET_ALL)

    prompt = PromptTemplate(
        template=EMAIL_PROOFREADER_PROMPT, 
        input_variables=["initial_email", "generated_email"]
    )

    # Correctly format the prompt before invoking the model
    formatted_prompt = prompt.format(
        initial_email=state["current_email"].body,
        generated_email=state["generated_email"]
    )

    structure_llm = llm.with_structured_output(ProofReaderOutput)

    # Invoke with a properly formatted string
    review = structure_llm.invoke(formatted_prompt)

    logger.info(f"Proofreading Result: {review}")  # Debugging Output

    writer_messages = state.get('writer_messages', [])
    writer_messages.append(f"**Proofreader Feedback:**\n{review.feedback}")

    return {
        "sendable": review.send,
        "writer_messages": writer_messages
    }


def must_rewrite(state: GraphState) -> str:
    """Determines if the email needs to be rewritten based on review and trial count."""
    email_sendable = state["sendable"]
    
    if email_sendable:
        logger.info(Fore.GREEN + "Email is good, ready to be sent!!!" + Style.RESET_ALL)
        state["emails"].pop()
        state["writer_messages"] = []  # ✅ Reset writer_messages after sending
        return "send"  # ✅ Returning only a string
    
    elif state["trials"] >= 3:
        logger.info(Fore.RED + "Email is not good, we reached max trials must stop!!!" + Style.RESET_ALL)
        state["emails"].pop()
        state["writer_messages"] = []  # ✅ Reset writer_messages after max trials
        return "stop"  # ✅ Returning only a string

    else:
        logger.info(Fore.RED + "Email is not good, must rewrite it..." + Style.RESET_ALL)
        return "rewrite"  # ✅ Correct




def create_draft_response(state: GraphState) -> GraphState:
    """Creates a draft response in Gmail."""
    logger.info(Fore.YELLOW + "Creating draft email...\n" + Style.RESET_ALL)
    gmail_tools.create_draft_reply(state["current_email"], state["generated_email"])
    
    return {"retrieved_documents": "", "trials": 0}

def send_email_response(state: GraphState) -> GraphState:
    """Sends the email response directly using Gmail."""
    logger.info(Fore.YELLOW + "Sending email...\n" + Style.RESET_ALL)

    transcript = state.get("transcript", [])
    generated_email = state["generated_email"].strip()

    if not generated_email:
        logger.warning("Generated email is empty, skipping sending.")
        return state

    cleaned_email = clean_email_body(generated_email)

    entry = {
        'sender': 'Car Buddy',
        'message': cleaned_email,
    }

    transcript.append(entry)
    
    logger.info(Fore.MAGENTA + f"Updated Transcript: {transcript}" + Style.RESET_ALL)

    gmail_tools.send_reply(state["current_email"], state["generated_email"])
    logger.info(Fore.YELLOW + "Email sent." + Style.RESET_ALL)

    # Reset the writer_messages after the email has been sent
    state["writer_messages"] = []
    return {
        "retrieved_documents": "",
        "trials": 0,
        "transcript": transcript,
        "writer_messages": []
    }


def skip_spam_email(state):
    """Skip spam emails and remove from emails list."""
    logger.info("Skipping spam emails...\n")
    state["emails"].pop()
    return state

# def sendgrid_email(state):

#     user_details: UserDetails = state["user_details"]
#     transcript = state["transcript"]

#     data = {
#         "CustomerName": user_details.name,
#         "CustomerEmailAddress": user_details.email,
#         "PhoneNumber": user_details.phone,
#         "Transcript": transcript
#     }

#     message = Mail(from_email=FROM_EMAIL)
#     message.template_id = TEMPLATE_ID
#     recipient_emails = ["mmaazkhanhere@gmail.com"]

#     for email in recipient_emails:
#         personalization = Personalization()
#         personalization.add_to(To(email))
#         personalization.dynamic_template_data = data  # Ensure each recipient gets the dynamic data
#         message.add_personalization(personalization)

#     sg = SendGridAPIClient(api_key=SENDGRID_API_KEY)

#     # Send the email
#     response = sg.send(message)

#     # Print the response status
#     print(f"Email sent to {recipient_emails}. Status Code: {response.status_code}")