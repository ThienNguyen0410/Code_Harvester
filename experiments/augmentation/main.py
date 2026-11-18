from decompose import requirment_decomposing
import json

def main():
    user_prompt = (
            "The system shall allow registered users to log in "
            "using their email address and password. "
            "The system shall validate the provided credentials "
            "and display an error message if the email or "
            "password is incorrect."
        )
    decompose_result = requirment_decomposing(user_prompt)

    print(json.dumps(
        decompose_result,
        indent=4,
        ensure_ascii=False
    ))

main()