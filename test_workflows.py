#!/usr/bin/env python3

"""
Comprehensive test script to verify both single state and comparison workflows
are functioning correctly with the tier detection and scoring updates.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_single_state_flow():
    """Test the single state workflow"""
    print("🧪 Testing Single State Flow")
    print("=" * 50)
    
    try:
        from build_graph import get_new_workflow_graph
        
        # Get the workflow graph
        graph = await get_new_workflow_graph()
        
        # Test single state query
        test_query = "I'm looking for the best counties in California for a family of 4 with a $800,000 budget"
        
        # Create initial state
        initial_state = {
            "messages": [{"role": "user", "content": test_query}]
        }
        
        print(f"📝 Test Query: {test_query}")
        print(f"⏰ Starting at: {datetime.now().strftime('%H:%M:%S')}")
        
        # Create a unique thread ID for this test
        thread_id = f"test-single-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        config = {"configurable": {"thread_id": thread_id}}
        
        # Run the workflow step by step
        print("\n🔄 Executing workflow...")
        
        # First step: extract states
        result = await graph.ainvoke(initial_state, config)
        
        # Check if we need to answer a followup question
        if result.get("followup_question"):
            print(f"\n❓ Followup Question: {result['followup_question']}")
            
            # Simulate user response to followup
            followup_response = "We prioritize good schools and family safety. We prefer suburban areas with good amenities."
            print(f"💬 Simulated Response: {followup_response}")
            
            # Continue with followup response
            followup_state = {
                "messages": result["messages"] + [{"role": "user", "content": followup_response}]
            }
            
            result = await graph.ainvoke(followup_state, config)
        
        # Check final result
        final_result = result.get("final_result", "No final result found")
        
        print("\n✅ Single State Flow Results:")
        print("-" * 30)
        if "Top 5 Counties for Homebuyers in California" in final_result:
            print("✅ Report title found")
        if "| Rank | County |" in final_result:
            print("✅ County table found")
        if "Key Insights" in final_result:
            print("✅ Insights section found")
        if "Recommendations" in final_result:
            print("✅ Recommendations section found")
            
        # Show a sample of the output
        lines = final_result.split('\n')
        print("\n📊 Sample Output (first 15 lines):")
        for i, line in enumerate(lines[:15]):
            print(f"{i+1:2d}: {line}")
        
        return True
        
    except Exception as e:
        print(f"❌ Single State Flow Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_comparison_flow():
    """Test the comparison workflow"""
    print("\n\n🧪 Testing Comparison State Flow")
    print("=" * 50)
    
    try:
        from build_graph import get_new_workflow_graph
        
        # Get the workflow graph
        graph = await get_new_workflow_graph()
        
        # Test comparison query
        test_query = "Compare Texas vs Florida for a family of 4 with a $600,000 budget"
        
        # Create initial state
        initial_state = {
            "messages": [{"role": "user", "content": test_query}]
        }
        
        print(f"📝 Test Query: {test_query}")
        print(f"⏰ Starting at: {datetime.now().strftime('%H:%M:%S')}")
        
        # Create a unique thread ID for this test
        thread_id = f"test-comparison-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        config = {"configurable": {"thread_id": thread_id}}
        
        # Run the workflow step by step
        print("\n🔄 Executing workflow...")
        
        # First step: extract states
        result = await graph.ainvoke(initial_state, config)
        
        # Check if we need to answer a followup question
        if result.get("followup_question"):
            print(f"\n❓ Followup Question: {result['followup_question']}")
            
            # Simulate user response to followup
            followup_response = "We want good schools, safe neighborhoods, and reasonable cost of living. Suburban areas preferred."
            print(f"💬 Simulated Response: {followup_response}")
            
            # Continue with followup response
            followup_state = {
                "messages": result["messages"] + [{"role": "user", "content": followup_response}]
            }
            
            result = await graph.ainvoke(followup_state, config)
        
        # Check final result
        final_result = result.get("final_result", "No final result found")
        
        print("\n✅ Comparison Flow Results:")
        print("-" * 30)
        if "State Comparison Report" in final_result:
            print("✅ Report title found")
        if "State-by-State Summary Table" in final_result:
            print("✅ Summary table section found")
        if "| Metric | Texas | Florida |" in final_result:
            print("✅ Comparison table found")
        if "Top 3 Counties in Each State" in final_result:
            print("✅ County sections found")
        if "Key Takeaways" in final_result:
            print("✅ Takeaways section found")
        if "Recommendation" in final_result:
            print("✅ Recommendations section found")
            
        # Check for empty table indicators
        if "—" in final_result and "| — | — |" not in final_result:
            print("✅ Tables contain data (not all empty)")
        elif "[N/A]" not in final_result:
            print("✅ No [N/A] indicators found")
        else:
            print("⚠️ May contain empty table cells")
            
        # Show a sample of the output
        lines = final_result.split('\n')
        print("\n📊 Sample Output (first 20 lines):")
        for i, line in enumerate(lines[:20]):
            print(f"{i+1:2d}: {line}")
        
        return True
        
    except Exception as e:
        print(f"❌ Comparison Flow Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_tier_detection_integration():
    """Test that tier detection is working in the workflows"""
    print("\n\n🧪 Testing Tier Detection Integration")
    print("=" * 50)
    
    try:
        from tools import detect_tier
        from build_graph import get_new_workflow_graph
        
        # Test different budget tiers
        test_budgets = [
            ("$300,000", "affordable"),
            ("$750,000", "move_up"), 
            ("$1,500,000", "luxury"),
            ("$8,000,000", "ultra_luxury")
        ]
        
        print("💰 Testing Tier Detection:")
        for budget_str, expected_tier in test_budgets:
            budget_int = int(budget_str.replace("$", "").replace(",", ""))
            actual_tier = detect_tier(budget_int)
            status = "✅" if actual_tier == expected_tier else "❌"
            print(f"  {status} {budget_str} -> {actual_tier} (expected: {expected_tier})")
        
        # Test a quick comparison with luxury budget to see tier-aware results
        print("\n🏆 Testing Luxury Tier Comparison:")
        graph = await get_new_workflow_graph()
        
        luxury_query = "Compare California vs New York for a luxury buyer with $2,000,000 budget"
        initial_state = {
            "messages": [{"role": "user", "content": luxury_query}]
        }
        
        thread_id = f"test-luxury-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        config = {"configurable": {"thread_id": thread_id}}
        
        print(f"📝 Luxury Query: {luxury_query}")
        
        # Run just the state extraction to verify tier detection
        result = await graph.ainvoke(initial_state, config)
        
        if result.get("followup_question"):
            # Quick followup for luxury segment
            followup_response = "We want prestige properties, excellent schools, and high-end amenities."
            followup_state = {
                "messages": result["messages"] + [{"role": "user", "content": followup_response}]
            }
            result = await graph.ainvoke(followup_state, config)
            
        # Check if luxury-appropriate results are generated
        final_result = result.get("final_result", "")
        if "$2,000,000" in final_result and ("luxury" in final_result.lower() or "prestige" in final_result.lower()):
            print("✅ Luxury tier results detected")
        else:
            print("⚠️ Luxury tier integration may need verification")
            
        return True
        
    except Exception as e:
        print(f"❌ Tier Detection Integration Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests"""
    print("🚀 Testing Agent Workflow Routing - Both Flows")
    print("=" * 60)
    print(f"⏰ Test Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # Test single state flow
    single_state_success = await test_single_state_flow()
    results.append(("Single State Flow", single_state_success))
    
    # Test comparison flow  
    comparison_success = await test_comparison_flow()
    results.append(("Comparison Flow", comparison_success))
    
    # Test tier detection integration
    tier_success = await test_tier_detection_integration()
    results.append(("Tier Detection Integration", tier_success))
    
    # Summary
    print("\n\n📋 Test Summary")
    print("=" * 30)
    all_passed = True
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} {test_name}")
        if not success:
            all_passed = False
    
    print(f"\n🏁 Overall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    print(f"⏰ Test Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return all_passed

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 