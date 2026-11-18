
"""RD Agent (Requirement Decomposition Agent).
This agent decomposes a natural-language requirement
into smaller sub-requirements.
"""

import json
import os
import re

from dotenv import load_dotenv
from crewai import LLM

#from RD_Agent.RD_Agent import RD_Agent

load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")

if not groq_api_key:
    raise ValueError("GROQ_API_KEY is not configured in the .env file.")


# llm = LLM(
#     model="openai/openai/gpt-oss-20b",
#     api_key=groq_api_key,
#     base_url="https://api.groq.com/openai/v1",
#     temperature=0.3,
# )

openai_api_key = os.getenv("OPENAI_API_KEY") 
openai_model = os.getenv("GPT_MODEL")
openai_baseurl = os.getenv("OPENAI_API_BASE")
llm = LLM(
    model=openai_model,
    api_key= openai_api_key,
    base_url=openai_baseurl
)



DECOMPOSE_SCHEMA = {
    "Original_requirement": "",
    "Sub_requirements_list": [
        {
            "id": "",
            "content": "",
            "isAtomic": None
        }
    ]
}




EVALUATION_RULES = """
Evaluate each sub-requirement independently.

For each sub-requirement, apply the following criterion:

"Would further breakup of this requirement into separate
parts be extremely difficult or detract from understandability?"

Evaluation procedure:

1. Identify whether the requirement contains multiple
   independently testable conditions, behaviors, or outcomes.

2. Consider whether splitting these parts would produce
   meaningful, independently verifiable requirements.

3. Do not split a requirement merely because it contains
   multiple nouns, parameters, or verbs.

4. Do not split a requirement if doing so would:
   - Lose its original meaning.
   - Create meaningless or overly trivial requirements.
   - Make the requirement less understandable.
   - Introduce information not present in the original requirement.

5. Set the fields as follows:
   - If further decomposition is extremely difficult
     or would detract from understandability:
       isAtomic = "Yes"

   - Otherwise:
       isAtomic = "No"

6. Preserve all original information.
   Only modify isAtomic.
"""



ATOMIC_REQUIREMENT_CONTEXT = """
DEFINITION OF ATOMIC REQUIREMENT:

An atomic requirement is a requirement that expresses
a single coherent behavior, capability, condition,
or constraint that can be independently understood
and verified.

A requirement does not need to contain only one verb
or one object to be considered atomic.

DECOMPOSITION CRITERIA:

A requirement should be considered NON-ATOMIC when:

1. It contains multiple independent behaviors that
   can be specified and verified separately.

2. It contains multiple independent conditions
   that lead to distinct system behaviors.

3. It combines multiple requirements that can exist
   independently without changing their original meaning.

4. Splitting the requirement produces meaningful,
   independently verifiable sub-requirements.

A requirement should be considered ATOMIC when:

1. It expresses one coherent system responsibility.

2. Its components are strongly related and must work
   together to fulfill the same system behavior.

3. Further decomposition would produce trivial,
   incomplete, or meaningless requirements.

4. Splitting it would lose the original intent or
   reduce its understandability.

IMPORTANT DISTINCTIONS:

- Multiple input parameters do not automatically
  indicate a non-atomic requirement.

- Multiple verbs do not automatically indicate
  a non-atomic requirement.

- The presence of AND or OR does not automatically
  indicate a non-atomic requirement.

- A vague or underspecified requirement is not
  necessarily non-atomic. Lack of detail and lack
  of atomicity are different problems.

- Evaluate semantic independence, not sentence length.

"""



ATOMIC_EXAMPLES = """
EXAMPLE 1 - ATOMIC:

Requirement:
"The system shall allow registered users to log in
using their email address and password."

Evaluation:
isAtomic = "Yes"

Reason:
Email and password are two input parameters of
one coherent login operation. Separating them would
not produce meaningful independent system behaviors.


EXAMPLE 2 - NON-ATOMIC:

Requirement:
"The system shall validate the user's email address
and display an error message if the email is invalid."

Evaluation:
isAtomic = "No"

Reason:
The requirement combines two independently
verifiable behaviors:
- Validate the email address.
- Display an error message when invalid.

These behaviors can be specified separately.


EXAMPLE 3 - NON-ATOMIC:

Requirement:
"The system shall display an error message if
the email or password is incorrect."

Evaluation:
isAtomic = "No"

Reason:
The requirement combines two distinct error
conditions that can be independently verified:
- Incorrect email.
- Incorrect password.


EXAMPLE 4 - ATOMIC:

Requirement:
"The system shall calculate the total price of
an order based on its items and quantities."

Evaluation:
isAtomic = "Yes"

Reason:
Items and quantities are related inputs used
to perform one coherent calculation.
Splitting them would detract from understandability.
"""


def strip_markdown_code_fence(response_text: str) -> str:
    """Remove Markdown code fences from the LLM response."""

    match = re.search(
        r"```(?:json)?\s*(.*?)\s*```",
        response_text,
        re.DOTALL | re.IGNORECASE,
    )

    if match:
        return match.group(1)

    return response_text.strip()


def validate_AI_response(response_text: str) -> dict:
    """Validate and parse the LLM response."""

    if not isinstance(response_text, str):
        raise TypeError("LLM returned a non-text response.")

    if not response_text.strip():
        raise ValueError("LLM returned an empty response.")

    response_text = strip_markdown_code_fence(response_text)

    # Parse JSON
    try:
        result = json.loads(response_text)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"LLM returned invalid JSON: {error}\n"
            f"Response:\n{response_text}"
        )

    # Validate required fields
    if not isinstance(result, dict):
        raise TypeError("The response must be a JSON object.")

    if "Original_requirement" not in result:
        raise ValueError("Missing Original_requirement.")

    if "Sub_requirements_list" not in result:
        raise ValueError("Missing Sub_requirements_list.")

    if not isinstance(result["Sub_requirements_list"], list):
        raise TypeError("Sub_requirements_list must be a list.")

    # Validate each sub-requirement
    for index, sub_requirement in enumerate(
        result["Sub_requirements_list"]
    ):
        if not isinstance(sub_requirement, dict):
            raise TypeError(
                f"Sub-requirement at index {index} must be an object."
            )

        if not sub_requirement.get("id"):
            raise ValueError(
                f"Missing id in sub-requirement at index {index}."
            )

        if not sub_requirement.get("content"):
            raise ValueError(
                f"Missing content in sub-requirement at index {index}."
            )

    return result

class Evaluation_Agent:
    def __init__(self, RD_ouput: dict):
        self.RD_output = RD_ouput

    def evaluate(self) -> dict:

        system_prompt = f"""
        You are a Software Requirement Evaluation Agent.

        Your task is to evaluate the atomicity of each
        sub-requirement using the RA5 criterion.

        INPUT:
        {json.dumps(self.RD_output, indent=4, ensure_ascii=False)}

        {ATOMIC_REQUIREMENT_CONTEXT}

        {ATOMIC_EXAMPLES}

        EVALUATION PROCEDURE:

        For each sub-requirement:

        1. Understand its intended system behavior.
        2. Identify its conditions, actions, and outcomes.
        3. Determine whether these represent independent
        behaviors or one coherent responsibility.
        4. Apply the RA5 criterion.
        5. Assign the evaluation values.

        OUTPUT RULES:

        - Only modify isAtomic.
        - Preserve all IDs and requirement contents.
        - Do not add or remove sub-requirements.
        - Do not modify Original_requirement.
        - Return ONLY a valid JSON object.
        - Use "Yes" or "No", never null.
        """

        response_text = llm.call(system_prompt)

        return validate_AI_response(response_text)


    def output(self) -> dict:
        return self.evaluate()



if __name__ == "__main__":
    schema = """
{
    "Original_requirement": "The system shall allow registered users to log in using their email address and password. The system shall validate the provided credentials and display an error message if the email or password is incorrect.",
    "Sub_requirements_list": [
        {
            "id": "SR-001",
            "content": "The system shall allow registered users to log in using their email address and password.",
            "isAtomic": null
        },
        {
            "id": "SR-002",
            "content": "The system shall validate the provided credentials.",
            "isAtomic": null
        },
        {
            "id": "SR-003",
            "content": "The system shall display an error message if the email address is incorrect.",
            "isAtomic": null
        },
        {
            "id": "SR-004",
            "content": "The system shall display an error message if the password is incorrect.",
            "isAtomic": null
        }
    ]
}
"""

    schema1 = """

{
    "Original_requirement": "The system shall allow administrators to create user accounts, update user information, and delete user accounts.",
    "Sub_requirements_list": [
        {
            "id": "SR-001",
            "content": "The system shall allow administrators to create user accounts, update user information, and delete user accounts.",
            "isAtomic": null
        }
    ]
}

"""

    schema2 = """

{
    "Original_requirement": "The system shall calculate the shipping fee based on the package weight and delivery destination.",
    "Sub_requirements_list": [
        {
            "id": "SR-001",
            "content": "The system shall calculate the shipping fee based on the package weight and delivery destination.",
            "isAtomic": null
        }
    ]
}

"""

    schema3 = """

{
    "Original_requirement": "The system shall authenticate a user by retrieving the stored account information, comparing the provided password with the stored password hash, and granting access if the credentials are valid.",
    "Sub_requirements_list": [
        {
            "id": "SR-001",
            "content": "The system shall authenticate a user by retrieving the stored account information, comparing the provided password with the stored password hash, and granting access if the credentials are valid.",
            "isAtomic": null
        }
    ]
}

    """
    schema4 = """

{
    "Original_requirement": "When an order is confirmed, the system shall update the inventory quantity and send an order confirmation email to the customer.",
    "Sub_requirements_list": [
        {
            "id": "SR-001",
            "content": "When an order is confirmed, the system shall update the inventory quantity and send an order confirmation email to the customer.",
            "isAtomic": null
        }
    ]
}

"""

    schema5 = """

{
    "Original_requirement": "The system shall apply free shipping to an order when the order's total value is at least $100 and the customer is a premium member.",
    "Sub_requirements_list": [
        {
            "id": "SR-001",
            "content": "The system shall apply free shipping to an order when the order's total value is at least $100 and the customer is a premium member.",
            "isAtomic": null
        }
    ]
}


    """


decomposed_schema = """
{
    "Original_requirement": "Open the shopping website, search for \"Laptop\", and retrieve the product name and price of the first search result. If the price is less than $1,000, add the product to the shopping cart.",
    "Sub_requirements_list": [
        {
            "id": "SR-001",
            "content": "Open the shopping website.",
            "isAtomic": null
        },
        {
            "id": "SR-002",
            "content": "Search for \"Laptop\".",
            "isAtomic": null
        },
        {
            "id": "SR-003",
            "content": "Retrieve the product name and price of the first search result.",
            "isAtomic": null
        },
        {
            "id": "SR-004",
            "content": "If the price is less than $1,000, add the product to the shopping cart.",
            "isAtomic": null
        }
    ]
}

"""
schema_list = [
    {
        "Original_requirement": "The system shall calculate the total price of an order based on the selected products and their quantities, and apply a discount when the customer is eligible for a promotional offer.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall calculate the total price of an order based on the selected products and their quantities, and apply a discount when the customer is eligible for a promotional offer.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall allow customers to update their account information, and send an email notification whenever their registered email address is changed.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall allow customers to update their account information, and send an email notification whenever their registered email address is changed.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall authenticate users using their email address and password, and lock the account after five consecutive failed login attempts.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall authenticate users using their email address and password, and lock the account after five consecutive failed login attempts.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall generate a monthly sales report containing total revenue for each region, and email the report to the regional sales managers.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall generate a monthly sales report containing total revenue for each region, and email the report to the regional sales managers.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall allow administrators to create new employee accounts, and assign default permissions based on each employee's department.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall allow administrators to create new employee accounts, and assign default permissions based on each employee's department.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall retrieve all unpaid invoices, calculate the outstanding balance for each customer, and generate a separate overdue payment report.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall retrieve all unpaid invoices, calculate the outstanding balance for each customer, and generate a separate overdue payment report.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall allow users to search for products by name or category, and display the average customer rating for each matching product.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall allow users to search for products by name or category, and display the average customer rating for each matching product.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall record employee attendance based on check-in and check-out events, and calculate the total working hours for each employee at the end of the day.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall record employee attendance based on check-in and check-out events, and calculate the total working hours for each employee at the end of the day.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall allow customers to submit product reviews with ratings and comments, and notify the product manager whenever a review receives a rating of one star.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall allow customers to submit product reviews with ratings and comments, and notify the product manager whenever a review receives a rating of one star.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall monitor product inventory levels and automatically generate purchase orders when stock falls below the minimum threshold, and send low-stock notifications to inventory managers.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall monitor product inventory levels and automatically generate purchase orders when stock falls below the minimum threshold, and send low-stock notifications to inventory managers.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall allow project managers to create tasks with assigned deadlines, and notify assigned team members when a task's deadline is approaching.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall allow project managers to create tasks with assigned deadlines, and notify assigned team members when a task's deadline is approaching.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall validate customer registration information before creating a new account, and send a verification email containing an activation link to the registered email address.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall validate customer registration information before creating a new account, and send a verification email containing an activation link to the registered email address.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall retrieve transaction records within a specified date range, calculate the total transaction amount for each account, and export the results as a CSV file.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall retrieve transaction records within a specified date range, calculate the total transaction amount for each account, and export the results as a CSV file.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall allow administrators to deactivate employee accounts, and revoke all active sessions belonging to the deactivated employees.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall allow administrators to deactivate employee accounts, and revoke all active sessions belonging to the deactivated employees.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall retrieve customer support tickets based on their priority levels, calculate the number of unresolved tickets in each priority group, and display the results in a dashboard.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall retrieve customer support tickets based on their priority levels, calculate the number of unresolved tickets in each priority group, and display the results in a dashboard.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall allow suppliers to update their product prices, and record the previous and updated prices in the product price history.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall allow suppliers to update their product prices, and record the previous and updated prices in the product price history.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall identify orders that have not been shipped within three business days, update their delivery status to delayed, and notify the logistics manager.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall identify orders that have not been shipped within three business days, update their delivery status to delayed, and notify the logistics manager.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall allow users to upload documents to their profiles, and maintain an audit log containing the document name, upload timestamp, and uploading user's identity.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall allow users to upload documents to their profiles, and maintain an audit log containing the document name, upload timestamp, and uploading user's identity.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall calculate the total revenue generated by each department, compare it with the assigned revenue target, and generate a performance evaluation for each department.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall calculate the total revenue generated by each department, compare it with the assigned revenue target, and generate a performance evaluation for each department.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall allow customers to cancel eligible orders, and automatically initiate a refund for payments associated with successfully cancelled orders.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall allow customers to cancel eligible orders, and automatically initiate a refund for payments associated with successfully cancelled orders.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall retrieve all employees whose contracts are approaching their expiration dates, update their contract status to pending renewal, and generate a notification for the HR department.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall retrieve all employees whose contracts are approaching their expiration dates, update their contract status to pending renewal, and generate a notification for the HR department.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall allow administrators to define role-based access permissions, and maintain a history of all permission changes made to each role.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall allow administrators to define role-based access permissions, and maintain a history of all permission changes made to each role.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall retrieve all incoming customer inquiries, classify them according to their topics, and assign each inquiry to the appropriate support department.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall retrieve all incoming customer inquiries, classify them according to their topics, and assign each inquiry to the appropriate support department.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall calculate the monthly salary of each employee based on their attendance records, and generate individual salary statements that employees can download.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall calculate the monthly salary of each employee based on their attendance records, and generate individual salary statements that employees can download.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall allow customers to save products to their wishlists, and notify them when the price of a saved product decreases by at least 10 percent.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall allow customers to save products to their wishlists, and notify them when the price of a saved product decreases by at least 10 percent.",
                "isAtomic": None
            }
        ]
    }
]



atomic_list = [
    {
        "Original_requirement": "The system shall display the customer's current account balance.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall display the customer's current account balance.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall calculate the total price of an order based on the selected products and their quantities.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall calculate the total price of an order based on the selected products and their quantities.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall lock a user account after five consecutive failed login attempts.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall lock a user account after five consecutive failed login attempts.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall allow customers to update their registered phone number.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall allow customers to update their registered phone number.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall display all available products belonging to the selected category.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall display all available products belonging to the selected category.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall calculate the average rating of a product based on its submitted customer reviews.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall calculate the average rating of a product based on its submitted customer reviews.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall reject a registration request when the provided email address is already registered.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall reject a registration request when the provided email address is already registered.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall generate a unique identification number for each newly created employee account.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall generate a unique identification number for each newly created employee account.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall calculate the remaining stock quantity of a product after a completed purchase.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall calculate the remaining stock quantity of a product after a completed purchase.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall record the timestamp of each employee check-in event.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall record the timestamp of each employee check-in event.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall calculate the total working hours of an employee based on a valid check-in and check-out pair.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall calculate the total working hours of an employee based on a valid check-in and check-out pair.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall assign a unique ticket identifier to every newly submitted customer support ticket.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall assign a unique ticket identifier to every newly submitted customer support ticket.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall classify an invoice as overdue when its payment due date has passed and its payment status remains unpaid.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall classify an invoice as overdue when its payment due date has passed and its payment status remains unpaid.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall prevent users without administrator privileges from accessing the system configuration page.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall prevent users without administrator privileges from accessing the system configuration page.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall export the currently displayed transaction records into a CSV file.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall export the currently displayed transaction records into a CSV file.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall display the shipping address associated with the selected customer order.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall display the shipping address associated with the selected customer order.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall calculate the discount amount corresponding to a specified discount percentage and order subtotal.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall calculate the discount amount corresponding to a specified discount percentage and order subtotal.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall send a password reset link to the email address associated with the user's account.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall send a password reset link to the email address associated with the user's account.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall retrieve the profile information associated with a specified employee ID.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall retrieve the profile information associated with a specified employee ID.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall reject an uploaded document whose file size exceeds 10 MB.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall reject an uploaded document whose file size exceeds 10 MB.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall calculate the total revenue generated by a specified sales region during a given reporting period.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall calculate the total revenue generated by a specified sales region during a given reporting period.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall generate a QR code containing a unique token for the authenticated employee.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall generate a QR code containing a unique token for the authenticated employee.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall verify whether a submitted QR token matches an active token stored in the system.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall verify whether a submitted QR token matches an active token stored in the system.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall calculate the number of unresolved support tickets assigned to a specified support agent.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall calculate the number of unresolved support tickets assigned to a specified support agent.",
                "isAtomic": None
            }
        ]
    },
    {
        "Original_requirement": "The system shall maintain the chronological order of messages within a customer support conversation.",
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": "The system shall maintain the chronological order of messages within a customer support conversation.",
                "isAtomic": None
            }
        ]
    }
]

def main():

    # passed_count = 0
    # failed_count = 0

    # for index, schema in enumerate(schema_list, start=1):

    #     print(f"\nProcessing schema {index}/{len(atomic_list)}")

    #     agent = Evaluation_Agent(schema)
    #     result = agent.evaluate()

    #     #print(json.dumps(result, indent=4, ensure_ascii=False))

    #     # Access dictionary directly
    #     is_atomic = result["Sub_requirements_list"][0]["isAtomic"]

    #     passed = is_atomic == "No"

    #     if passed:
    #         print("Passed")
    #         passed_count += 1
    #     else:
    #         print("Failed")
    #         failed_count += 1

    # print("\n========== SUMMARY ==========")
    # print(f"Total: {len(schema_list)}")
    # print(f"Passed: {passed_count}")
    # print(f"Failed: {failed_count}")

    # accuracy = passed_count / len(schema_list) * 100

    # print(f"Accuracy: {accuracy:.2f}%")
    # agents = Evaluation_Agent(decomposed_schema)
    # result = agents.evaluate()

    # print(json.dumps(result, indent=4, ensure_ascii=False))
    pass


main()

