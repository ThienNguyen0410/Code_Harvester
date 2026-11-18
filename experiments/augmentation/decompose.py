
import sys
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.Evaluation_Agent import Evaluation_Agent
from agents.RD_Agent import RD_Agent


def requirment_decomposing(requirement: str) -> dict:
    decompose_output = RD_Agent(requirement).output()

    decompose_result = json.dumps(
        decompose_output,
        indent=4,
        ensure_ascii=False
    )

    evaluation_output = Evaluation_Agent(decompose_result).output()

    return evaluation_output



def read_prompts(file_path: Path) -> list:

    content = file_path.read_text(encoding="utf-8")

    pattern = (
        r"(?ms)^\[(A\d{3}|N\d{3})\]\s+"
        r"(?:ATOMIC|NON-ATOMIC)\s*"
        r"(.*?)"
        r"(?=^\[(?:A|N)\d{3}\]\s+(?:ATOMIC|NON-ATOMIC)\b|\Z)"
    )

    matches = re.finditer(pattern, content)

    prompts = []

    for match in matches:

        prompt_id = match.group(1)
        prompt = match.group(2).strip()

        if prompt:
            prompts.append({
                "id": prompt_id,
                "requirement": prompt
            })

    return prompts


def main():

    input_path = PROJECT_ROOT / "experiments/augmentation/decompose_input.txt"
    output_path = PROJECT_ROOT / "experiments/augmentation/decompose_output.txt"

    prompts = read_prompts(input_path)

    print(f"Total prompts: {len(prompts)}")

    with output_path.open("w", encoding="utf-8") as file:

        for index, item in enumerate(prompts, start=1):

            prompt_id = item["id"]
            requirement = item["requirement"]

            print(f"Processing {index}/{len(prompts)}: {prompt_id}")

            file.write("=" * 80 + "\n")
            file.write(f"PROMPT ID: {prompt_id}\n")
            file.write("=" * 80 + "\n")

            file.write("ORIGINAL PROMPT:\n")
            file.write(requirement + "\n\n")

            try:

                result = requirment_decomposing(requirement)

                file.write("EVALUATION OUTPUT:\n")

                file.write(
                    json.dumps(
                        result,
                        indent=4,
                        ensure_ascii=False,
                        default=str
                    )
                )

                file.write("\n")

                print(f"Completed: {prompt_id}")

            except Exception as e:

                file.write("ERROR:\n")
                file.write(str(e) + "\n")

                print(f"Failed: {prompt_id} - {e}")

            file.write("\n\n")

    print(f"\nAll processing finished!")
    print(f"Output saved to: {output_path}")


if __name__ == "__main__":
    main()
