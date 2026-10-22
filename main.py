import asyncio
from pathlib import Path
from typing import Dict, List

from augmented_prompt import augment_prompt
from code_split import extract_all_functions
from essemble_streaming import Essemble_Multi_Stream
from rpa_code_generate import RPA_Code_Generate


GITHUB_REPO = "https://github.com/ThienNguyen0410/Test_Harvester.git"
FUNCTIONS_FILE = Path(__file__).with_name("test.py")


def print_ranking_table(ranking_table: List[Dict]) -> None:
    if not ranking_table:
        print("\nNo suitable functions found to rank.")
        return

    print("\n===== RANKING TABLE =====")
    for rank, result in enumerate(ranking_table, start=1):
        print(
            f"\n--- Rank {rank} | "
            f"Similarity: {result['similarity']:.4f} | "
            f"Stream: {result['stream']} ---"
        )
        print(result["function"])
        # if "generated_function" in result:
        #     print("\nCorresponding generated function:")
        #     print(result["generated_function"])


def main() -> None:
    user_prompt = input("Enter a prompt: ").strip()
    if not user_prompt:
        raise ValueError("The prompt cannot be empty.")

    functions = extract_all_functions(str(FUNCTIONS_FILE))
    if not functions:
        raise RuntimeError(f"No functions found in {FUNCTIONS_FILE}.")

    print("\nAugmenting prompt...")
    augmented_prompt = augment_prompt(user_prompt, GITHUB_REPO)
    print("\n===== AUGMENTED PROMPT =====")
    print(augmented_prompt)

    stream_runner = Essemble_Multi_Stream(
        augmented_prompt=augmented_prompt,
        functions=functions,
        ranking_table=[],
    )
    ranking_table = asyncio.run(stream_runner.run_all())
    print_ranking_table(ranking_table)

    print("\nGenerating RPA code...")
    code_generator = RPA_Code_Generate(
        augmented_prompt=augmented_prompt,
        ranking_table=ranking_table,
    )
    generated_code = code_generator.RPA_generate_code()
    print("\n===== GENERATED RPA CODE =====")
    print(generated_code)


if __name__ == "__main__":
    main()