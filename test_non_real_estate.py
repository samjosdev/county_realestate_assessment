#!/usr/bin/env python3
"""
Test script for non-real estate queries to ensure graceful handling
"""

import asyncio
from langchain_core.messages import HumanMessage
from build_Graph import us_census_agent

async def test_non_real_estate_queries():
    """Test queries that are not about real estate."""
    
    print("🔧 Setting up USCensusAgent...")
    workflow_graph = await us_census_agent.setup_graph()
    print("Starting non-real estate query tests...")
    print("🔧 Testing Non-Real Estate Query Handling")
    print("=" * 60)
    
    # Test 1: Weather query
    print("\n--- TEST 1: Weather query ---")
    config1 = {"configurable": {"thread_id": "test_weather"}}
    
    weather_state = {
        "messages": [HumanMessage(content="What's the weather like today?")]
    }
    
    try:
        result1 = await workflow_graph.ainvoke(weather_state, config=config1)
        print("✅ Weather query handled gracefully")
        print(f"Response: {result1.get('final_result', 'No response')}")
    except Exception as e:
        print(f"❌ Weather query failed: {e}")
    
    print("\n" + "=" * 60)
    
    # Test 2: General greeting
    print("\n--- TEST 2: General greeting ---")
    config2 = {"configurable": {"thread_id": "test_greeting"}}
    
    greeting_state = {
        "messages": [HumanMessage(content="Hello, how are you?")]
    }
    
    try:
        result2 = await workflow_graph.ainvoke(greeting_state, config=config2)
        print("✅ Greeting handled gracefully")
        print(f"Response: {result2.get('final_result', 'No response')}")
    except Exception as e:
        print(f"❌ Greeting failed: {e}")
    
    print("\n" + "=" * 60)
    
    # Test 3: Cooking question
    print("\n--- TEST 3: Cooking question ---")
    config3 = {"configurable": {"thread_id": "test_cooking"}}
    
    cooking_state = {
        "messages": [HumanMessage(content="How do I bake a chocolate cake?")]
    }
    
    try:
        result3 = await workflow_graph.ainvoke(cooking_state, config=config3)
        print("✅ Cooking query handled gracefully")
        print(f"Response: {result3.get('final_result', 'No response')}")
    except Exception as e:
        print(f"❌ Cooking query failed: {e}")
    
    print("\n" + "=" * 60)
    
    # Test 4: Valid real estate query (should still work)
    print("\n--- TEST 4: Valid real estate query ---")
    config4 = {"configurable": {"thread_id": "test_real_estate"}}
    
    real_estate_state = {
        "messages": [HumanMessage(content="Show me real estate data for Texas")]
    }
    
    try:
        result4 = await workflow_graph.ainvoke(real_estate_state, config=config4)
        print("✅ Real estate query processed successfully")
        print(f"Result type: {type(result4.get('final_result', 'No result'))}")
        print("Note: This should interrupt for followup, which is expected behavior")
    except Exception as e:
        print(f"❌ Real estate query failed: {e}")
    
    print("\n" + "=" * 60)
    print("🏁 Non-real estate testing completed!")

if __name__ == "__main__":
    asyncio.run(test_non_real_estate_queries()) 