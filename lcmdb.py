import os
import time
import uuid
from typing import Any, Dict, Literal

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_mongodb.agent_toolkit import MONGODB_AGENT_SYSTEM_PROMPT

# MongoDB Agent Toolkit
from langchain_mongodb.agent_toolkit.database import MongoDBDatabase
from langchain_mongodb.agent_toolkit.toolkit import MongoDBDatabaseToolkit

# LangGraph Core
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, create_react_agent
from pymongo import MongoClient
from groq import Groq
from langchain_groq import ChatGroq
from pymongo import MongoClient
import os
from dotenv import load_dotenv
load_dotenv()  
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

uri = "mongodb+srv://prithviraj82rt:prithvirajjouganrt@hotel-data.rk61lvj.mongodb.net/?retryWrites=true&w=majority&appName=Hotel-data"

client = MongoClient(
    uri , appname="langchain-llm-app"
)

db = MongoDBDatabase.from_connection_string(uri , "Hotel")

llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model="openai/gpt-oss-20b",
    temperature=0,
)


# Create toolkit and extract tools
toolkit = MongoDBDatabaseToolkit(db=db, llm=llm)
tools = toolkit.get_tools()

def create_react_agent_with_enhanced_memory():
    """Create ReAct agent with LLM-powered summarizing checkpointer"""
    system_message = MONGODB_AGENT_SYSTEM_PROMPT.format(top_k=5)
    
    return create_react_agent(
        llm,
        toolkit.get_tools(),
        prompt=system_message,
    )

react_agent_with_memory = create_react_agent_with_enhanced_memory()
   
def execute_react_with_memory(thread_id: str, user_input: str) -> str:
    """Run the agent and return the final AI message as plain text."""
    config = {"configurable": {"thread_id": thread_id}}
    events = list(react_agent_with_memory.stream(
        {"messages": [("user", user_input)]}, config, stream_mode="values"
    ))
    final_ai_message = None
    for event in reversed(events):
        for msg in reversed(event["messages"]):
            if isinstance(msg, AIMessage):
                final_ai_message = msg
                break
        if final_ai_message:
            break
    if final_ai_message:
        return final_ai_message.content
    else:
        return "Sorry, I couldn't process your request."
