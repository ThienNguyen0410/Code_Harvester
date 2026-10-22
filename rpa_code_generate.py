import ast
import re
from datetime import date
from pathlib import Path
from typing import Dict, List
from dotenv import load_dotenv
from crewai import Agent, Crew, Task
from code_gen import llm
from code_split import get_text_embeddings, cal_cosine_similarity

load_dotenv()
RPA_LIBRARY_PATH = Path("rpa_code.py")

class RPA_Code_Generate:
    def __init__(
        self,
        augmented_prompt: str,
        ranking_table: List[Dict[str, object]],
    ):
        if not augmented_prompt.strip():
            raise ValueError("The augmented prompt cannot be empty.")
        if not ranking_table:
            raise ValueError("The ranking table cannot be empty.")

        self.ranking_table = ranking_table
        self.augmented_prompt = augmented_prompt

    def RPA_generate_code(self) -> str:
        ranked_functions = []
        for rank, result in enumerate(self.ranking_table, start=1):
            function = result.get("function")
            if not isinstance(function, str) or not function.strip():
                raise ValueError(
                    f"The ranking table entry at position {rank} does not contain a valid function."
                )

            ranked_functions.append(
                f"Rank: {rank}\n"
                f"Similarity: {result.get('similarity', 'unknown')}\n"
                f"Stream: {result.get('stream', 'unknown')}\n"
                f"Code:\n{function}"
            )

        agent = Agent(
            role="RPA Python Code Generator",
            goal=(
                "Generate a Python function that satisfies the augmented prompt, "
                "leverages highly ranked functions, and follows the output standard."
            ),
            backstory=(
                "You are a Python engineer specializing in building functions for RPA. "
                "Use the ranked code as a reference; do not copy it mechanically."
            ),
            llm=llm,
            verbose=True,
            max_iter=2,
            allow_delegation=False,
        )
        task = Task(
            description=(
                "Create exactly one new Python function that satisfies the requirement "
                "in the augmented prompt below. Use the functions in the ranking table "
                "as references for logic and implementation; prioritize higher-ranked "
                "entries with greater similarity and reuse only relevant parts.\n\n"
                f"AUGMENTED PROMPT:\n{self.augmented_prompt}\n\n"
                "RANKING TABLE (in ranked order):\n"
                f"{chr(10).join(ranked_functions)}\n\n"
                "STANDARDIZE:\n"
                "```text\n"
                f"{self._get_standardize_guide()}\n"
                "```\n\n"
                "Just Use the available methods which are defined in\n"
                f"{self._get_sample_code()}\n"
                "In case there are methods which were not available. You need to generate that methods by using functions in ranking table as references\n"
                "Do not import the libraries which were imported before\n"
                "Follow the standard above: create a valid Python function, use the "
                "appropriate @keyword(...) decorator, and include a comment or "
                f"docstring stating the code generation date ({date.today().isoformat()}) "
                "and the function's purpose. Replace the placeholders in the guide "
                "with actual values; the function declaration must include parameter "
                "parentheses and a colon. If needed for the code to run independently, "
                "add the appropriate decorator import. Return only Python code, "
                "without explanations."
            ),
            expected_output="Valid Python source code for exactly one RPA function.",
            agent=agent,
        )
        response = Crew(agents=[agent], tasks=[task], verbose=True).kickoff()
        if response is None:
            raise ValueError("The agent returned empty code or a non-text response.")

        response_text = str(response)

        if not response_text.strip():
            raise ValueError("The agent returned empty code or a non-text response.")

        code_blocks = re.findall(
            r"```(?:python|py)?\s*\n(.*?)```",
            response_text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        candidates = code_blocks or [response_text.strip()]
        syntax_error = None

        for candidate in candidates:
            candidate = candidate.strip()
            try:
                ast.parse(candidate)
            except SyntaxError as error:
                syntax_error = error
                continue
            with RPA_LIBRARY_PATH.open("a", encoding="utf-8") as file:
                file.write(f"\n\n{candidate}\n")
            return candidate

        if syntax_error is not None:
            raise ValueError(
                "The agent did not return valid Python code. "
                f"Syntax error on line {syntax_error.lineno}: {syntax_error.msg}"
            ) from syntax_error

        raise ValueError("The agent did not return a valid Python code block.")

    @staticmethod
    def _get_standardize_guide() -> str:
        standardize_path = Path(__file__).with_name("standarlize.md")
        with standardize_path.open(encoding="utf-8") as standardize_file:
            return standardize_file.read()

    @staticmethod
    def _get_sample_code() -> str:
        libpath = Path(__file__).with_name("rpa_code.py")
        with libpath.open(encoding="utf-8") as file:
            return file.read()
