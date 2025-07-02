#!/usr/bin/env python3
"""
Test script for the new workflow graph in build_graph.py
Tests both single-state and comparison real estate queries with ToolNode pattern.
"""

import asyncio
from langchain_core.messages import HumanMessage
from build_Graph import us_census_agent

async def test_new_workflow():
    """Test the new workflow with both single-state and comparison queries."""
    
    # Setup the agent and get the graph
    print("🔧 Setting up workflow graph...")
    await us_census_agent.setup_graph()
    graph = us_census_agent.graph
    
    # Configuration for checkpointer
    config1 = {"configurable": {"thread_id": "test_thread_1"}}
    config2 = {"configurable": {"thread_id": "test_thread_2"}}
    
    print("🏡 Testing New Real Estate Workflow with ToolNode Pattern")
    print("=" * 60)
    
    # Test 1: Single-state query (simpler to test first)
    print("\n--- TEST 1: Single-state query ---")
    test_state1 = {
        "messages": [HumanMessage(content="Show me real estate data for California")]
    }
    
    try:
        # First invocation - should stop at followup question
        print("Step 1: Initial query processing...")
        result1 = await graph.ainvoke(test_state1, config=config1)
        print(f"Followup question: {result1.get('followup_question', 'None')}")
        
        # Continue with a followup answer
        print("Step 2: Answering followup and continuing workflow...")
        followup_state = {
            "messages": [
                HumanMessage(content="Show me real estate data for California"),
                HumanMessage(content="Family of 4 with $150k income looking for good schools")
            ]
        }
        final_result1 = await graph.ainvoke(followup_state, config=config1)
        print("✅ Single-state query completed successfully")
        print(f"Final result length: {len(str(final_result1.get('final_result', '')))}")
        print(f"Tool output keys: {list(final_result1.get('tool_output', {}).keys()) if final_result1.get('tool_output') else 'None'}")
        
    except Exception as e:
        print(f"❌ Single-state query failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    
    # Test 2: Multi-state comparison query
    print("\n--- TEST 2: Multi-state comparison query ---")
    test_state2 = {
        "messages": [HumanMessage(content="Compare Texas vs Florida for real estate investment")]
    }
    
    try:
        # First invocation - should stop at followup question
        print("Step 1: Initial query processing...")
        result2 = await graph.ainvoke(test_state2, config=config2)
        print(f"Followup question: {result2.get('followup_question', 'None')}")
        
        # Continue with a followup answer
        print("Step 2: Answering followup and continuing workflow...")
        followup_state2 = {
            "messages": [
                HumanMessage(content="Compare Texas vs Florida for real estate investment"),
                HumanMessage(content="Family with $120k income, prefer lower cost of living")
            ]
        }
        final_result2 = await graph.ainvoke(followup_state2, config=config2)
        print("✅ Comparison query completed successfully")
        print(f"Final result length: {len(str(final_result2.get('final_result', '')))}")
        print(f"Tool output keys: {list(final_result2.get('tool_output', {}).keys()) if final_result2.get('tool_output') else 'None'}")
        
    except Exception as e:
        print(f"❌ Comparison query failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    
    # Test 3: Non-real estate query
    print("\n--- TEST 3: Non-real estate query ---")
    test_state3 = {
        "messages": [HumanMessage(content="What's the weather like today?")]
    }
    
    try:
        result3 = await graph.ainvoke(test_state3, config={"configurable": {"thread_id": "test_thread_3"}})
        print("✅ Non-real estate query completed successfully")
        print(f"Response: {result3.get('final_result', 'No final result found')[:200]}...")
        
    except Exception as e:
        print(f"❌ Non-real estate query failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🏁 Testing completed!")

if __name__ == "__main__":
    print("Starting new workflow tests with ToolNode pattern...")
    asyncio.run(test_new_workflow()) 