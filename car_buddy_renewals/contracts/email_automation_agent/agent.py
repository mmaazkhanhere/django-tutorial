from langgraph.graph import START, END, StateGraph

from PIL import Image

from agent_nodes import (
    load_new_emails,
    check_new_emails,
    is_email_inbox_empty,
    categorize_email,
    route_email_based_on_category,
    load_full_email_thread,
    extract_user_information,
    classifying_user,
    write_email,
    write_draft_email,
    verify_generated_email,
    must_rewrite,
    send_email_response,
    skip_spam_email,
    sendgrid_email
)

from agent_states import GraphState





def email_agent():
    workflow = StateGraph(GraphState)

    workflow.add_node("load_inbox_emails", load_new_emails)
    workflow.add_node("is_email_inbox_empty", is_email_inbox_empty)
    workflow.add_node("categorize_email", categorize_email)

    workflow.add_node("load_full_email_thread", load_full_email_thread)
    workflow.add_node("extract_user_information", extract_user_information)
    workflow.add_node("classifying_user", classifying_user)

    workflow.add_node("email_writer", write_draft_email)
    workflow.add_node("email_proofreader", verify_generated_email)
    workflow.add_node("send_email_response", send_email_response)  # New node for sending emails
    workflow.add_node("skip_spam_email", skip_spam_email)

    workflow.add_node("sendgrid_email", sendgrid_email)

    



    # Load inbox emails
    workflow.add_edge(START, "load_inbox_emails")

    # Check if there are emails to process
    workflow.add_edge("load_inbox_emails", "is_email_inbox_empty")
    workflow.add_conditional_edges(
        "is_email_inbox_empty",
        check_new_emails,
        {
            "process": "categorize_email",
            "empty": END
        }
    )

    # Route email based on category
    workflow.add_conditional_edges(
        "categorize_email",
        route_email_based_on_category,
        {
            "car enquiry": "load_full_email_thread",
            "general enquiry": "load_full_email_thread",
            "service booking": "load_full_email_thread",
            "test drive booking": "load_full_email_thread",
            "spam": "skip_spam_email"
        }
    )

    workflow.add_edge("load_full_email_thread", "extract_user_information")

    workflow.add_conditional_edges("extract_user_information",
                                    write_email,
                                    {
                                        "approved": END,
                                        "refused": END,
                                        "unsure": "classifying_user"
                                    }
                                )

    workflow.add_edge("classifying_user", "email_writer")

    workflow.add_edge("email_writer", "email_proofreader")

    # Check if the email is ready to send or needs rewriting
    workflow.add_conditional_edges(
        "email_proofreader",
        must_rewrite,
        {
            "send": "send_email_response",  
            "rewrite": "email_writer",
            "stop": "categorize_email"
        }
    )

    # If the email is sent, check if there are still more emails to process
    # workflow.add_edge("send_email_response", "is_email_inbox_empty")  # ✅ Now added send email response
    workflow.add_conditional_edges(
        "send_email_response",
        write_email,
        {
            "approved": "sendgrid_email",
            "refused": "sendgrid_email",
            "unsure": "is_email_inbox_empty"
        }
    )
    workflow.add_edge("sendgrid_email", END)
    workflow.add_edge("skip_spam_email", "is_email_inbox_empty")

    # Compile
    return workflow.compile()

