import gradio as gr
import asyncio
import os
from dotenv import load_dotenv
from build_Graph import us_census_agent, checkpointer, new_workflow_graph
from langchain_core.messages import HumanMessage, AIMessage
# Removed unused import: tools_condition

load_dotenv(override=True)

EXAMPLES = [
    "Find me a good place to buy a house in West Virginia for my family of four with $120k income",
    "Compare Texas vs Florida for real estate",
    "Show me real estate data for California for a family with $150k income",
    "Which is better for real estate: Oregon or Washington?",
    "Find affordable housing in Texas for my family of four with $100k income"
]

async def agent_chat(message, history, request: gr.Request):
    thread_id = "default"
    state = {"messages": []}
    for entry in history:
        if isinstance(entry, (list, tuple)) and len(entry) == 2:
            human, ai = entry
            if human:
                state["messages"].append(HumanMessage(content=human))
            if ai:
                state["messages"].append(AIMessage(content=ai))
        elif isinstance(entry, dict):
            if entry.get('role') == 'user':
                state["messages"].append(HumanMessage(content=entry.get('content', '')))
            elif entry.get('role') == 'assistant':
                state["messages"].append(AIMessage(content=entry.get('content', '')))
    state["messages"].append(HumanMessage(content=message))

    try:
        config = {"configurable": {"thread_id": thread_id}}
        saved_state = checkpointer.get(config)
        if saved_state and saved_state.get("values"):
            from langgraph.types import Command
            resume_state = saved_state["values"].copy()
            resume_state["messages"].append(HumanMessage(content=message))
            resume_state["tool_output"] = None
            result = await new_workflow_graph.ainvoke(
                Command(resume=resume_state),
                config=config
            )
        else:
            result = await new_workflow_graph.ainvoke(
                state,
                config=config
            )
        if "__interrupt__" in result:
            interrupt_payload = result["__interrupt__"][0].value
            return interrupt_payload.get("followup_question", "Please answer the follow-up question.")
        elif "followup_question" in result:
            return str(result["followup_question"])
        else:
            report = result.get("final_result", result.get("result", "Sorry, I couldn't generate a report."))
            
            # Note: LangGraph handles state management automatically
            # Manual state reset is generally not needed and can cause API issues
            if "final_result" in result:
                print("🔄 Query completed - LangGraph will handle state transitions automatically")
            
            return str(report)
    except Exception as e:
        print(f"Error in agent_chat: {e}")
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