import sys
from build_graph import USCensusAgent
import asyncio

async def run_agent_workflow(query: str):
    state = {"messages": []}
    from langchain_core.messages import HumanMessage
    state["messages"].append(HumanMessage(content=query))
    agent = USCensusAgent()
    await agent.setup_graph()
    result = await agent.graph.ainvoke(state)
    report = result.get("final_result", "Sorry, I couldn't generate a report.")
    print("\n=== USCensusAgent Report ===\n")
    print(report)
    print("\n==========================\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python cli_app.py 'Your query here'")
        sys.exit(1)
    query = sys.argv[1]
    asyncio.run(run_agent_workflow(query)) 