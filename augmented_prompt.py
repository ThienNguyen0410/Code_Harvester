import os
from crewai import Agent, Task, Crew, LLM
from crewai.tools import tool
from duckduckgo_search import DDGS
from dotenv import load_dotenv

# ======================
# 1. Configure the Groq model
# ======================
load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY is not configured in the .env file.")

# Previous Gemini configuration:
# llm = LLM(
#     model="gemini-3.8-flash",
#     temperature=0.3
# )

llm = LLM(
    model="openai/openai/gpt-oss-20b",
    api_key=groq_api_key,
    base_url="https://api.groq.com/openai/v1",
    temperature=0.3,
)

# ======================
# 2. Search tool
# ======================
@tool("Internet Search")
def internet_search(query: str) -> str:
    """Search the internet for information related to the query."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        
        if not results:
            return "No relevant information was found."
        
        content = "\n\n".join([
            f"Title: {r.get('title', '')}\nContent: {r.get('body', '')}" 
            for r in results
        ])
        return content
    except Exception as e:
        return f"Search error: {str(e)}"

# ======================
# 3. Create the agent
# ======================
technical_writer = Agent(
    role="Technical Research Writer",
    goal="Add detailed technical information to the user's prompt based on the GitHub repository context",
    backstory=(
        "You are a Technical Research Writer specializing in enriching prompts. "
        "Only add information related to topics in the original prompt. "
        "Prioritize information from the repository; if none is available, use general knowledge. "
        "Stay focused."
    ),
    tools=[internet_search],
    llm=llm,
    verbose=True,
    max_iter=2,
    allow_delegation=False
)

# ======================
# 4. Prompt augmentation function
# ======================
def augment_prompt(user_query: str, github_repo: str) -> str:
    task = Task(
        description=(
            f"Given an input text prompt: {user_query}\n\n"
            f"Add more technical details about some of the topics in this text prompt "
            f"in the general context of the following github repo: {github_repo}.\n\n"
            f"If you can’t find how it is implemented in the repository, then provide "
            f"information on how it is implemented generally.\n"
            f"Ensure that you only give info on specifically the topics present in the input text prompt. "
            f"Do not deviate from the topic."
        ),
        expected_output="A clear, focused paragraph enriched with technical information.",
        agent=technical_writer
    )

    crew = Crew(
        agents=[technical_writer],
        tasks=[task],
        verbose=True
    )

    result = crew.kickoff()
    return str(result)

# ======================
# 5. Run a test
# ======================
if __name__ == "__main__":
    user_query = "update the splitter and readline delims when greedy is changed"
    github_repo = "https://github.com/cloudflare/gurumate"

    print("=== Original User Prompt ===")
    print(user_query)
    print("\n=== Augmenting prompt... ===\n")

    augmented = augment_prompt(user_query, github_repo)

    print("\n=== Augmented Prompt ===")
    print(augmented)