
import sys
import json
import os
import csv
import re
from pathlib import Path
from dotenv import load_dotenv
from crewai import LLM

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.RD_Agent import RD_Agent


load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")

if not groq_api_key:
    raise ValueError("GROQ_API_KEY is not configured in the .env file.")

openai_api_key = os.getenv("OPENAI_API_KEY") 
openai_model = os.getenv("GPT_MODEL")
openai_baseurl = os.getenv("OPENAI_API_BASE")
"""
This module is used to evaluate the completeness of the user prompt.
"""


# ============================================================
# 1. ACTION TYPE SPECIFICATION
# ============================================================

ACTION_TYPE_SPECIFICATION = {
    "INTERACTION": {
        "description": "Interact with UI elements or system interfaces.",
        "required_fields": [
            "operation",
            "element"
        ],
        "conditional_required_fields": {
            "SELECT": ["value"],
            "KEY_PRESS": ["value"]
        }
    },

    "DATA_RETRIEVAL": {
        "description": "Retrieve or extract information from a data source.",
        "required_fields": [
            "source",
            "retrieval_method"
        ]
    },

    "DATA_INPUT": {
        "description": "Provide or enter data into a system.",
        "required_fields": [
            "input_method",
            "destination",
            "value"
        ]
    },

    "DATA_PROCESSING": {
        "description": "Transform, calculate, or manipulate data.",
        "required_fields": [
            "operation",
            "operands",
            "output_name"
        ]
    },

    "VALIDATION": {
        "description": "Verify whether data satisfies a specified rule.",
        "required_fields": [
            "subject",
            "validation_rule"
        ]
    },

    "DECISION": {
        "description": "Determine the next execution path based on a condition.",
        "required_fields": [
            "condition",
            "branches"
        ]
    },

    "DATA_STORAGE": {
        "description": "Create, update, delete, or save data.",
        "required_fields": [
            "operation",
            "destination",
            "data"
        ]
    },

    "COMMUNICATION": {
        "description": "Send information to another entity.",
        "required_fields": [
            "channel",
            "recipient",
            "content"
        ]
    },

    "WAIT": {
        "description": "Wait for a duration, event, or condition.",
        "required_fields": [
            "wait_type"
        ],
        "conditional_required_fields": {
            "DURATION": ["duration"],
            "EVENT": ["condition"],
            "CONDITION": ["condition"]
        }
    },

    "EXCEPTION_HANDLING": {
        "description": "Handle errors or exceptional situations.",
        "required_fields": [
            "exception_type",
            "trigger_condition",
            "handling_strategy"
        ],
        "conditional_required_fields": {
            "RETRY": ["retry_config"],
            "FALLBACK": ["fallback_action_id"]
        }
    }
}


# ============================================================
# 2. ACTION MAPPING SCHEMA
# ============================================================

ACTION_MAPPING_SCHEMA = {
    "mappings": [
        {
            "sub_requirement_id": "",
            "actions": [
                {
                    "action_id": "",
                    "action_type": "",
                    "description": "",
                    "config": {},
                    "required_fields_status": {
                        "isComplete": None,
                        "missing_fields": [],
                        "unspecified_fields": []
                    }
                }
            ]
        }
    ]
}

ACTION_TYPE_EXAMPLE = """

EXAMPLES FOR EACH ACTION TYPE
==============================

1. INTERACTION
---------------
Requirement: "Click the 'Submit' button on the login form."
→ action_type: INTERACTION
config:
  operation: "CLICK"
  element: "Submit button on the login form"
  value: null

required_fields_status:
  isComplete: true
  missing_fields: []
  unspecified_fields: []


Requirement: "Select 'Vietnam' from the Country dropdown."
→ action_type: INTERACTION
config:
  operation: "SELECT"
  element: "Country dropdown"
  value: "Vietnam"

required_fields_status:
  isComplete: true


2. DATA_RETRIEVAL
-----------------
Requirement: "Get the current stock quantity of product ID 8821 from the inventory system."
→ action_type: DATA_RETRIEVAL
config:
  source: "inventory system"
  retrieval_method: "query by product ID 8821"

required_fields_status:
  isComplete: true


Requirement: "Retrieve employee information."
→ action_type: DATA_RETRIEVAL
config:
  source: null
  retrieval_method: null

required_fields_status:
  isComplete: false
  unspecified_fields: ["source", "retrieval_method"]


3. DATA_INPUT
-------------
Requirement: "Enter the customer name 'Nguyen Van A' into the Name field."
→ action_type: DATA_INPUT
config:
  input_method: "type"
  destination: "Name field"
  value: "Nguyen Van A"

required_fields_status:
  isComplete: true


4. DATA_PROCESSING
------------------
Requirement: "Calculate the total amount by multiplying quantity by unit price."
→ action_type: DATA_PROCESSING
config:
  operation: "multiply"
  operands: ["quantity", "unit price"]
  output_name: "total_amount"

required_fields_status:
  isComplete: true


Requirement: "Process the employee data."
→ action_type: DATA_PROCESSING
config:
  operation: null
  operands: null
  output_name: null

required_fields_status:
  isComplete: false
  unspecified_fields: ["operation", "operands", "output_name"]


5. VALIDATION
-------------
Requirement: "Check whether the email address is in valid format."
→ action_type: VALIDATION
config:
  subject: "email address"
  validation_rule: "must be in valid email format"

required_fields_status:
  isComplete: true


6. DECISION
-----------
Requirement: "If the order amount is greater than 10,000,000 VND then require manager approval, otherwise proceed automatically."
→ action_type: DECISION
config:
  condition: "order amount > 10,000,000 VND"
  branches: {
    "true": "require manager approval",
    "false": "proceed automatically"
  }

required_fields_status:
  isComplete: true


7. DATA_STORAGE
---------------
Requirement: "Save the processed employee data into the database at c:/Thien/main.db."
→ action_type: DATA_STORAGE
config:
  operation: "INSERT"          # or "UPDATE" / "SAVE"
  destination: "c:/Thien/main.db"
  data: "processed employee data"

required_fields_status:
  isComplete: true


Requirement: "Store the processed information of employee's data in the c:/Thien/main.db."
→ action_type: DATA_STORAGE
config:
  operation: null
  destination: "c:/Thien/main.db"
  data: null                   # "processed employee data" is too vague

required_fields_status:
  isComplete: false
  unspecified_fields: ["operation", "data"]


8. COMMUNICATION
-----------------
Requirement: "Send an email to the manager notifying that the report is ready."
→ action_type: COMMUNICATION
config:
  channel: "email"
  recipient: "manager"
  content: "the report is ready"

required_fields_status:
  isComplete: true


Requirement: "Send an email to the manager."
→ action_type: COMMUNICATION
config:
  channel: "email"
  recipient: "manager"
  content: null

required_fields_status:
  isComplete: false
  unspecified_fields: ["content"]


9. WAIT
-------
Requirement: "Wait for 30 seconds before continuing."
→ action_type: WAIT
config:
  wait_type: "DURATION"
  duration: "30 seconds"

required_fields_status:
  isComplete: true


Requirement: "Wait until the file is fully downloaded."
→ action_type: WAIT
config:
  wait_type: "CONDITION"
  condition: "file is fully downloaded"

required_fields_status:
  isComplete: true


10. EXCEPTION_HANDLING
----------------------
Requirement: "If the connection to the database fails, retry 3 times with 5-second intervals."
→ action_type: EXCEPTION_HANDLING
config:
  exception_type: "database connection failure"
  trigger_condition: "connection to the database fails"
  handling_strategy: "RETRY"
  retry_config: {
    "max_retries": 3,
    "interval": "5 seconds"
  }

required_fields_status:
  isComplete: true


BAD EXAMPLE (What you must NOT do):
Original: "Store the processed information of employee's data in the c:/Thien/main.db."
Wrong description: "Store processed employee data into the specified database"
→ This is incorrect because it paraphrases and loses original wording.

GOOD EXAMPLE:
Original: "Store the processed information of employee's data in the c:/Thien/main.db."
Correct description: "Store the processed information of employee's data in the c:/Thien/main.db."
config:
  operation: null
  destination: "c:/Thien/main.db"
  data: "the processed information of employee's data"   # hoặc null nếu bạn coi là vẫn chưa đủ cụ thể
"""


# ============================================================
# 3. LLM CONFIGURATION
# ============================================================

# mapping_llm = LLM(
#     model=os.getenv(
#         "LLM_MODEL",
#         "openai/openai/gpt-oss-20b"
#     ),
#     api_key=groq_api_key,
#     base_url=os.getenv(
#         "GROQ_BASE_URL",
#         "https://api.groq.com/openai/v1"
#     )
# )

mapping_llm = LLM(
    model=openai_model,
    api_key= openai_api_key,
    base_url=openai_baseurl
)

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


def parse_json_response(response_text: str) -> dict:
    """Parse JSON returned by the LLM."""

    if not isinstance(response_text, str):
        raise TypeError("LLM returned a non-text response.")

    if not response_text.strip():
        raise ValueError("LLM returned an empty response.")

    response_text = strip_markdown_code_fence(response_text)

    try:
        result = json.loads(response_text)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"LLM returned invalid JSON: {error}\n"
            f"Response:\n{response_text}"
        ) from error

    if not isinstance(result, dict):
        raise TypeError("The response must be a JSON object.")

    return result


# ============================================================
# 5. DECOMPOSITION RESPONSE VALIDATION
# ============================================================

def validate_AI_response(response_text: str) -> dict:
    """Validate and parse the decomposition response."""

    result = parse_json_response(response_text)

    if "Original_requirement" not in result:
        raise ValueError("Missing Original_requirement.")

    if "Sub_requirements_list" not in result:
        raise ValueError("Missing Sub_requirements_list.")

    if not isinstance(result["Sub_requirements_list"], list):
        raise TypeError("Sub_requirements_list must be a list.")

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

        # These fields will be evaluated by the Atomicity Agent.
        sub_requirement["Ra5_passed"] = None
        sub_requirement["isAtomic"] = None

    return result


# ============================================================
# 6. DECOMPOSITION
# ============================================================

def decompose_user_prompt(prompt: str) -> dict:
    return RD_Agent(prompt).decompose()


# ============================================================
# 7. ACTION MAPPING
# ============================================================

def mapping_sub_requirement_to_action(
    decompose_schema: dict
) -> dict:
    """
    Map each sub-requirement to one or more actions.

    The LLM uses ACTION_TYPE_SPECIFICATION to classify actions
    and generate the corresponding configuration fields.
    """

    mapping_prompt = f"""
You are an RPA Action Mapping Agent.

Your task is to map each sub-requirement into one or more
executable actions.

INPUT:
{json.dumps(decompose_schema, indent=4, ensure_ascii=False)}

ACTION TYPE SPECIFICATION:
{json.dumps(ACTION_TYPE_SPECIFICATION, indent=4, ensure_ascii=False)}

OUTPUT SCHEMA:
{json.dumps(ACTION_MAPPING_SCHEMA, indent=4, ensure_ascii=False)}

RULES:

1. Every sub-requirement must be mapped to one or more actions.

2. Use ONLY the predefined action types in
   ACTION_TYPE_SPECIFICATION.

3. Select the most appropriate action_type based on the
   semantic meaning of the sub-requirement.

4. Every action must have:
   - action_id
   - action_type
   - description
   - config
   - required_fields_status

5. The config object must contain all required fields
   specified for its action_type.

6. Conditional required fields must also be included
   when their corresponding condition applies.

7. Do NOT invent information that is not supported by
   the original requirement.

8. If a required field cannot be determined from the
   requirement:
   - Include that field in config with value null.
   - Add its name to unspecified_fields.

9. If a required field is accidentally omitted from
   config, add its name to missing_fields.

10. Set isComplete to false if either missing_fields
    or unspecified_fields is not empty.

11. Set isComplete to true only when every required
    field has a meaningful value supported by the
    requirement.

12. Do not create additional actions that introduce
    unsupported operations, conditions, or side effects.

13. One sub-requirement may map to multiple actions
    when necessary.

14. Multiple sub-requirements may map to the same
    action only when their semantics genuinely describe
    the same operation.

15. Preserve the original meaning of every
    sub-requirement.

16. Return valid JSON only. Do not include Markdown
    or explanations outside the JSON.

17. Do not add or enrich any additional information in the content of each sub requirements.
18. Preserving the meaning and semantic of original requirement.


19. STRICT PRESERVATION OF ORIGINAL CONTENT:
    - When writing the "description" field of an action, you MUST stay as close as possible to the original wording of the sub-requirement.
    - Do NOT paraphrase, rephrase, summarize, or beautify the original sentence.
    - Do NOT replace specific terms with more general terms (e.g. do not change "processed information of employee's data" into "processed employee data").
    - Do NOT replace a concrete path with vague phrases such as "the specified database".

20. DESCRIPTION RULE:
    - The "description" should be a minimal adaptation of the original sub-requirement content, only changing what is necessary for grammatical correctness.
    - Prefer copying key phrases from the original requirement rather than rewriting them.

21. FORBIDDEN BEHAVIORS:
    - Do not invent smoother or more professional-sounding language.
    - Do not omit important details present in the original requirement.
    - Do not add any information that does not appear in the original requirement.

22. CONFIG FIELD RULE:
    - When filling values in "config", use the exact phrases from the original requirement whenever possible.
    - Example: if the requirement says "processed information of employee's data", the "data" field should use that phrase (or null if still too vague), not a shortened version.
IMPORTANT:
A structurally present field does not necessarily mean
that sufficient information is available.

EXAMPLE FOR EACH ACTION TYPE:
{ACTION_TYPE_EXAMPLE}

"""

    response = mapping_llm.call(
        messages=[
            {
                "role": "user",
                "content": mapping_prompt
            }
        ]
    )

    result = parse_json_response(response)

    if "mappings" not in result:
        raise ValueError("Missing mappings in Action Mapping response.")

    if not isinstance(result["mappings"], list):
        raise TypeError("mappings must be a list.")

    # Validate mapping references and action structure.
    expected_ids = {
        item["id"]
        for item in decompose_schema["Sub_requirements_list"]
    }

    mapped_ids = set()

    for mapping_index, mapping in enumerate(result["mappings"]):

        sub_id = mapping.get("sub_requirement_id")

        if sub_id not in expected_ids:
            raise ValueError(
                f"Unknown sub_requirement_id: {sub_id}"
            )

        if sub_id in mapped_ids:
            raise ValueError(
                f"Duplicate mapping for sub-requirement: {sub_id}"
            )

        mapped_ids.add(sub_id)

        if not isinstance(mapping.get("actions"), list):
            raise TypeError(
                f"Actions of mapping {sub_id} must be a list."
            )

        for action in mapping["actions"]:

            if action.get("action_type") not in ACTION_TYPE_SPECIFICATION:
                raise ValueError(
                    f"Invalid action_type: {action.get('action_type')}"
                )

            if not action.get("action_id"):
                raise ValueError("Missing action_id.")

            if not isinstance(action.get("config"), dict):
                raise TypeError("Action config must be an object.")

    # Check whether every sub-requirement was mapped.
    unmapped_ids = expected_ids - mapped_ids

    if unmapped_ids:
        raise ValueError(
            f"Unmapped sub-requirements: {unmapped_ids}"
        )

    return result


# ============================================================
# 8. COMPLETENESS EVALUATION
# ============================================================

def is_empty_value(value) -> bool:
    """Check whether a field has no meaningful value."""

    return (
        value is None
        or value == ""
        or value == []
        or value == {}
    )


def evaluation_completeness(action_schema: dict) -> str:
    """
    Evaluate whether all actions contain sufficient
    information based on their required fields.

    This function does NOT use an LLM.
    """

    has_missing_information = False

    for mapping in action_schema.get("mappings", []):

        for action in mapping.get("actions", []):

            action_type = action.get("action_type")

            if action_type not in ACTION_TYPE_SPECIFICATION:
                raise ValueError(
                    f"Unknown action type: {action_type}"
                )

            specification = ACTION_TYPE_SPECIFICATION[action_type]

            config = action.get("config", {})

            if not isinstance(config, dict):
                raise TypeError(
                    f"Config of {action.get('action_id')} must be an object."
                )

            missing_fields = []
            unspecified_fields = []

            # Step 1: Check normal required fields.
            required_fields = specification.get(
                "required_fields", []
            )

            for field in required_fields:

                if field not in config:
                    missing_fields.append(field)

                elif is_empty_value(config[field]):
                    unspecified_fields.append(field)

            # Step 2: Check conditional required fields.
            conditional_fields = specification.get(
                "conditional_required_fields", {}
            )

            # Determine which field controls the condition.
            discriminator = None

            if action_type == "INTERACTION":
                discriminator = "operation"

            elif action_type == "WAIT":
                discriminator = "wait_type"

            elif action_type == "EXCEPTION_HANDLING":
                discriminator = "handling_strategy"

            if discriminator:

                discriminator_value = config.get(discriminator)

                if discriminator_value in conditional_fields:

                    additional_fields = conditional_fields[
                        discriminator_value
                    ]

                    for field in additional_fields:

                        if field not in config:
                            missing_fields.append(field)

                        elif is_empty_value(config[field]):
                            unspecified_fields.append(field)

            # Step 3: Update the status.
            is_complete = (
                len(missing_fields) == 0
                and len(unspecified_fields) == 0
            )

            action["required_fields_status"] = {
                "isComplete": is_complete,
                "missing_fields": missing_fields,
                "unspecified_fields": unspecified_fields
            }

            if not is_complete:
                has_missing_information = True

    if has_missing_information:
        return "Lack of information"

    return "Enough information"


# ============================================================
# 9. MAIN
# ============================================================





import csv

def load_prompts(file_path="case.txt"):
    prompts = []

    with open(file_path, "r", encoding="utf-8-sig") as file:

        # Ignore comment lines and blank lines.
        valid_lines = (
            line for line in file
            if line.strip() and not line.lstrip().startswith("#")
        )

        reader = csv.DictReader(
            valid_lines,
            delimiter="\t"
        )

        for row in reader:
            # Remove unnecessary spaces from column names.
            row = {
                key.strip(): value.strip() if value else ""
                for key, value in row.items()
                if key is not None
            }

            prompts.append(row)

    return prompts



def main():

    dataset = load_prompts()

    # Mode "w": clear previous results at the beginning of each run.
    with open("test.txt", "a", encoding="utf-8") as output_file:

        for index, item in enumerate(dataset, start=1):

            prompt_id = item["ID"]
            label = item["LABEL"]
            user_prompt = item["PROMPT"]

            print("=" * 70, file=output_file)
            print(f"DATASET ITEM: {index}/100", file=output_file)
            print(f"PROMPT ID: {prompt_id}", file=output_file)
            print(f"EXPECTED LABEL: {label}", file=output_file)

            print("\nORIGINAL USER PROMPT", file=output_file)
            print("=" * 70, file=output_file)
            print(user_prompt, file=output_file)

            # Step 1: Decompose requirement.
            print("\n[STEP 1] Requirement Decomposition", file=output_file)

            decompose_schema = decompose_user_prompt(user_prompt)

            print(
                json.dumps(
                    decompose_schema,
                    indent=4,
                    ensure_ascii=False
                ),
                file=output_file
            )

            # Step 2: Map sub-requirements to actions.
            print("\n[STEP 2] Action Mapping", file=output_file)

            action_schema = mapping_sub_requirement_to_action(
                decompose_schema
            )

            print(
                json.dumps(
                    action_schema,
                    indent=4,
                    ensure_ascii=False
                ),
                file=output_file
            )

            # Step 3: Evaluate completeness.
            print("\n[STEP 3] Completeness Evaluation", file=output_file)

            completeness_result = evaluation_completeness(
                action_schema
            )

            print("Result:", completeness_result, file=output_file)

            # Print details of incomplete actions.
            print("\n[INCOMPLETE ACTIONS]", file=output_file)

            for mapping in action_schema["mappings"]:

                for action in mapping["actions"]:

                    status = action["required_fields_status"]

                    if not status["isComplete"]:

                        print(
                            {
                                "action_id": action["action_id"],
                                "action_type": action["action_type"],
                                "missing_fields": status["missing_fields"],
                                "unspecified_fields": status["unspecified_fields"]
                            },
                            file=output_file
                        )

            print("\n[FINAL ACTION MAPPING SCHEMA]", file=output_file)

            print(
                json.dumps(
                    action_schema,
                    indent=4,
                    ensure_ascii=False
                ),
                file=output_file
            )

            # Separate results between prompts.
            print("\n" + "#" * 80 + "\n", file=output_file)

            # Save results immediately after each prompt.
            output_file.flush()

            print(f"Processed {index}/{len(dataset)}: {prompt_id}")

    print("\nAll results have been saved to output.txt")


if __name__ == "__main__":
    main()
