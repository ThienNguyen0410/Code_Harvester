from code_split import get_text_embeddings, cal_cosine_similarity


p1 = "Add 2 numbers"
p2 = "Substract 2 numbers"

print(cal_cosine_similarity(get_text_embeddings(p1), get_text_embeddings(p2)))
