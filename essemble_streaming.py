import ast
from code_split import get_text_embeddings, cal_cosine_similarity
from code_gen import generate_code
from typing import List, Dict


class Essemble_Multi_Stream:
    def __init__(
        self,
        augmented_prompt: str,
        functions: List[str],
        ranking_table: List[Dict],
    ):
        self.augmented_prompt = augmented_prompt
        self.functions = functions
        self.ranking_table = ranking_table
        self.prompt_embedding = get_text_embeddings(self.augmented_prompt)
        self.generate_code = ""

    """Stream 01 ranks functions by similarity to the augmented prompt."""
    async def run_stream01(self):
        result = {}

        for function in self.functions:
            function_embedding = get_text_embeddings(self._get_function_code(function))
            similarity = cal_cosine_similarity(function_embedding, self.prompt_embedding)
            result[function] = similarity

        self._append_top_results(result, "stream01")

    async def run_stream02(self):
        result = {}
        generated_code = generate_code(self.augmented_prompt)
        self.generate_code = generated_code
        code_embedding = get_text_embeddings(generated_code)

        for function in self.functions:
            function_embedding = get_text_embeddings(self._get_function_code(function))
            similarity = cal_cosine_similarity(function_embedding, code_embedding)
            result[function] = similarity

        self._append_top_results(result, "stream02")

    async def run_stream03(self):
        if not self.generate_code or not self.generate_code.strip():
            return

        tree = ast.parse(self.generate_code)
        generated_functions = [
            ast.get_source_segment(self.generate_code, node)
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        generated_functions = [code for code in generated_functions if code]

        if not generated_functions or not self.functions:
            return

        best_matches = {}
        for generated_function in generated_functions:
            generated_embedding = get_text_embeddings(generated_function)

            for function in self.functions:
                function_code = self._get_function_code(function)
                similarity = cal_cosine_similarity(
                    get_text_embeddings(function_code),
                    generated_embedding,
                )

                if (
                    function not in best_matches
                    or similarity > best_matches[function]["similarity"]
                ):
                    best_matches[function] = {
                        "function": function,
                        "similarity": similarity,
                        "generated_function": generated_function,
                        "stream": "stream03",
                    }

        self.ranking_table.extend(
            sorted(
                best_matches.values(),
                key=lambda result: result["similarity"],
                reverse=True,
            )[:3]
        )

    async def run_all(self):
        await self.run_stream01()
        await self.run_stream02()
        await self.run_stream03()
        self.ranking_table.sort(
            key=lambda result: result["similarity"],
            reverse=True,
        )
        return self.ranking_table

    @staticmethod
    def _get_function_code(function):
        if isinstance(function, str):
            return function
        raise TypeError("Each function must be Python source code.")

    def _append_top_results(self, similarities, stream_name):
        self.ranking_table.extend(
            {
                "function": function,
                "similarity": similarity,
                "stream": stream_name,
            }
            for function, similarity in sorted(
                similarities.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:3]
        )

    def get_ranking_table(self):
        return self.ranking_table