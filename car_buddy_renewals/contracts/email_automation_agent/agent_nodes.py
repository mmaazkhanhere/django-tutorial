from colorama import Fore, Style
from dotenv import load_dotenv
import os
import logging
from ..helper_functions.clean_email_body import clean_email_body
from ..helper_functions.extract_name_and_email import extract_name_and_email
from django.db import transaction

from ..models import User, EmailTranscript, PCPContract, CLASSIFICATION_CHOICES
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
    
    # Get the last email from the state
    current_email = state["emails"][-1]
    sender_email = current_email.sender
    category = state["email_category"]

    print(f"Email Sender in Category: {sender_email}")

    print(f"Email Category: {category}")

    try:
        user = User.objects.filter(email=sender_email).first()
    except User.DoesNotExist:
        logger.error(Fore.RED + f"User with email {sender_email} not found." + Style.RESET_ALL)
        return state
    
    user_details = state.get("user_details", {})
    user_details['email'] = sender_email

    customer_name = user.first_name if user else user_details.get("name", sender_email)

    transcript = state.get("transcript", [])
    new_message = clean_email_body(current_email.body)

    print(f"Cleaned New Message: {new_message}")

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
    formatted_prompt = email_category_prompt.format(email=new_message)
    
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
    sender_email = current_email.sender
    # user_details['email'] = sender_email

    # print(f"Current Sender: {sender_email}")

    # Ensure existing_user_details is always a dictionary
    existing_user_details = state.get("user_details", {})



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

    logger.info(Fore.CYAN + f"Extracted User Details from LLM: {result}" + Style.RESET_ALL)

    try:
        user = User.objects.filter(email=sender_email).first()
        print(f"User: {user}")
    except User.DoesNotExist:
        logger.error(Fore.RED + f"User with email {sender_email} not found." + Style.RESET_ALL)
        return {"user_details": existing_user_details}  # Preserve existing user details

    if result.name:
        name_parts = result.name.strip().split(" ", 1)  # ✅ Use split here
        user.first_name = name_parts[0]
        user.last_name = name_parts[1] if len(name_parts) > 1 else ""

    user.mobile_number = result.phone if result.phone else user.mobile_number
    user.availability = result.availability if result.availability else user.availability

    if result.car:
        pcp_contract, created = PCPContract.objects.get_or_create(user=user)
        pcp_contract.car = result.car
        pcp_contract.save()

    user.save()

    logger.info(Fore.GREEN + f"User details updated for {user.email}" + Style.RESET_ALL)

    updated_user_details = UserDetails(
        name=f"{user.first_name} {user.last_name}".strip(),
        email=user.email,
        phone=user.mobile_number,
        availability=user.availability,
        car=pcp_contract.car if result.car else existing_user_details.car,
    )
    logger.info(Fore.MAGENTA + f"Final User Details: \n{updated_user_details.dict()}" + Style.RESET_ALL)

    return {"user_details": updated_user_details}



def classifying_user(state: GraphState):
    """Classifies the user and updates only the status."""
    logger.info(Fore.YELLOW + "Classifying user...\n" + Style.RESET_ALL)

    user_details = state["user_details"]
    user_status = state["current_status"]
    user_email = user_details.get("email")

    transcript = state.get("transcript", [])

    if not user_email:
        logger.error(Fore.RED + "User email not found in user_details." + Style.RESET_ALL)
        return state
    
    try:
        user = User.objects.get(email=user_email)
    except User.DoesNotExist:
        logger.error(Fore.RED + f"User with email {user_email} not found." + Style.RESET_ALL)
        return state
    

    user_classification_prompt = PromptTemplate(
        template=USER_CLASSIFICATION_PROMPT,
        input_variables=["emails", "user_details"]
    )
    formatted_prompt = user_classification_prompt.format(emails=transcript, user_details=user_details)
    structure_llm = llm.with_structured_output(UserClassification)
    classification_result = structure_llm.invoke(formatted_prompt)

    normalized_status = classification_result.status.strip().lower()
    logger.info(Fore.MAGENTA + f"User classification: {normalized_status}" + Style.RESET_ALL)

    with transaction.atomic():
        if normalized_status in CLASSIFICATION_CHOICES:
            if user.classification != normalized_status:
                user.classification = normalized_status
                user.save()
                logger.info(Fore.GREEN + f"User classification updated to {normalized_status}" + Style.RESET_ALL)
        else:
            logger.warning(Fore.YELLOW + f"Invalid classification status: {normalized_status}" + Style.RESET_ALL)

    return {
        "user_status": user_status,
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

    writer_messages = state.get('writer_messages', [])
    transcript = state.get('transcript', [])
    category = state["email_category"]
    user_details = state["user_details"]  # This is a `UserDetails` object, not a dict
    user_status = user_details.status.status if user_details.status else "unsure"  # Fix: Use dot notation

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
        f'# **EMAIL CONTENT:**\n{transcript}\n\n'
    )

    formatted_prompt = writer_prompt.format(
        email_information=inputs,
        history=writer_messages
    )

    try:
        structure_llm = llm.with_structured_output(WriterOutput)
        draft_result = structure_llm.invoke(formatted_prompt)
        logger.info(f"Draft Result: {draft_result}")
    except Exception as e:
        logger.error(f"LLM failed to generate draft: {e}")
        return state  # Return the original state if LLM fails


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

    current_email = state["emails"][-1]
    transcript = state.get("transcript", [])
    generated_email = state["generated_email"].strip()
    sender_email = current_email.sender

    try:
        user = User.objects.get(email=sender_email)
    except User.DoesNotExist:
        logger.error(Fore.RED + f"User with email {sender_email} not found." + Style.RESET_ALL)
        return state  # Exit if user not found, though this should not happen

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

    with transaction.atomic():
        # Either fetch the existing transcript or create a new one for the user
        email_transcript, created = EmailTranscript.objects.get_or_create(
            customer_email=sender_email,
            defaults={'transcript': []}
        )

        # Append new message to the existing transcript
        email_transcript.transcript.append(entry)
        email_transcript.save()

        # Link the transcript to the user (if not already linked)
        user.email_transcripts.add(email_transcript)

    gmail_tools.send_reply(state["current_email"], state["generated_email"])
    logger.info(Fore.YELLOW + "Email sent." + Style.RESET_ALL)

    # Reset the writer_messages after the email has been sent
    state["writer_messages"] = []
    return state


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