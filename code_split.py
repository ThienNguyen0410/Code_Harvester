
import ast
from typing import List, Dict
import numpy as np
from numpy.linalg import norm
from sentence_transformers import SentenceTransformer
from code_gen import generate_code

model = SentenceTransformer("all-MiniLM-L6-v2")


def extract_all_functions(file_path: str) -> List[str]:
    """
    Extract all functions and methods from a Python file,
    including methods within classes.
    Return a list containing the source code of each function.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        source_code = f.read()

    tree = ast.parse(source_code)
    functions = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_code = ast.get_source_segment(source_code, node)

            if func_code:
                functions.append(func_code)

    return functions


def get_function_embeddings(file_path: str) -> List[Dict]:
    """
    Extract functions and calculate an embedding for each one.
    Return a list of dictionaries containing the code and embedding.
    """
    functions = extract_all_functions(file_path)

    if not functions:
        return []

    embeddings = model.encode(
        functions,
        convert_to_numpy=True,
        show_progress_bar=True
    )

    results = []

    for func_code, embedding in zip(functions, embeddings):
        results.append({
            "code": func_code,
            "embedding": embedding,
            "embedding_shape": embedding.shape
        })

    return results

def get_text_embeddings(text: str) -> np.ndarray:

    if not text or not isinstance(text, str) or not text.strip():
        raise ValueError("Text is invalid! Can not find vector embeddings!")

    embeddings = model.encode(
        text,
        convert_to_numpy=True,
    )

    return embeddings

def cal_cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    if v1.shape != v2.shape:
        raise ValueError("Two shapes are differents!")

    if norm(v1) == 0 or norm(v2) == 0:
        return 0.0

    return (np.dot(v1, v2)) / (norm(v1) * norm(v2))

# ====================== Usage example ======================
if __name__ == "__main__":

    ranking_table = {}

    prompt = input("Please enter your prompt: ")
    prompt_embedding = get_text_embeddings(prompt)

    function_emdbedings = get_function_embeddings("test.py")

    for item in function_emdbedings:
        cosine_similarity = cal_cosine_similarity(item["embedding"], prompt_embedding)
        ranking_table[item["code"]] = cosine_similarity


    sorted_ranking = sorted(ranking_table.items(), key=lambda x: x[1], reverse=True)

    print("\n===== RANKING TABLE =====")
    for i, (code, score) in enumerate(sorted_ranking, 1):
        print(f"\n--- Rank {i} | Similarity: {score:.4f} ---")
        print(code)