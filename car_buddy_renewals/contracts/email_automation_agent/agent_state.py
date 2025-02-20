from pydantic import BaseModel, Field
from typing import List, Annotated, Optional
from typing_extensions import TypedDict, Dict
from enum import Enum

from langgraph.graph.message import add_messages

class Email(BaseModel):
    id: str = Field(..., description="Unique identifier of the email")
    threadId: str = Field(..., description="Thread identifier of the email")
    messageId: str = Field(..., description="Message identifier of the email")
    references: str = Field(..., description="References of the email")
    sender: str = Field(..., description="Email address of the sender")
    subject: str = Field(..., description="Subject line of the email")
    body: str = Field(..., description="Body content of the email")
    
class EmailCategory(str, Enum):
    car_enquiry = "car_enquiry"
    test_drive_booking = "test_drive_booking"
    service_booking = "service_booking"
    general_enquiry = "general_enquiry"
    spam = "spam"

class CategorizeEmailOutput(BaseModel):
    category: EmailCategory = Field(
        ..., 
        description="The category assigned to the email, indicating its type based on predefined rules."
    )

class UserStatus(str, Enum):
    approved = "approved"
    refused = "refused"
    unsure = "unsure"

class UserClassification(BaseModel):
    status: str = Field(..., description="Status of the user (e.g., unsure, confirmed)")
    reason: str = Field(..., description="Reason for the status")

class UserDetails(BaseModel):
    name: str = Field(..., description="Name of the customer")  # Remove default ""
    email: str = Field(..., description="Email address of the customer")
    phone: str = Field(..., description="Phone number of the customer")  
    availability: str = Field(..., description="Availability for booking")
    car: str = Field(..., description="Vehicle details")





class WriterOutput(BaseModel):
    email: str = Field(
        ..., 
        description="The draft email written in response to the customer's inquiry, adhering to company tone and standards."
    )

class ProofReaderOutput(BaseModel):
    feedback: str = Field(
        ..., 
        description="Detailed feedback explaining why the email is or is not sendable."
    )
    send: bool = Field(
        ..., 
        description="Indicates whether the email is ready to be sent (true) or requires rewriting (false)."
    )


class GraphState(TypedDict):
    emails: List[Email]  # Queue of emails to process
    current_email: Email  # Email currently being processed
    email_category: EmailCategory  # Category of the current email
    generated_email: str  # AI-generated response draft
    user_details: UserDetails  # Extracted user details
    writer_messages: List[str]  # Logs of proofreading and rewrites
    transcript: List[Dict[str, str]]  # Structured transcript: {"timestamp": ..., "sender": ..., "message": ...}
    current_status: UserStatus  # Updated status after classification
    sendable: bool  # Is the draft sendable?
    trials: int  # Number of email rewrite attempts
