import os
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

if not os.getenv("GOOGLE_API_KEY"):
    raise ValueError("GOOGLE_API_KEY is not set")

def get_supervisor_llm():   
    supervisor_llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-preview-05-20",
        temperature=0.0,
        timeout=30,
        max_retries=2
    )
    return supervisor_llm

def get_formatter_llm():
    formatter_llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-preview-05-20", 
        temperature=0.0,
        timeout=30,
        max_retries=2
    )
    return formatter_llm



