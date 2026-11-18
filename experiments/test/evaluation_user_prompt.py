
import sys
import json
import re
import os
from crewai import LLM
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.augmentation.evaluation_tmp import evaluation_completeness, mapping_sub_requirement_to_action, decompose_user_prompt


openai_api_key = os.getenv("OPENAI_API_KEY") 
openai_model = os.getenv("GPT_MODEL")
openai_baseurl = os.getenv("OPENAI_API_BASE")
llm = LLM(
    model=openai_model,
    api_key= openai_api_key,
    base_url=openai_baseurl
)

LLM_ONLY_OUTPUT_FILE = PROJECT_ROOT / "experiments/result/evaluation/llm_only.txt"
USING_5_METRICS = PROJECT_ROOT / "experiments/result/evaluation/using_5_metrics.txt"
USING_AI_SPLIT = PROJECT_ROOT / "experiments/result/evaluation/AI_split.txt"
USING_AI_SPLIT2 = PROJECT_ROOT / "experiments/result/evaluation/AI_split2.txt"

prompt_dataset = [
    # ==========================================
    # FULLY SPECIFIED (15)
    # ==========================================

    "Open the RPA dashboard, navigate to the Workflow Management page, and display all workflows created by the currently authenticated user.",

    "Create a new automation workflow named Invoice Processing and save it to the My Workflows collection.",

    "Search for workflows whose names contain the keyword Payment and display the matching results.",

    "Upload the file invoice_processor.py from the local Downloads folder to the Function Repository and register it under the category Data Processing.",

    "Execute the workflow named Daily Report Generation and display its final execution status after the process finishes.",

    "Configure the Invoice Processing workflow to execute automatically every day at 08:00 AM.",

    "Open the Execution History page and filter execution records to display only workflows with the status Failed.",

    "Export the execution logs of the workflow named Customer Synchronization as a CSV file and save the exported file to the local Downloads folder.",

    "Open the User Management page and assign the Viewer role to the user with username john_doe.",

    "Validate the Python syntax of the file data_extractor.py and display all syntax errors with their corresponding line numbers.",

    "Open the workflow configuration page and change the execution timeout of Invoice Processing to 120 seconds.",

    "Extract the product names and prices from the first five results displayed on the product search page and save the extracted data to products.csv.",

    "If the execution status of Invoice Processing is Failed, send an email notification to admin@example.com with the workflow name and error message in the email body.",

    "Create a reusable Python function named calculate_total that accepts a list of numeric prices and returns their sum.",

    "Open the Bot Management page, select the bot named InvoiceBot, assign it to the Invoice Processing workflow, and save the configuration.",


    # ==========================================
    # UNDERSPECIFIED (15)
    # ==========================================

    "Open the dashboard and display the relevant information.",

    "Create a new automation workflow.",

    "Search for workflows using an appropriate keyword.",

    "Upload the Python script to the RPA platform.",

    "Execute the workflow and display its status.",

    "Schedule the automation bot to run automatically.",

    "Filter the execution history based on its status.",

    "Export the workflow execution logs to a file.",

    "Assign an appropriate role to the selected user.",

    "Validate the Python script and fix any problems found.",

    "Change the workflow execution configuration to an appropriate value.",

    "Extract customer information from the website and save the results.",

    "If the workflow encounters an error, notify the appropriate person.",

    "Create a reusable Python function to process the input data.",

    "Assign the automation bot to the workflow and configure its execution settings."
]

test_prompt = [
    "Assign the automation bot to the workflow and configure its execution settings."

]

added_prompt = [
      # ==========================================
    # ADDITIONAL PROMPTS (10)
    # ==========================================

    # 1. INTERACTION
    # Enough information: Has operation=CLICK and element=Run Workflow button.
    "Open the Workflow Management page, locate the Run Workflow button, "
    "and click it to start the selected automation workflow.",

    # 2. DATA_RETRIEVAL
    # Enough information: Has source=Execution History and retrieval_method=FILTER.
    "Retrieve execution records from the Execution History database by filtering "
    "all records whose execution status is Failed.",

    # 3. DATA_INPUT
    # Enough information: Has input_method=TEXT_ENTRY, destination=Workflow Name field,
    # and value=Monthly Sales Report.
    "Enter the text Monthly Sales Report into the Workflow Name input field "
    "on the workflow creation page.",

    # 4. DATA_PROCESSING
    # Enough information: Has operation=SUM, operands=extracted invoice amounts,
    # and output_name=total_invoice_amount.
    "Calculate the sum of all extracted invoice amounts from the current processing "
    "batch and store the calculated result in a variable named total_invoice_amount.",

    # 5. VALIDATION
    # Enough information: Has subject=workflow execution status and validation_rule=Completed.
    "Verify whether the execution status of the Invoice Processing workflow "
    "is equal to Completed before allowing the workflow to proceed.",

    # 6. DECISION
    # Enough information: Has condition and two explicit branches.
    "Check whether the extracted invoice amount is greater than 10000 dollars. "
    "If the condition is true, route the invoice to the manager approval process; "
    "otherwise, continue with the standard invoice processing procedure.",

    # 7. DATA_STORAGE
    # Enough information: Has operation=INSERT, destination=Execution History,
    # and data=workflow name, execution status, execution timestamp.
    "Insert a new execution record into the Execution History database containing "
    "the workflow name, final execution status, and execution timestamp "
    "after the automation process has finished.",

    # 8. COMMUNICATION
    # Enough information: Has channel=EMAIL, recipient=admin@example.com,
    # and content=workflow name and error message.
    "Send an email notification to admin@example.com containing the workflow name "
    "and the corresponding error message whenever an automation workflow fails.",

    # 9. WAIT
    # Lack of information: Has wait_type=DURATION but missing duration.
    "Wait for a specified period of time before clicking the Submit button "
    "on the workflow configuration page.",

    # 10. EXCEPTION_HANDLING
    # Lack of information: Has exception_type and trigger_condition,
    # but missing handling_strategy.
    "Handle any TimeoutError exception that occurs when executing the Invoice Processing "
    "workflow if the execution request exceeds the configured response time."
]

def using_LLM_only():
    using_LLM_only_table = []
    for prompt in test_prompt:
        system_prompt = f"""
        Does the prompt {prompt} has enough information to understand?
        If that prompt has enough information return "Enough information"
        Else return "Lack of information"

        RULES:
        1. Just return the text "Enough information" or "Lack of information"
        2. Do not include the strip markdown in return statement
        """
        respose_text = llm.call(system_prompt)

        using_LLM_only_table.append({
            "prompt": prompt,
            "conclusion" : respose_text
        })

    with open(LLM_ONLY_OUTPUT_FILE, "a", encoding="utf-8") as file:
            for index, item in enumerate(using_LLM_only_table, start=1):
                file.write(f"No: {index}\n")
                file.write(f"Prompt: {item['prompt']}\n")
                file.write(f"Conclusion: {item['conclusion']}\n")
                file.write("=" * 100 + "\n")

    


def evaluating_with_5_metrics():
    using_5_metrics_table = []

    for prompt in added_prompt:
        system_prompt = f"""
        Evaluate the following individual requirement based on
        the five metrics below.

        REQUIREMENT:
        {prompt}

        METRICS:

        Ra1 - Requirement Correctness:
        Is the individual requirement properly defining a genuine
        system function and need?

        Ra2 - Requirement Unambiguity:
        Is the individual requirement clear and understandable
        to the expected users of the document?

        Ra3 - Requirement Atomic Completeness:
        Does the individual requirement include everything necessary
        to fully understand the desired functionality?

        Ra4 - Requirement Atomic Verifiability:
        How adequately can this individual requirement be tested
        with a result able to show 100% passed or failed?

        Ra5 - Requirement Atomic Undecomposability:
        Would further breakup of this requirement into separate parts
        be extremely difficult or detract from its understandability?

        EVALUATION RULES:
        1. Evaluate the requirement independently against all five metrics.
        2. Assign a score from 1 to 10 for each metric.
        3. Determine whether each metric PASSES or FAILS based on
           its definition and the quality of the requirement.
        4. A requirement PASSES only if all five metrics PASS.
        5. If all five metrics PASS, return "Enough information".
        6. If at least one metric FAILS, return "Lack of information".

        OUTPUT RULES:
        1. Return only one of the following:
           "Enough information"
           "Lack of information"
        2. Do not include explanations.
        3. Do not include markdown formatting.
        """

        response_text = llm.call(system_prompt)

        using_5_metrics_table.append({
            "prompt": prompt,
            "conclusion": response_text
        })

    with open(USING_5_METRICS, "a", encoding="utf-8") as file:
        for index, item in enumerate(using_5_metrics_table, start=1):
            file.write(f"No: {index}\n")
            file.write(f"Prompt: {item['prompt']}\n")
            file.write(f"Conclusion: {item['conclusion']}\n")
            file.write("=" * 100 + "\n")

def using_AI_split():
    using_AI_split_table = []
    for prompt in added_prompt:
        decomposed_schema = decompose_user_prompt(prompt)
        mapping_schema = mapping_sub_requirement_to_action(decomposed_schema)
        prompt_conclusion = evaluation_completeness(mapping_schema)
        using_AI_split_table.append({
            "prompt": prompt,
            "conclusion": prompt_conclusion
        })

    with open(USING_AI_SPLIT2, "a", encoding="utf-8") as file:
        for index, item in enumerate(using_AI_split_table, start=1):
            file.write(f"No: {index}\n")
            file.write(f"Prompt: {item['prompt']}\n")
            file.write(f"Conclusion: {item['conclusion']}\n")
            file.write("=" * 100 + "\n")

def main():
    #using_LLM_only()
    #evaluating_with_5_metrics()
    using_AI_split()

if __name__ == "__main__":
    main()