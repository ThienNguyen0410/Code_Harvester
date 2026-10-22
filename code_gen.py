
import ast
import os
import re

from crewai import LLM
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("GROQ_API_KEY is not configured in the .env file.")

llm = LLM(
    model="openai/openai/gpt-oss-20b",
    api_key=api_key,
    base_url="https://api.groq.com/openai/v1",
    temperature=0.3,
)

def generate_code(contents_prompt: str) -> str:
    final_prompt = (
        "Write a Python function that applies the requirement in this description:\n"
        f"{contents_prompt}\n\n"
        "Return only valid Python source code. Do not include explanations, numbered "
        "lists, or Markdown. If you use a Markdown code fence, include only Python "
        "source inside it."
    )

    response_text = llm.call(final_prompt)
    if not isinstance(response_text, str):
        raise TypeError("Groq returned a non-text response instead of Python code.")

    if not response_text or not response_text.strip():
        raise ValueError("Groq returned an empty response instead of Python code.")

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
        return candidate

    if syntax_error is not None:
        raise ValueError(
            "Groq's response did not contain valid Python code. "
            f"Syntax error on line {syntax_error.lineno}: {syntax_error.msg}"
        ) from syntax_error

    raise ValueError("Groq's response did not contain a Python code block.")
