
import sys
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from code_split import get_text_embeddings, cal_cosine_similarity

SIMILARITY_OUTPUT_FILE = PROJECT_ROOT / "experiments/result/similarity/cs_result.txt"
AI_SPLIT_OUTPUT_FILE = PROJECT_ROOT / "experiments/result/similarity/AI_split_result.txt"
AI_SPLIT2_OUTPUT_FILE = PROJECT_ROOT / "experiments/result/similarity/AI_split_result2.txt"

AI_SPLIT3_OUTPUT_FILE = PROJECT_ROOT / "experiments/result/similarity/AI_split_result3.txt"


from agents.Evaluation_Agent.Evaluation_Agent import Evaluation_Agent
from agents.RD_Agent.RD_Agent import RD_Agent
from agents.Classification_Agent.Classification_Agent import Classification_Agent
pair_prompt = [
    # 1. PRESERVED - Academic rephrasing
    (
        "Open the RPA dashboard and display all workflows created by the current user.",
        "Navigate to the RPA dashboard and present the complete collection of workflows associated with the currently authenticated user."
    ),

    # 2. PRESERVED - Academic rephrasing
    (
        "Create a new workflow and save it with the name Invoice Processing.",
        "Instantiate a new automation workflow and persist it under the designated name Invoice Processing."
    ),

    # 3. PRESERVED - Academic rephrasing
    (
        "Run the selected workflow and show its execution status.",
        "Initiate the execution of the selected automation workflow and display its corresponding execution status."
    ),

    # 4. PRESERVED - Academic rephrasing
    (
        "Search for workflows containing the keyword Payment.",
        "Retrieve and display workflows whose names or descriptions contain the specified keyword Payment."
    ),

    # 5. PRESERVED - Academic rephrasing
    (
        "Upload a Python script and add it to the function repository.",
        "Import a Python script into the RPA platform and register it within the centralized function repository."
    ),

    # 6. CONTRADICTED - Opposite action
    (
        "Delete the selected workflow from the platform.",
        "Preserve the selected workflow and prevent its removal from the platform."
    ),

    # 7. CONTRADICTED - Opposite condition
    (
        "Execute the workflow only when all validation tests pass.",
        "Execute the workflow only when at least one validation test fails."
    ),

    # 8. CONTRADICTED - Opposite permission
    (
        "Allow administrators to modify workflow configurations.",
        "Restrict administrators from modifying workflow configurations."
    ),

    # 9. CONTRADICTED - Opposite operation
    (
        "Enable automatic workflow execution after deployment.",
        "Disable automatic workflow execution after deployment."
    ),

    # 10. CONTRADICTED - Opposite state
    (
        "Set the workflow status to Active after successful deployment.",
        "Set the workflow status to Inactive after successful deployment."
    ),

    # 11. ELIMINATED - Remove one requirement
    (
        "Create a workflow, assign it to the Finance team, and enable execution logging.",
        "Create a workflow and assign it to the Finance team."
    ),

    # 12. ELIMINATED - Remove one requirement
    (
        "Upload a Python function, validate its syntax, and store its execution examples.",
        "Upload a Python function and validate its syntax."
    ),

    # 13. ELIMINATED - Remove one requirement
    (
        "Display workflow execution history, including timestamps and error messages.",
        "Display the execution history of workflows."
    ),

    # 14. ELIMINATED - Remove one requirement
    (
        "Allow users to search, filter, and sort workflows by their creation date.",
        "Allow users to search and filter workflows."
    ),

    # 15. ELIMINATED - Remove one requirement
    (
        "Generate a workflow report containing execution time, success rate, and failure details.",
        "Generate a workflow report containing execution time and success rate."
    ),

    # 16. ADDITION - Preserve original and add compatible requirement
    (
        "Display all workflows created by the current user.",
        "Display all workflows created by the current user and organize them by their latest modification date."
    ),

    # 17. ADDITION - Preserve original and add compatible requirement
    (
        "Execute the selected workflow and display its execution status.",
        "Execute the selected workflow, display its execution status, and record the execution start timestamp."
    ),

    # 18. ADDITION - Preserve original and add compatible requirement
    (
        "Allow users to upload Python scripts to the function repository.",
        "Allow users to upload Python scripts to the function repository and categorize them according to their functional purpose."
    ),

    # 19. ADDITION - Preserve original and add compatible requirement
    (
        "Validate the generated Python code before saving it.",
        "Validate the generated Python code before saving it and provide detailed validation feedback to the user."
    ),

    # 20. ADDITION - Preserve original and add compatible requirement
    (
        "Allow administrators to manage user permissions.",
        "Allow administrators to manage user permissions and review the permission modification history."
    ),
    # 21. PRESERVED
    (
        "Create an automation workflow that extracts customer information from a web application and saves it to a CSV file.",
        "Develop an automated workflow to retrieve customer information from a web-based application and persist the extracted records in CSV format."
    ),

    # 22. CONTRADICTED
    (
        "Allow users to execute multiple workflows simultaneously.",
        "Restrict users to executing only one workflow at a time."
    ),

    # 23. ELIMINATED
    (
        "Configure an automation bot, assign it to a specific workflow, and schedule its execution every morning.",
        "Configure an automation bot and assign it to a specific workflow."
    ),

    # 24. ADDITION
    (
        "Display the execution logs of an automation workflow.",
        "Display the execution logs of an automation workflow and allow users to export them as downloadable text files."
    ),

    # 25. ADDITION
    (
        "Allow users to create reusable automation functions.",
        "Allow users to create reusable automation functions and document their input parameters and expected return values."
    )
]

new_pair_prompt = [
     # 26. MIXED: PRESERVED + CONTRADICTED + ELIMINATED + ADDITION
    (
        "Log in to the RPA platform using an authorized administrator account, navigate to the workflow management dashboard, retrieve all workflows created by the currently authenticated user, and display their names, creation dates, execution statuses, and assigned teams. Allow administrators to modify workflow configurations and assign workflows to different departments, while requiring every workflow to pass syntax and configuration validation before execution. Record the execution start time, completion time, and any error messages generated during execution, and provide users with access to the complete execution history. Additionally, send an email notification to the workflow owner whenever a workflow execution fails.",

        "Authenticate with an authorized administrator account and access the workflow management dashboard to retrieve all workflows associated with the currently authenticated user. Present the workflow names, creation dates, execution statuses, and assigned teams, and allow administrators to modify workflow configurations and assign workflows to different departments. However, permit workflows to execute even when their syntax or configuration validation fails. Record the execution start time and completion time for every workflow execution, but do not retain error messages or provide users with access to historical execution records. Furthermore, organize workflows by their latest modification dates, provide an option to export workflow information as CSV files, and display a notification on the dashboard whenever a workflow fails."
    ),

    # 27. MIXED: PRESERVED + CONTRADICTED + ELIMINATED + ADDITION
    (
        "Allow authorized users to upload Python automation scripts to the centralized function repository, validate the syntax of each uploaded script before registration, and reject any script containing syntax errors. After successful validation, extract the function names, input parameters, expected return values, and descriptions from the uploaded scripts, and store this information together with the corresponding source code. Assign a unique identifier to every registered function and allow users to search for functions by their names or descriptions. Maintain a record of the user who uploaded each function and the exact time of registration, and restrict ordinary users from deleting functions that belong to other users.",

        "Enable authorized users to import Python automation scripts into the centralized function repository and validate each script before it is registered. Accept scripts containing syntax errors instead of rejecting them, while continuing to extract function names, input parameters, expected return values, and descriptions from successfully uploaded scripts. Store the extracted metadata together with the corresponding source code, assign a unique identifier to every registered function, and allow users to search for functions using their names or descriptions. Additionally, categorize registered functions according to their functional purposes, display the number of times each function has been reused, and provide an option to download individual source files. Do not maintain information about the identity of the uploading user or the registration timestamp, and allow ordinary users to delete functions uploaded by other users."
    ),

    # 28. MIXED: PRESERVED + CONTRADICTED + ELIMINATED + ADDITION
    (
        "Create a new automation workflow through the visual workflow editor, assign the workflow to the Finance department, and configure its execution schedule to run automatically at 8:00 AM every working day. Before deployment, validate all workflow nodes and verify that every required function is available in the function repository. Prevent workflow execution if any validation test fails, and notify the workflow owner when the deployment process is completed successfully. Maintain execution logs containing the workflow identifier, execution timestamps, success or failure status, and detailed error messages. Allow administrators to pause, resume, or terminate scheduled executions, and provide a dashboard displaying the execution history of each workflow.",

        "Use the visual workflow editor to create a new automation workflow, assign it to the Finance department, and schedule automatic execution at 8:00 AM every working day. Before deployment, validate all workflow nodes and verify that the required functions exist in the function repository. Allow the workflow to proceed with execution even if one or more validation tests fail, and notify the workflow owner when deployment is completed successfully. Record the workflow identifier, execution timestamps, and execution status in the execution logs, but exclude detailed error messages and do not provide a dashboard for reviewing historical executions. Additionally, generate a daily summary report containing the total number of executions, success rate, and average execution duration, and allow administrators to export the report in PDF format."
    ),

    # 29. MIXED: PRESERVED + CONTRADICTED + ELIMINATED + ADDITION
    (
        "Allow users to execute multiple automation workflows simultaneously from the workflow dashboard, select the execution priority for each workflow, and monitor the real-time execution status of all running workflows. Restrict workflow execution to users who have the appropriate permissions, and prevent users from modifying workflow configurations while those workflows are running. Store the execution start time, completion time, and generated error messages for every execution, and allow users to review detailed execution logs after completion. When a workflow fails, automatically retry its execution up to three times and notify the workflow owner if all retry attempts are unsuccessful. Provide administrators with the ability to terminate running workflows and view the execution history of all users.",

        "Enable users to execute multiple automation workflows simultaneously from the workflow dashboard, select an execution priority for each workflow, and monitor the real-time status of all running workflows. Permit users without the required execution permissions to launch workflows, while continuing to prevent modifications to workflow configurations during active executions. Record the execution start time and completion time for every execution, but do not store generated error messages or allow users to review detailed execution logs after completion. Automatically retry failed workflows up to three times and notify the workflow owner when all retry attempts are unsuccessful. Additionally, provide a graphical representation of workflow execution durations, allow users to filter execution records by date and status, and support downloading execution reports in CSV format."
    ),

    # 30. MIXED: PRESERVED + CONTRADICTED + ELIMINATED + ADDITION
    (
        "Allow administrators to create, update, and deactivate user accounts within the RPA platform, assign roles and permissions to each account, and restrict access to workflow management features according to the assigned permissions. Require users to authenticate using their registered email addresses and passwords before accessing protected resources, and automatically terminate inactive sessions after thirty minutes. Maintain an audit log containing the administrator identity, affected user account, modified permission, and modification timestamp whenever account permissions are changed. Provide administrators with a searchable interface for reviewing permission modification history, and prevent ordinary users from viewing administrative audit records. Additionally, send an email notification to users whenever their account permissions are modified.",

        "Enable administrators to create, update, and deactivate user accounts within the RPA platform, assign roles and permissions to each account, and restrict access to workflow management features based on assigned permissions. Require users to authenticate using their registered email addresses and passwords before accessing protected resources, but extend inactive sessions indefinitely instead of terminating them after thirty minutes. Maintain an audit log containing the administrator identity, affected user account, modified permission, and modification timestamp whenever account permissions are changed. Allow ordinary users to access administrative audit records and provide administrators with a searchable interface for reviewing permission modification history. Furthermore, introduce two-factor authentication using email verification codes, display the last successful login time for every user account, and provide administrators with an option to export account permission records as downloadable CSV files. Do not send email notifications when user permissions are modified."
    )
]



pair_prompt3 = [
   

    # 7. ELIMINATED - Missing original requirement
    (
        "Navigate to the recruitment management portal, open the candidate directory, "
        "search for candidates applying for the Software Engineer position, retrieve "
        "their names and email addresses, and generate a CSV report containing the "
        "matching candidate information.",

        "Navigate to the recruitment management portal, open the candidate directory, "
        "search for candidates applying for the Software Engineer position, and retrieve "
        "their names and email addresses for further recruitment activities."
    ),

    
]

def using_cosine_similarity(p1: str, p2: str) -> float :
    p1_text = get_text_embeddings(p1)
    p2_text = get_text_embeddings(p2)
    return cal_cosine_similarity(p1_text, p2_text)

def cosine_similarity_output():
    cosine_similarity_table = []

    for pair_item in pair_prompt:
        similarity = using_cosine_similarity(pair_item[0], pair_item[1])

        cosine_similarity_table.append({
            "prompt_1": pair_item[0],
            "prompt_2": pair_item[1],
            "similarity": similarity
        })

    # Sort theo similarity giảm dần
    cosine_similarity_table.sort(
        key=lambda item: item["similarity"],
        reverse=True
    )

    with open(SIMILARITY_OUTPUT_FILE, "w", encoding="utf-8") as file:
        for index, item in enumerate(cosine_similarity_table, start=1):
            file.write(f"RANK {index}\n")
            file.write(f"Similarity: {item['similarity']:.6f}\n")
            file.write(f"Prompt 1: {item['prompt_1']}\n")
            file.write(f"Prompt 2: {item['prompt_2']}\n")
            file.write("=" * 100 + "\n")

    print("Results have been saved to output.txt")


def classify(schema: dict) -> str:
    CONTRADICTION = len(schema["List_Of_Contradicted_Pairs"])
    ELIMINATED = len(schema["ELIMINATED_LIST"])

    return CONTRADICTION == 0 and ELIMINATED == 0


def AI_split_result_output():
    AI_split_result_table = []

    for pair_item in pair_prompt3:
        schema1 = RD_Agent(pair_item[0]).output()
        schema2 = RD_Agent(pair_item[1]).output()
        result = Classification_Agent(schema1, schema2).output()
        print(json.dumps(result, indent=4, ensure_ascii=False))
    #     classification = Classification_Agent(schema1, schema2).output()
    #     if classify(classification):
    #         AI_split_result_table.append({
    #             "prompt_1": pair_item[0],
    #             "prompt_2": pair_item[1],
    #             "classify": "Good augmentation"
    #         })

    #     else:
    #          AI_split_result_table.append({
    #             "prompt_1": pair_item[0],
    #             "prompt_2": pair_item[1],
    #             "classify": "Bad augmentation"
    #         })

    # with open(AI_SPLIT3_OUTPUT_FILE, "w", encoding="utf-8") as file:
    #     for index, item in enumerate(AI_split_result_table, start=1):
    #         file.write(f"No: {index}\n")
    #         file.write(f"Classification: {item['classify']}\n")
    #         file.write(f"Prompt 1: {item['prompt_1']}\n")
    #         file.write(f"Prompt 2: {item['prompt_2']}\n")
    #         file.write("=" * 100 + "\n")

def main():
    #cosine_similarity_output()
    AI_split_result_output()

if __name__ == "__main__":
    main()
