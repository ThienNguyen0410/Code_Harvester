
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
            "target.entity",
            "target.disambiguator"
        ],
        "conditional_discriminator": "operation",
        "conditional_required_fields": {
            "SELECT": ["value.kind", "value.content"],
            "KEY_PRESS": ["value.kind", "value.content"],
            "TYPE": ["value.kind", "value.content"],
            "COPY": ["value.kind", "value.content"],
            "UPLOAD": ["value.kind", "value.content"],
            "UPDATE": ["value.kind", "value.content"]
        },
        "insufficient_values": {
            "target.disambiguator": [
                "button",
                "the button",
                "field",
                "the field",
                "element",
                "appropriate stock status",
                "confirmation button"
            ],
            "value.content": [
                "document",
                "the document",
                "order status",
                "status",
                "the new status",
                "the value",
                "value"
            ]
        },
        "semantic_requirements": [
            "target.entity identifies the UI element; target.disambiguator must provide enough context or a locator to identify it uniquely.",
            "Do not treat generic labels such as 'button', 'field', or 'appropriate status' as a uniquely identified target.",
            "For value.kind use LITERAL or REFERENCE. value.content must contain the literal value or the explicitly named source."
        ]
    },

    "DATA_RETRIEVAL": {
        "description": "Retrieve or extract information from a data source.",
        "required_fields": [
            "source.system",
            "source.object",
            "query.method",
            "query.fields"
        ],
        "conditional_discriminator": "query.method",
        "conditional_required_fields": {
            "LATEST": [
                "query.ordering.field",
                "query.ordering.direction",
                "query.limit"
            ]
        },
        "insufficient_values": {
            "query.fields": [
                "information",
                "customer information",
                "employee information",
                "relevant field",
                "data",
                "required information"
            ]
        },
        "semantic_requirements": [
            "Identify the data source and the object or dataset being queried.",
            "query.fields must name the requested attributes, not a vague phrase such as 'information' or 'data'.",
            "Use query.method='LATEST' for a request for the latest records; then specify ordering field, direction, and limit.",
            "Include filters, ordering, and limits when needed to identify the requested records, such as a product ID or what 'latest' means."
        ]
    },

    "DATA_INPUT": {
        "description": "Provide or enter data into a system.",
        "required_fields": [
            "input_method",
            "destination.entity",
            "destination.field",
            "value.kind",
            "value.content"
        ],
        "insufficient_values": {
            "destination.field": ["destination field", "field"],
            "value.content": ["the value", "value"]
        },
        "semantic_requirements": [
            "destination must identify the target entity and field; include destination.context when needed to disambiguate the field.",
            "For value.kind use LITERAL or REFERENCE. value.content must be the specified value or an explicitly named source, not a placeholder such as 'the value'."
        ]
    },

    "DATA_PROCESSING": {
        "description": "Transform, calculate, or manipulate data.",
        "required_fields": [
            "operation",
            "operands.*.source",
            "output.name"
        ],
        "conditional_required_fields": {
            "AVERAGE": ["parameters.aggregation_scope"],
            "SUM": ["parameters.aggregation_scope"],
            "COUNT": ["parameters.aggregation_scope"],
            "CONVERT": ["parameters.target_format"]
        },
        "conditional_discriminator": "operation",
        "semantic_requirements": [
            "Each operand must identify the data or variable used. For collection operations, aggregation_scope must identify the dataset or record set.",
            "Parameters that define the operation, such as target format, units, or rounding, must be explicit when required to determine the result.",
            "output.name must be a specific result name or destination; vague phrases such as 'appropriate format' are not output names."
        ]
    },

    "VALIDATION": {
        "description": "Verify whether data satisfies a specified rule.",
        "required_fields": [
            "subject.entity",
            "predicate.operator",
            "predicate.expected"
        ],
        "insufficient_values": {
            "subject.entity": ["required field"],
            "predicate.expected": [
                "is valid",
                "must be valid",
                "correct",
                "must be correct",
                "too large",
                "must not be too large",
                "check before processing it"
            ]
        },
        "conditional_discriminator": "predicate.operator",
        "conditional_required_fields": {
            "MATCHES_FORMAT": ["predicate.format"],
            "GREATER_THAN": ["predicate.unit"],
            "LESS_THAN": ["predicate.unit"],
            "GREATER_THAN_OR_EQUAL": ["predicate.unit"],
            "LESS_THAN_OR_EQUAL": ["predicate.unit"]
        },
        "semantic_requirements": [
            "subject must identify the data being checked.",
            "predicate must state a testable rule. Provide a threshold and unit, allowed value, or format when the rule depends on one.",
            "Terms such as 'valid', 'correct', or 'too large' are insufficient unless the requirement or an established context defines their criteria."
        ]
    },

    "DECISION": {
        "description": "Determine the next execution path based on a condition.",
        "required_fields": [
            "condition.subject",
            "condition.operator",
            "condition.expected",
            "branches.true",
            "branches.false"
        ],
        "insufficient_values": {
            "condition.operator": ["eligible"]
        },
        "semantic_requirements": [
            "The condition must be testable; an eligibility or success condition needs its criteria when those criteria are not defined by context.",
            "Specify both true and false outcomes when both paths affect execution. Do not invent a default such as 'no action'; mark an unstated required branch as null."
        ]
    },

    "DATA_STORAGE": {
        "description": "Create, update, delete, or save data.",
        "required_fields": [
            "operation",
            "destination.system",
            "destination.object",
            "data.source"
        ],
        "insufficient_values": {
            "destination.object": ["log file", "file", "database"]
        },
        "semantic_requirements": [
            "destination must identify the storage system and target object, such as a table, file, or record; include a path or key when necessary to identify it.",
            "data.source must identify exactly what is being stored. Do not replace the original data description with a broad summary.",
            "For UPDATE or DELETE, identify the affected record or selection criteria."
        ]
    },

    "COMMUNICATION": {
        "description": "Send information to another entity.",
        "required_fields": [
            "channel",
            "recipient.identity",
            "content.body"
        ],
        "semantic_requirements": [
            "recipient.identity must identify a person, address, group, or unambiguous role in the current context.",
            "content.body must identify the message or information to send; include content.purpose when the body alone does not make the intent clear."
        ]
    },

    "WAIT": {
        "description": "Wait for a duration, event, or condition.",
        "required_fields": [
            "wait_type"
        ],
        "conditional_required_fields": {
            "DURATION": ["duration.value", "duration.unit"],
            "EVENT": ["condition.target", "condition.signal"],
            "CONDITION": ["condition.target", "condition.state"]
        },
        "conditional_discriminator": "wait_type",
        "insufficient_values": {
            "condition.target": [
                "the page",
                "operation",
                "the operation",
                "expected result",
                "required file"
            ],
            "condition.state": [
                "ready",
                "the page is ready",
                "the operation is completed",
                "expected result to appear",
                "the required file is available"
            ]
        },
        "semantic_requirements": [
            "A condition wait must identify an observable target and state; words such as 'ready' or 'expected result' need a concrete definition.",
            "An event wait must identify the target and event signal. A duration must provide a numeric value and unit.",
            "Provide a timeout when the requirement specifies one; do not invent one."
        ]
    },

    "EXCEPTION_HANDLING": {
        "description": "Handle errors or exceptional situations.",
        "required_fields": [
            "exception.type",
            "trigger.target",
            "trigger.condition",
            "handling_strategy"
        ],
        "conditional_required_fields": {
            "RETRY": ["retry_config.max_retries", "retry_config.interval.value", "retry_config.interval.unit"],
            "FALLBACK": ["fallback.action"]
        },
        "conditional_discriminator": "handling_strategy",
        "insufficient_values": {
            "trigger.condition": [
                "an error occurs",
                "error occurs",
                "an error"
            ]
        },
        "semantic_requirements": [
            "Identify the exception and the observable condition that triggers handling.",
            "For RETRY, provide an explicit retry count and interval when specified by the requirement.",
            "For FALLBACK, describe the specified fallback action; do not create an action that the requirement does not state."
        ]
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

The snippets illustrate config fields. "isComplete" is shorthand for
required_fields_status.isComplete; generated JSON must use the full
required_fields_status object. Null or insufficient values belong in
unspecified_fields.

1. INTERACTION
---------------
Requirement: "Click the 'Submit' button on the login form."
config:
  operation: "CLICK"
  target:
    entity: "button"
    disambiguator: "label 'Submit' on the login form"
  value: null
isComplete: true

Insufficient: "Click the button."
  target.entity: "button"
  target.disambiguator: null


2. DATA_RETRIEVAL
-----------------
Requirement: "Get the current stock quantity of product ID 8821 from the inventory system."
→ action_type: DATA_RETRIEVAL
config:
  source:
    system: "inventory system"
    object: "product"
  query:
    method: "retrieve current record"
    fields: ["stock quantity"]
    filters:
      - field: "product ID"
        operator: "equals"
        value: "8821"
isComplete: true

Insufficient: "Retrieve customer information from the system."
  source:
    system: "the system"
    object: "customer"
  query:
    method: "retrieve"
  query.fields: null


3. DATA_INPUT
-------------
Requirement: "Enter 'Nguyen Van A' into the Name field on the customer form."
→ action_type: DATA_INPUT
config:
  input_method: "type"
  destination:
    entity: "customer form"
    field: "Name"
    context: "customer form"
  value:
    kind: "LITERAL"
    content: "Nguyen Van A"
isComplete: true

Insufficient: "Copy the value into the destination field."
  value:
    kind: "REFERENCE"
    content: null


4. DATA_PROCESSING
------------------
Requirement: "Calculate the total amount for the current order by multiplying quantity by unit price."
→ action_type: DATA_PROCESSING
config:
  operation: "MULTIPLY"
  operands:
    - source: "quantity"
      scope: "current order"
    - source: "unit price"
      scope: "current order"
  output:
    name: "total amount"
  parameters: {}
isComplete: true

Insufficient: "Calculate the average score."
  operation: "AVERAGE"
  operands:
    - source: "score"
      scope: "the score"
  output:
    name: "average score"
  parameters:
    aggregation_scope: null


5. VALIDATION
-------------
Requirement: "Check whether the email address is in valid format."
→ action_type: VALIDATION
config:
  subject:
    entity: "email address"
  predicate:
    operator: "matches_format"
    expected: "valid email address format"
    format: "email address"
isComplete: true

Insufficient: "Reject files that are too large."
  subject.entity: "files"
  predicate:
    operator: "greater_than"
    expected: null
    unit: null


6. DECISION
-----------
Requirement: "If the order amount is greater than 10,000,000 VND then require manager approval, otherwise proceed automatically."
→ action_type: DECISION
config:
  condition:
    subject: "order amount"
    operator: "greater_than"
    expected: 10000000
    unit: "VND"
  branches:
    true: "require manager approval"
    false: "proceed automatically"
isComplete: true

Insufficient: "If the order is eligible, apply the discount."
  condition:
    subject: "order"
    operator: "eligible"
    expected: null
  branches:
    true: "apply the discount"
    false: null


7. DATA_STORAGE
---------------
Requirement: "Insert the employee record into the employees table in c:/Thien/main.db."
→ action_type: DATA_STORAGE
config:
  operation: "INSERT"
  destination:
    system: "database at c:/Thien/main.db"
    object: "employees table"
  data:
    source: "employee record"
isComplete: true

Insufficient: "Append the execution result to the log file."
  destination:
    system: null
    object: "log file"


8. COMMUNICATION
-----------------
Requirement: "Email the report-ready notification to alex@example.com."
config:
  channel: "email"
  recipient:
    identity: "alex@example.com"
  content:
    body: "the report is ready"
isComplete: true

Insufficient: "Send an email to the manager."
  content.body: null


9. WAIT
-------
Requirement: "Wait for 30 seconds before continuing."
→ action_type: WAIT
config:
  wait_type: "DURATION"
  duration:
    value: 30
    unit: "seconds"
isComplete: true

Requirement: "Wait until report.csv appears in the Downloads folder and its download progress reaches 100%."
→ action_type: WAIT
config:
  wait_type: "CONDITION"
  condition:
    target: "report.csv in the Downloads folder"
    state: "download progress is 100%"
isComplete: true

Insufficient: "Wait until the page is ready."
  condition:
    target: "the page"
    state: null


10. EXCEPTION_HANDLING
----------------------
Requirement: "If the connection to the database fails, retry 3 times with 5-second intervals."
→ action_type: EXCEPTION_HANDLING
config:
  exception:
    type: "database connection failure"
  trigger:
    target: "database connection"
    condition: "connection fails"
  handling_strategy: "RETRY"
  retry_config:
    max_retries: 3
    interval:
      value: 5
      unit: "seconds"
isComplete: true

Insufficient: "If an error occurs, use a fallback."
  handling_strategy: "FALLBACK"
  exception.type: null
  trigger.condition: "an error occurs"
  fallback.action: null


BAD EXAMPLE (What you must NOT do):
Original: "Store the processed information of employee's data in the c:/Thien/main.db."
Wrong description: "Store processed employee data into the specified database"
→ This is incorrect because it paraphrases and loses original wording.

GOOD EXAMPLE:
Original: "Store the processed information of employee's data in the c:/Thien/main.db."
Correct description: "Store the processed information of employee's data in the c:/Thien/main.db."
config:
  operation: null
  destination:
    system: "c:/Thien/main.db"
    object: null
  data:
    source: "the processed information of employee's data"
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

5. The config object must follow the nested field structure
   specified for its action_type. Dotted paths such as
   "target.entity" refer to nested object fields, and "*"
   refers to every item in a list.

6. Conditional required fields must also be included
   when their corresponding condition applies. Use the
   conditional_discriminator declared for the action type.

7. Do NOT invent information that is not supported by
   the original requirement.

8. If a required field cannot be determined from the
   requirement, or its value is too vague to identify
   the intended entity, value, rule, or outcome:
   - Include that field in config with value null.
   - Add its name to unspecified_fields.

9. If a required field is accidentally omitted from
   config, add its name to missing_fields.

10. Set isComplete to false if either missing_fields
    or unspecified_fields is not empty.

11. Set isComplete to true only when every required
    field has a specific, meaningful value supported by
    the requirement. A non-empty generic phrase does not
    automatically make a field complete.

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
    - Preserve the wording in the appropriate nested field. If that wording is still ambiguous, use null rather than guessing.

23. Apply every semantic_requirements entry in the selected action specification. Required fields describe the structure; semantic_requirements describe what each value must mean.

24. Do not invent missing targets, thresholds, query scopes, output formats, decision branches, wait states, recipients, or fallback actions. Do not fill an unstated branch with "no action".

25. Values listed in insufficient_values are examples of non-specific values. Treat an exact match as unspecified and leave it null.
IMPORTANT:
A structurally present and non-empty field does not
necessarily mean that sufficient information is available.

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
        or (isinstance(value, str) and not value.strip())
        or value == []
        or value == {}
    )


def get_field_values(data: dict, field_path: str) -> tuple:
    """Resolve a dotted field path, expanding "*" across list items."""

    values = [data]

    for segment in field_path.split("."):
        resolved_values = []

        for value in values:
            if segment == "*":
                if isinstance(value, list) and value:
                    resolved_values.extend(value)
                else:
                    return True, [None]
            elif isinstance(value, dict):
                if segment not in value:
                    return False, []
                resolved_values.append(value[segment])
            else:
                return True, [None]

        values = resolved_values

    return True, values


def contains_insufficient_value(value, insufficient_values: set) -> bool:
    if isinstance(value, str):
        return value.strip().casefold() in insufficient_values
    if isinstance(value, list):
        return any(
            contains_insufficient_value(item, insufficient_values)
            for item in value
        )
    return False


def evaluation_completeness(action_schema: dict) -> str:
    """
    Evaluate nested required fields and known non-specific values.

    Semantic requirements guide action mapping; this function
    enforces the declared paths, conditions, and value exclusions.
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

            def check_field(field_path: str) -> None:
                present, values = get_field_values(config, field_path)

                if not present:
                    if field_path not in missing_fields:
                        missing_fields.append(field_path)
                elif any(is_empty_value(value) for value in values):
                    if field_path not in unspecified_fields:
                        unspecified_fields.append(field_path)

            for field in specification.get("required_fields", []):
                check_field(field)

            conditional_fields = specification.get(
                "conditional_required_fields", {}
            )
            discriminator = specification.get(
                "conditional_discriminator"
            )

            if discriminator:
                present, values = get_field_values(config, discriminator)

                if present and values and not is_empty_value(values[0]):
                    discriminator_value = str(values[0]).upper()
                    additional_fields = conditional_fields.get(
                        discriminator_value, []
                    )

                    for field in additional_fields:
                        check_field(field)

            for field_path, insufficient_values in specification.get(
                "insufficient_values", {}
            ).items():
                present, values = get_field_values(config, field_path)
                normalized_insufficient = {
                    value.casefold()
                    for value in insufficient_values
                }

                if present and any(
                    contains_insufficient_value(
                        value,
                        normalized_insufficient
                    )
                    for value in values
                ):
                    if field_path not in unspecified_fields:
                        unspecified_fields.append(field_path)

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
