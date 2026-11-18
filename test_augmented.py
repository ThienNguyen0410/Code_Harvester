from code_split import get_text_embeddings, cal_cosine_similarity


original_prompt = "visit the website with the url www.example.com"
all_preserved_prompts = [
    "Open the website at www.example.com.",
    "Navigate to www.example.com using a web browser.",
    "Access the webpage located at www.example.com.",
    "Go to the website www.example.com.",
    "Launch a browser and visit www.example.com.",
    "Browse to the URL www.example.com.",
    "Open www.example.com in the browser.",
    "Navigate to the web page with the address www.example.com.",
    "Use a browser to access the website at www.example.com.",
    "Visit the web page available at www.example.com.",

    # Additional 10 prompts
    "Please access www.example.com through your browser.",
    "Direct your browser to the website www.example.com.",
    "Load the webpage hosted at www.example.com.",
    "Connect to the website using the URL www.example.com.",
    "Enter www.example.com into the browser's address bar and open it.",
    "Browse the internet to reach www.example.com.",
    "Navigate directly to the homepage of www.example.com.",
    "Use the provided URL to open the corresponding website: www.example.com.",
    "Retrieve the webpage by visiting www.example.com.",
    "Start browsing at www.example.com."
]


contradicted_prompts = [
    "Do not visit the website at www.example.com.",
    "Avoid accessing www.example.com.",
    "Stay away from the website www.example.com.",
    "Do not open www.example.com in the browser.",
    "Never navigate to www.example.com.",
    "Close the browser instead of visiting www.example.com.",
    "Block access to the website www.example.com.",
    "Make sure the browser does not load www.example.com.",
    "Ignore the URL www.example.com and do not access it.",
    "Prevent the browser from connecting to www.example.com.",

    "Visit a different website instead of www.example.com.",
    "Navigate to www.google.com rather than www.example.com.",
    "Open www.wikipedia.org instead of www.example.com.",
    "Access the website www.github.com, not www.example.com.",
    "Go to www.amazon.com rather than the specified URL.",
    "Do not follow the provided URL; visit another website.",
    "Replace www.example.com with www.google.com and open it.",
    "Navigate to a website other than www.example.com.",
    "Access an alternative webpage without visiting www.example.com.",
    "Skip www.example.com and browse another website."
]


original_prompt_embedding = get_text_embeddings(original_prompt)
preserved_result = []
contradicted_result = []

def cal_preserved_prompt():
    for p in all_preserved_prompts:
        p_embedding = get_text_embeddings(p)
        similarity = cal_cosine_similarity(original_prompt_embedding, p_embedding)
        preserved_result.append({
            f"{p}" : similarity
        })
    print("Similarity Table")

def cal_contradicted_prompt():
    for p in contradicted_prompts:
        p_embeddings = get_text_embeddings(p)
        similarity = cal_cosine_similarity(original_prompt_embedding, p_embeddings)
        contradicted_result.append({
            f"{p}" : similarity
        })

# cal_preserved_prompt()
# for item in preserved_result:
#     print(item)
    

# cal_contradicted_prompt()
# for item in contradicted_result:
#     print(item)

p1 = "access"
p2 = "visit"

p3 = "out"

synonym = [
    "enter",
    "approach",
    "reach",
    "gain entry",
    "retrieve",
    "obtain",
    "use",
    "utilize",
    "visit",
    "open",
    "connect",
    "log in",
    "get into",
    "sign in",
    "get access to",
    "browse",
    "interact with",
    "consult",
    "tap into",
    "make use of"
]

unsynonym = [
    "denial",
    "restriction",
    "prohibition",
    "exclusion",
    "inaccessibility",
    "disconnection",
    "rejection",
    "blocking",
    "obstruction",
    "barrier",
     "design",
    "develop",
    "calculate",
    "purchase",
    "download",
    "upload",
    "edit",
    "delete",
    "print",
    "subscribe"
]


for unsy in unsynonym:
    similarity = cal_cosine_similarity(get_text_embeddings(p1), get_text_embeddings(unsy))
    print(f"{unsy} : {similarity}" )



# for sy in synonym:
#     similarity = cal_cosine_similarity(get_text_embeddings(p1), get_text_embeddings(sy))
#     print(f"{sy} : {similarity}" )
