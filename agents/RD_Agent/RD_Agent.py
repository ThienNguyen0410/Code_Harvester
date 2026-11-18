
"""RD Agent (Requirement Decomposition Agent).
This agent decomposes a natural-language requirement
into smaller sub-requirements.
"""

import json
import os
import re

from dotenv import load_dotenv
from crewai import LLM


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

        # These fields will be evaluated by the Atomicity Agent.
        sub_requirement["isAtomic"] = None

    return result


class RD_Agent:

    def __init__(self, user_requirement: str):
        self.user_requirement = user_requirement

    def decompose(self) -> dict:

        system_prompt = f"""
        You are a Requirement Decomposition Agent.

        Your task is to decompose the given natural-language
        software requirement into smaller sub-requirements.

        ORIGINAL REQUIREMENT:
        {self.user_requirement}

        OUTPUT SCHEMA:
        {json.dumps(DECOMPOSE_SCHEMA, indent=4)}

        DECOMPOSITION RULES:

        1. Preserve the original meaning of the requirement.
        2. Each sub-requirement should describe one independent
        functional behavior.
        3. Do not introduce new requirements.
        4. Do not omit any information from the original requirement.
        5. Keep conditions, inputs, constraints, and outcomes
        together when they belong to the same functional behavior.
        6. Do not split a requirement merely because it contains
        multiple verbs or the word "and".
        7. Separate behaviors only when they can be specified
        and verified independently without losing their meaning.
        8. Assign sequential IDs: SR-001, SR-002, SR-003, etc.
        9. Fill in Original_requirement and Sub_requirements_list.
        10. Set isAtomic to null.
        11. Return ONLY a valid JSON object.
        12. Do not include Markdown code blocks or explanations.
        13. Do not add any information which did not appear in original requirements.
        14. Strictly preserve the semantic content of the original
    requirement. Do not enrich, extend, or reinterpret its meaning.

    15. Do not infer implicit information, intentions, or behaviors
        that are not explicitly stated in the original requirement.

    16. Do not introduce new:
        - Actions or operations.
        - Conditions or decision criteria.
        - Inputs, outputs, or data values.
        - Constraints or validation rules.
        - Execution sequences or dependencies.
        - Error-handling behaviors or fallback strategies.

    17. Do not replace unspecified information with assumed,
        conventional, or contextually reasonable values.

    18. Do not make the requirement more specific than the
        original statement.
        """

        response_text = llm.call(system_prompt)

        return validate_AI_response(response_text)

    def output(self) -> dict:
        return self.decompose()


if __name__ == "__main__":

    user_prompt = (
    'Open the shopping website, search for "Laptop", '
    'and retrieve the product name and price of the first search result. '
    'If the price is less than $1,000, add the product to the shopping cart.'
)

    agent = RD_Agent(user_prompt)

    result = agent.output()

    print(
        json.dumps(
            result,
            indent=4,
            ensure_ascii=False
        )
    )
