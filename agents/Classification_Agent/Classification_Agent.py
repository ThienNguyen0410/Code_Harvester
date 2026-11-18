
from dotenv import load_dotenv
from crewai import LLM
import os
import json

load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")

if not groq_api_key:
    raise ValueError("GROQ_API_KEY is not configured in the .env file.")


llm = LLM(
    model="openai/openai/gpt-oss-20b",
    api_key=groq_api_key,
    base_url="https://api.groq.com/openai/v1",
    temperature=0.3,
)

CLASSIFICATION_STRATEGY = {
    "PRESERVED": (
        """There exist a requirment in augmented requirment which has the same meaning with the requirment in original requriment."""
    ),

    "CONTRADICTION": (
        """There exist a requirment in augmented requirment whose meaning is contradicted with the meaning of the requriment in original requirment."""
    ),

    "ELIMINATED" : (
        """The requirment which appear in original prompt but it disappeared in augmented prompt. That requirment is eliminated."""
    ),

    "ADDITION": ("""    
    The requirment which does not appear in original requirement but it appear in augmented requirment. If it is not contradicted with any requirment in original requirment so that requirment is addition.
    """)
}


CLASSIFICATION_SCHEMA = {
    "PRESERVED_LIST" : [
        {
            "id": "",
            "content": ""
        }
    ],

    "List_Of_Contradicted_Pairs" :[
        [
            {
                "id": "",
                "content": ""
            },

            {
                "id": "",
                "content": ""
            }
        ]
    ],

    "ELIMINATED_LIST" : [
        {
           "id": "",
            "content": "" 
        }
    ],

    "ADDITION_LIST": [
        {
            "id": "",
            "content": ""
        }
    ]
    
}

class Classification_Agent:
    def __init__(self, requirment_dict: dict, augmented_requirment: dict):
        self.requirment_dict = requirment_dict
        self.augmented_requirment = augmented_requirment

    def classification(self) -> dict:
        system_prompt = f"""
        You are a Classification Agent.

        Your task is to classify PRESERVED/CONTRADICTION/ELIMINATED/ADDITION for each sub requirments in Sub_requirements_list of
        ORINAL REQUIREMENT:
        {self.requirment_dict}

        AND
        AUGMENTED_REQUIREMENT:
        {self.augmented_requirment}

        CLASSIFICATION_STRATEGY:
        {CLASSIFICATION_STRATEGY}

        OUTPUT_SCHEMA:
        {CLASSIFICATION_SCHEMA}

        CLASSIFICATION RULES:
        1. List all requirments in original requirment which is preserved in augmented requirment.
        2. List all pairs contradiction in List_Of_Contradicted_Pairs.
        3. List all requirment which satisfy ELIMINATED strategy in ELIMINATED_LIST.
        4. List all requirment which satisfy ADDIDTION in ADDITION_LIST.
        5. Return ONLY a valid JSON object.
        6. Do onot include Markdown code blocks or explanations.
        """
        response_text = llm.call(system_prompt)
        response_text = str(response_text).strip()

        try:
            result = json.loads(response_text)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Invalid JSON returned by LLM: {error}\n"
                f"Response:\n{response_text}"
            )
        return result

    def output(self) -> dict:
        return self.classification()

if __name__ == "__main__":

    original_requirement_decomposed = {
    "Original_requirement": (
        "The system shall allow registered users to log in "
        "using their email address and password. "
        "The system shall validate the provided credentials "
        "and display an error message if the email or password "
        "is incorrect. "
        "The system shall lock the account after five "
        "consecutive failed login attempts."
    ),
    "Sub_requirements_list": [
        {
            "id": "SR-001",
            "content": (
                "The system shall allow registered users "
                "to log in using their email address and password."
            ),
            "Ra5_passed": "Yes",
            "isAtomic": "Yes"
        },
        {
            "id": "SR-002",
            "content": (
                "The system shall validate the provided "
                "login credentials."
            ),
            "Ra5_passed": "Yes",
            "isAtomic": "Yes"
        },
        {
            "id": "SR-003",
            "content": (
                "The system shall display an error message "
                "if the email address is incorrect."
            ),
            "Ra5_passed": "Yes",
            "isAtomic": "Yes"
        },
        {
            "id": "SR-004",
            "content": (
                "The system shall display an error message "
                "if the password is incorrect."
            ),
            "Ra5_passed": "Yes",
            "isAtomic": "Yes"
        },
        {
            "id": "SR-005",
            "content": (
                "The system shall lock the account after "
                "five consecutive failed login attempts."
            ),
            "Ra5_passed": "Yes",
            "isAtomic": "Yes"
        }
    ]
}

    
    augmented_requirement_decomposed = {
    "Original_requirement": (
        "The system shall allow registered users to log in "
        "using their email address and password. "
        "The system shall validate the provided credentials "
        "and display an error message if the email or password "
        "is incorrect. "
        "The system shall lock the account after five "
        "consecutive failed login attempts."
    ),
    "Sub_requirements_list": [
        {
            "id": "AR-001",
            "content": (
                "The system shall allow registered users "
                "to log in using their registered email address "
                "and password."
            ),
            "Ra5_passed": "Yes",
            "isAtomic": "Yes"
        },
        {
            "id": "AR-002",
            "content": (
                "The system shall validate the provided "
                "login credentials."
            ),
            "Ra5_passed": "Yes",
            "isAtomic": "Yes"
        },
        {
            "id": "AR-003",
            "content": (
                "The system shall display an error message "
                "if the email address is incorrect."
            ),
            "Ra5_passed": "Yes",
            "isAtomic": "Yes"
        },
        {
            "id": "AR-004",
            "content": (
                "The system shall send an email notification "
                "to the user after a successful login."
            ),
            "Ra5_passed": "Yes",
            "isAtomic": "Yes"
        },
        {
            "id": "AR-005",
            "content": (
                "The system shall unlock the account after "
                "five consecutive failed login attempts."
            ),
            "Ra5_passed": "Yes",
            "isAtomic": "Yes"
        }
    ]
}

        
    original_requirement_decomposed2 = {
        "Original_requirement": (
            "The system shall allow customers to place orders "
            "by selecting products and specifying quantities. "
            "The system shall calculate the total order price "
            "including applicable taxes. "
            "The system shall send an order confirmation email "
            "to the customer after successful order placement. "
            "The system shall allow customers to cancel orders "
            "before they are shipped."
        ),
        "Sub_requirements_list": [
            {
                "id": "SR-001",
                "content": (
                    "The system shall allow customers to place "
                    "orders by selecting products."
                ),
                "Ra5_passed": "Yes",
                "isAtomic": "Yes"
            },
            {
                "id": "SR-002",
                "content": (
                    "The system shall allow customers to specify "
                    "the quantity of each selected product."
                ),
                "Ra5_passed": "Yes",
                "isAtomic": "Yes"
            },
            {
                "id": "SR-003",
                "content": (
                    "The system shall calculate the total order "
                    "price including applicable taxes."
                ),
                "Ra5_passed": "Yes",
                "isAtomic": "Yes"
            },
            {
                "id": "SR-004",
                "content": (
                    "The system shall send an order confirmation "
                    "email to the customer after successful "
                    "order placement."
                ),
                "Ra5_passed": "Yes",
                "isAtomic": "Yes"
            },
            {
                "id": "SR-005",
                "content": (
                    "The system shall allow customers to cancel "
                    "orders before they are shipped."
                ),
                "Ra5_passed": "Yes",
                "isAtomic": "Yes"
            }
        ]
    }



    augmented_requirement_decomposed2 = {
        "Original_requirement": (
            "The system shall allow customers to place orders "
            "by selecting products and specifying quantities. "
            "The system shall calculate the total order price "
            "including applicable taxes. "
            "The system shall send an order confirmation email "
            "to the customer after successful order placement. "
            "The system shall allow customers to cancel orders "
            "before they are shipped."
        ),
        "Sub_requirements_list": [
            {
                "id": "AR-001",
                "content": (
                    "Customers shall be able to create an order "
                    "by choosing one or more products."
                ),
                "Ra5_passed": "Yes",
                "isAtomic": "Yes"
            },
            {
                "id": "AR-002",
                "content": (
                    "The system shall calculate the total order "
                    "price including applicable taxes."
                ),
                "Ra5_passed": "Yes",
                "isAtomic": "Yes"
            },
            {
                "id": "AR-003",
                "content": (
                    "The system shall send an order confirmation "
                    "email to the customer after successful "
                    "order placement."
                ),
                "Ra5_passed": "Yes",
                "isAtomic": "Yes"
            },
            {
                "id": "AR-004",
                "content": (
                    "The system shall allow customers to cancel "
                    "orders even after they have been shipped."
                ),
                "Ra5_passed": "Yes",
                "isAtomic": "Yes"
            },
            {
                "id": "AR-005",
                "content": (
                    "The system shall allow customers to track "
                    "their orders in real time."
                ),
                "Ra5_passed": "Yes",
                "isAtomic": "Yes"
            }
        ]
    }



    result = Classification_Agent(original_requirement_decomposed2, augmented_requirement_decomposed2).output()

    print(
        json.dumps(
            result,
            indent=4,
            ensure_ascii=False
            )
        )
