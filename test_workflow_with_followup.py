#!/usr/bin/env python3
"""
Comprehensive test script for the new workflow with followup handling.
Tests the complete flow including followup responses.
"""

import asyncio
from langchain_core.messages import HumanMessage
from build_Graph import new_workflow_graph

async def test_complete_workflow():
    """Test the complete workflow including followup responses."""
    
    print("🏡 Testing Complete Real Estate Workflow with Followup")
    print("=" * 60)
    
    # Test 1: Texas vs Florida comparison with followup
    print("\n--- TEST 1: Texas vs Florida Comparison (Complete Flow) ---")
    config1 = {"configurable": {"thread_id": "test_complete_1"}}
    
    # Initial query
    initial_state = {
        "messages": [HumanMessage(content="Compare Texas vs Florida for real estate for a family of four with $120k income")]
    }
    
    try:
        # Step 1: Initial query - should interrupt for followup
        print("Step 1: Processing initial query...")
        result1 = await new_workflow_graph.ainvoke(initial_state, config=config1)
        print(f"✅ Workflow interrupted for followup: {result1.get('followup_question', 'No followup question')}")
        
        # Step 2: Provide followup response and continue
        print("\nStep 2: Providing followup response...")
        followup_state = {
            "messages": [
                HumanMessage(content="Compare Texas vs Florida for real estate for a family of four with $120k income"),
                HumanMessage(content="I'm looking for suburban areas with good schools and family amenities")
            ]
        }
        
        result2 = await new_workflow_graph.ainvoke(followup_state, config=config1)
        print("✅ Comparison analysis completed!")
        print(f"Final report length: {len(str(result2.get('final_result', '')))} characters")
        
        # Print first 500 characters of the report
        final_result = result2.get('final_result', 'No final result')
        if final_result and final_result != 'No final result':
            print(f"\nReport preview:\n{final_result[:500]}{'...' if len(final_result) > 500 else ''}")
        
    except Exception as e:
        print(f"❌ Texas vs Florida test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    
    # Test 2: California single-state with followup
    print("\n--- TEST 2: California Single-State (Complete Flow) ---")
    config2 = {"configurable": {"thread_id": "test_complete_2"}}
    
    try:
        # Step 1: Initial query - should interrupt for followup
        print("Step 1: Processing initial California query...")
        initial_state2 = {
            "messages": [HumanMessage(content="Show me real estate data for California for a family with $150k income")]
        }
        
        result3 = await new_workflow_graph.ainvoke(initial_state2, config=config2)
        print(f"✅ Workflow interrupted for followup: {result3.get('followup_question', 'No followup question')}")
        
        # Step 2: Provide followup response and continue
        print("\nStep 2: Providing followup response...")
        followup_state2 = {
            "messages": [
                HumanMessage(content="Show me real estate data for California for a family with $150k income"),
                HumanMessage(content="I prefer coastal areas with tech job opportunities")
            ]
        }
        
        result4 = await new_workflow_graph.ainvoke(followup_state2, config=config2)
        print("✅ Single-state analysis completed!")
        print(f"Final report length: {len(str(result4.get('final_result', '')))} characters")
        
        # Print first 500 characters of the report
        final_result2 = result4.get('final_result', 'No final result')
        if final_result2 and final_result2 != 'No final result':
            print(f"\nReport preview:\n{final_result2[:500]}{'...' if len(final_result2) > 500 else ''}")
            
    except Exception as e:
        print(f"❌ California test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🏁 Complete workflow testing finished!")

if __name__ == "__main__":
    print("Starting complete workflow tests with followup handling...")
    asyncio.run(test_complete_workflow()) 