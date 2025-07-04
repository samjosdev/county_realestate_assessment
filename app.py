import gradio as gr
import asyncio
import os
import uuid
from dotenv import load_dotenv
from build_Graph import USCensusAgent, checkpointer
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv(override=True)

# Global variables to store the agent and thread_id  
us_census_agent = None
thread_id = None


async def setup_graph():
    """Setup the USCensusAgent and workflow graph once at startup"""
    global us_census_agent, thread_id
    if us_census_agent is None:
        print("🔧 Setting up USCensusAgent...")
        thread_id = f"conversation_{uuid.uuid4()}"
        print(f"🧹 Starting fresh conversation: {thread_id}")
        us_census_agent = USCensusAgent()
        await us_census_agent.setup_graph()
        print("✅ USCensusAgent ready!")
    return us_census_agent.graph

EXAMPLES = [
    "Find me a good place to buy a house in West Virginia for my family of four with $120k income",
    "Compare Texas vs Florida for real estate",
    "Show me real estate data for California for a family with $150k income",
    "Which is better for real estate: Oregon or Washington?",
    "Find affordable housing in Texas for my family of four with $100k income"
]

async def agent_chat(message, history, request: gr.Request):
    """
    Simplified agent_chat function - just append the new message and let LangGraph handle the rest
    """
    global us_census_agent
    # Ensure workflow graph is setup
    print ("Calling setup graph here")
    graph = await setup_graph()
    
    # Simple: just add the new user message, let add_messages handle everything
    state = {"messages": [HumanMessage(content=message)]}
    config = {"configurable": {"thread_id": thread_id}}

    try:
        print(f"🚀 Invoking workflow with new message: {message}")
        
        result = await graph.ainvoke(state, config=config)
        # print (f'result after graph.ainvoke: {result}')
        print(f"✅ Workflow completed!")
        # print(f"🔑 Result keys: {list(result.keys())}")

        # Check if workflow completed (has final_result) or is interrupted (waiting for user input)
        if "final_result" in result:
            # Workflow completed successfully
            us_census_agent = None
            return str(result["final_result"])
        elif "__interrupt__" in result:
            # Workflow is interrupted and waiting for user input
            interrupt_payload = result["__interrupt__"][0].value
            return interrupt_payload.get("followup_question", "Please answer the follow-up question.")
        elif "followup_question" in result:
            return str(result["followup_question"])
        else:
            # Fallback
            report = result.get("result", "Sorry, I couldn't generate a report.")
            us_census_agent = None
            return str(report)
            
    except Exception as e:
        print(f"❌ Error type: {type(e).__name__}")
        print(f"❌ Error message: {e}")
        import traceback
        traceback.print_exc()
        return f"Sorry, I encountered an error: {str(e)}"

theme = gr.themes.Soft(
    primary_hue="green",
    secondary_hue="green",
    neutral_hue="gray",
    font=gr.themes.GoogleFont("Open Sans")
)

demo = gr.ChatInterface(
    fn=agent_chat,
    title="🏡 FamilyHomeFinder",
    description="Your Data-Driven Guide to the Best Places to Live—Compare States or Find Your Perfect County. Ask follow-up questions like 'Show me larger counties' or 'Filter out tiny counties' to customize your results.",
    examples=EXAMPLES,
    chatbot=gr.Chatbot(
        render_markdown=True,
        height=600,
        show_copy_button=True,
        latex_delimiters=[],
        type="messages"
    ),
    theme=theme,
    css=".examples-table {border-radius: 8px !important; border: 1px solid rgba(128, 128, 128, 0.2) !important; padding: 10px !important; margin: 10px 0 !important;} .examples-table button {background-color: #2c2c2c !important; border: 1px solid #404040 !important; border-radius: 4px !important; margin: 4px !important; padding: 8px 16px !important; box-shadow: 0 1px 3px rgba(0,0,0,0.12) !important;}"
)

if __name__ == "__main__":
    demo.launch()