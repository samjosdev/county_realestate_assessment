import asyncio
import os
from typing import TypedDict, Annotated, List, Optional, Any
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, AIMessage
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from datetime import datetime
from models import get_supervisor_llm, get_formatter_llm
from prompts import (
    SINGLE_STATE_INSIGHTS_PROMPT,
    COMPARISON_INSIGHTS_PROMPT,
    SINGLE_STATE_TOOL_CALL_PROMPT,
    COMPARISON_TOOL_CALL_PROMPT,
)
# Import from new modular structure
from tools import real_estate_investment_tool
from scoring.filtering import process_counties_with_tagging
from utils.data_processing import extract_tool_results_from_messages
from scoring.county_scoring import detect_tier, calculate_state_medians
from utils.user_preferences import parse_user_priority
from langgraph.prebuilt import tools_condition, ToolNode
from html_formatting import format_single_state_html_report, format_comparison_html_report

# Create a checkpointer for state persistence
checkpointer = MemorySaver()

# Simplified state
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    tool_output: Optional[dict]
    is_comparison: Optional[bool]
    summary: Optional[str]
    insights: Optional[str]
    final_result: Optional[str]
    followup_question: Optional[str]
    needs_followup: Optional[bool]
    states: Optional[list]
    route: Optional[str]  # Used for routing: "non_real_estate", "comparison", "single_state"
    user_preferences: Optional[str]  # Store user's answers to followup questions
    income: Optional[str]  # Store extracted or provided income information
    extracted_preferences: Optional[dict]  # Store structured preferences from LLM analysis

class USCensusAgent(BaseModel):
    graph: Any = Field(default=None, init=False)
    formatter_llm: Any = Field(default=None, init=False)
    formatter_llm_with_tools: Any = Field(default=None, init=False)
    supervisor_llm: Any = Field(default=None, init=False)
    supervisor_llm_with_tools: Any = Field(default=None, init=False)
    tools: Any = Field(default=None, init=False)
    single_state_tool_node: Any = Field(default=None, init=False)
    comparison_tool_node: Any = Field(default=None, init=False)
    needs_followup: Any = Field(default=None, init=False)

    class Config:
        arbitrary_types_allowed = True

    async def setup_graph(self):
        """
        Setup function that initializes LLMs, binds them with tools, and builds the graph.
        
        Returns:
            Compiled graph ready for execution
        """
        # Initialize LLMs
        self.supervisor_llm = get_supervisor_llm()
        self.formatter_llm = get_formatter_llm()
        self.tools = [real_estate_investment_tool]
        self.needs_followup = True
        
        # Bind tools to LLMs for tool calling
        self.supervisor_llm_with_tools = self.supervisor_llm.bind_tools(self.tools)
        self.formatter_llm_with_tools = self.formatter_llm.bind_tools(self.tools)
        
        # Build the graph
        self.graph = await self.build_graph()
        return self.graph

    # --- New Workflow Nodes as staticmethods ---
    def simple_routing_node(self, state):
        """Simple routing based on form data - no NLP needed"""
        # Get states from the pre-populated state (set by form interface)
        states = state.get("states", [])
        
        if not states:
            raise ValueError("States must be provided in form interface")
        
        # Determine if this is a comparison (more than one state)
        is_comparison = len(states) > 1
        route = "comparison" if is_comparison else "single_state"
        
        return {
            **state,
            "is_comparison": is_comparison,
            "route": route
        }

    def single_state_county_lookup(self, state):
        """County lookup node for single state flow - LLM generates tool call"""
        state_info = state["states"][0]
        prompt = SINGLE_STATE_TOOL_CALL_PROMPT.format(
            state_info=state_info,
            state_name=state_info["state_name"],
            state_fips=state_info["fips_code"]
        )
        
        # LLM generates tool call
        response = self.supervisor_llm_with_tools.invoke([{"role": "user", "content": prompt}])
        
        # Add the AI message with tool calls to state
        result = {
            **state,
            "messages": state.get("messages", []) + [response]
        }
        
        return result

    def comparison_county_lookup(self, state):
        """County lookup node for comparison flow - LLM generates tool calls"""
        state1, state2 = state["states"][:2]
        prompt = COMPARISON_TOOL_CALL_PROMPT.format(
            state1_info=state1,
            state1_name=state1["state_name"],
            state1_fips=state1["fips_code"],
            state2_info=state2,
            state2_name=state2["state_name"],
            state2_fips=state2["fips_code"]
        )
        
        # LLM generates tool calls
        response = self.supervisor_llm_with_tools.invoke([{"role": "user", "content": prompt}])
        
        # Add the AI message with tool calls to state
        return {
            **state,
            "messages": state.get("messages", []) + [response]
        }

    def summarize_single_state(self, state):
        """Summarize single state results using tagging and sorting"""
        # Extract tool results from messages
        messages = state.get("messages", [])
        tool_output = extract_tool_results_from_messages(messages)
        
        state_info = state["states"][0]
        state_name = state_info["state_name"]
        
        # Handle case where tool_output might be a list
        if isinstance(tool_output, list):
            counties = tool_output
        else:
            counties = tool_output.get("data", {}).get(state_name, {}).get("data", [])
        
        # Process counties with tagging system using function from tools.py
        user_preferences = state.get("user_preferences", "")
        user_budget = int(state.get("income", "150000"))
        user_priority = parse_user_priority(user_preferences)
        state_medians = calculate_state_medians(counties)
        
        processed_counties = process_counties_with_tagging(
            counties, user_priority, state_medians, user_budget, state_name
        )
        
        # Update tool_output with processed counties
        if processed_counties:
            tool_output["data"][state_name]["data"] = processed_counties
            summary = f"Top 5 counties in {state_name}: " + ", ".join([c["name"] for c in processed_counties[:5]])
        else:
            summary = f"No counties found in {state_name}"
        
        return {**state, "summary": summary, "tool_output": tool_output}
    
    def insights_single_state(self, state):
        summary = state.get("summary", "")
        tool_output = state.get("tool_output", {})
        state_info = state["states"][0]
        state_name = state_info["state_name"]
        income = state.get("income", "150000")
        user_preferences = state.get("user_preferences", "No specific preferences provided")
        
        # Add tier information
        user_budget = int(income)
        tier = detect_tier(user_budget)
        tier_descriptions = {
            "affordable": "affordable housing",
            "move_up": "move-up buyer segment", 
            "luxury": "luxury home market",
            "ultra_luxury": "ultra-luxury estate market"
        }
        tier_description = tier_descriptions.get(tier, "housing market")
        
        try:
            chain = SINGLE_STATE_INSIGHTS_PROMPT | self.formatter_llm
            response = chain.invoke({
                "state_name": state_name,
                "summary": summary,
                "tool_output": str(tool_output),
                "income": income,
                "user_preferences": f"{user_preferences} (Budget tier: {tier_description})"
            })
            
            # Parse response using the new format (INSIGHTS: and RECOMMENDATION:)
            content = response.content if hasattr(response, 'content') else str(response)
            
            insights = ""
            recommendation = ""
            
            if "INSIGHTS:" in content and "RECOMMENDATION:" in content:
                parts = content.split("RECOMMENDATION:")
                insights = parts[0].replace("INSIGHTS:", "").strip()
                recommendation = parts[1].strip()
            elif "INSIGHTS:" in content:
                insights = content.replace("INSIGHTS:", "").strip()
                recommendation = f"Consider exploring the top counties in {state_name} that match your criteria for family-friendly communities and investment potential."
            else:
                # Fallback: use entire content as insights
                insights = content.strip()
                recommendation = f"Based on this analysis, focus your search on the top-ranked counties in {state_name} for the best combination of value and family amenities."
                
        except Exception as e:
            insights = f"Based on your ${income} income and family priorities, {state_name} offers excellent opportunities in the identified counties. Your budget positions you well in the {tier_description} tier, giving you access to quality family neighborhoods with good schools and amenities."
            recommendation = f"Focus your search on the top 3 counties identified in this analysis. These areas offer the best combination of affordability, family amenities, and investment potential for your ${income} budget. Consider visiting these communities to experience the local schools and neighborhood character firsthand."
        
        return {**state, "insights": insights, "recommendation": recommendation}

    def assemble_single_state(self, state):
        insights = state.get("insights", "")
        recommendation = state.get("recommendation", "")
        tool_output = state.get("tool_output", {})
        state_info = state["states"][0]
        state_name = state_info["state_name"]
        income_raw = state.get("income", "150000")
        # Format income for display (add commas)
        income = f"{int(income_raw):,}" if str(income_raw).isdigit() else income_raw
        counties = tool_output.get("data", {}).get(state_name, {}).get("data", [])

        # Use HTML formatting function
        final_report = format_single_state_html_report(
            state_name=state_name,
            income=income,
            counties=counties,
            insights=insights,
            recommendation=recommendation
        )

        # Reset state flags for next query
        result = {
            "messages": state.get("messages", []),
            "final_result": final_report
        }

        return result

    def summarize_comparison(self, state):
        """Summarize comparison results using tagging and sorting"""
        # Extract tool results from messages
        messages = state.get("messages", [])
        tool_output = extract_tool_results_from_messages(messages)
        
        state1, state2 = state["states"][:2]
        name1, name2 = state1["state_name"], state2["state_name"]
        counties1 = tool_output.get("state1", {}).get("data", {}).get(name1, {}).get("data", [])
        counties2 = tool_output.get("state2", {}).get("data", {}).get(name2, {}).get("data", [])
        
        # Process counties for both states using function from tools.py
        user_preferences = state.get("user_preferences", "")
        user_budget = int(state.get("income", "150000"))
        user_priority = parse_user_priority(user_preferences)
        
        # Calculate state medians for each state separately
        state_medians1 = calculate_state_medians(counties1) if counties1 else {}
        state_medians2 = calculate_state_medians(counties2) if counties2 else {}
        
        processed_counties1 = process_counties_with_tagging(
            counties1, user_priority, state_medians1, user_budget, name1
        )
        processed_counties2 = process_counties_with_tagging(
            counties2, user_priority, state_medians2, user_budget, name2
        )

        # Update tool_output
        if processed_counties1:
            tool_output["state1"]["data"][name1]["data"] = processed_counties1
        if processed_counties2:
            tool_output["state2"]["data"][name2]["data"] = processed_counties2

        # Generate summary
        counties1_names = [c.get("name", "Unknown County") for c in processed_counties1[:3]] if processed_counties1 else ["No data available"]
        counties2_names = [c.get("name", "Unknown County") for c in processed_counties2[:3]] if processed_counties2 else ["No data available"]
        
        summary = f"Top 3 counties in {name1}: " + ", ".join(counties1_names)
        summary += f" | Top 3 counties in {name2}: " + ", ".join(counties2_names)
        
        return {**state, "summary": summary, "tool_output": tool_output}

    def insights_comparison(self, state):
        summary = state.get("summary", "")
        tool_output = state.get("tool_output", {})
        state1, state2 = state["states"][:2]
        name1, name2 = state1["state_name"], state2["state_name"]
        income = state.get("income", "150000")
        user_preferences = state.get("user_preferences", "No specific preferences provided")
        
        # Add tier information
        user_budget = int(income)
        tier = detect_tier(user_budget)
        tier_descriptions = {
            "affordable": "affordable housing",
            "move_up": "move-up buyer segment", 
            "luxury": "luxury home market",
            "ultra_luxury": "ultra-luxury estate market"
        }
        tier_description = tier_descriptions.get(tier, "housing market")
        
        try:
            chain = COMPARISON_INSIGHTS_PROMPT | self.formatter_llm
            response = chain.invoke({
                "state1": name1,
                "state2": name2,
                "summary": summary,
                "tool_output": str(tool_output),
                "income": income,
                "user_preferences": f"{user_preferences} (Budget tier: {tier_description})"
            })
            
            # Parse response (simple split)
            content = response.content if hasattr(response, 'content') else str(response)
            takeaways, recommendation = "", ""
            if "Recommendation:" in content:
                parts = content.split("Recommendation:")
                takeaways = parts[0].replace("Takeaways:", "").strip()
                recommendation = parts[1].strip()
            else:
                takeaways = content.strip()
                
        except Exception as e:
            takeaways = f"Comparing {name1} and {name2} for your ${income} budget and family needs."
            recommendation = f"Both states offer unique advantages. Consider visiting the top counties in each state to find the best fit for your family."
            
        return {**state, "insights": takeaways, "recommendation": recommendation}

    def assemble_comparison(self, state):
        insights = state.get("insights", "")
        recommendation = state.get("recommendation", "")
        tool_output = state.get("tool_output", {})
        state1, state2 = state["states"][:2]
        name1, name2 = state1["state_name"], state2["state_name"]
        income_raw = state.get("income", "150000")
        # Format income for display (add commas)
        income = f"{int(income_raw):,}" if str(income_raw).isdigit() else income_raw
        counties1 = tool_output.get("state1", {}).get("data", {}).get(name1, {}).get("data", [])
        counties2 = tool_output.get("state2", {}).get("data", {}).get(name2, {}).get("data", [])

        # Use HTML formatting function
        final_report = format_comparison_html_report(
            name1=name1,
            name2=name2,
            income=income,
            counties1=counties1,
            counties2=counties2,
            insights=insights,
            recommendation=recommendation
        )

        # Reset state flags for next query
        return {
            "messages": state.get("messages", []),
            "final_result": final_report
        }

    async def build_graph(self):
        """Builds the LangGraph workflow."""
        graph = StateGraph(AgentState)
        
        # Create a single ToolNode for executing tools
        tool_node = ToolNode(self.tools)

        # Add all nodes to the graph
        graph.add_node("simple_routing", self.simple_routing_node)
        graph.add_node("single_state_county_lookup", self.single_state_county_lookup)
        graph.add_node("comparison_county_lookup", self.comparison_county_lookup)
        graph.add_node("tools", tool_node)
        graph.add_node("summarize_single_state", self.summarize_single_state)
        graph.add_node("insights_single_state", self.insights_single_state)
        graph.add_node("assemble_single_state", self.assemble_single_state)
        graph.add_node("summarize_comparison", self.summarize_comparison)
        graph.add_node("insights_comparison", self.insights_comparison)
        graph.add_node("assemble_comparison", self.assemble_comparison)
        
        # Entry point
        graph.set_entry_point("simple_routing")
        
        # Simple routing from entry point
        graph.add_conditional_edges(
            "simple_routing",
            lambda state: state.get("route", "single_state"),
            {
                "single_state": "single_state_county_lookup",
                "comparison": "comparison_county_lookup"
            }
        )
        
        # County lookup to tools using tools_condition from langgraph.prebuilt
        graph.add_conditional_edges(
            "single_state_county_lookup",
            tools_condition,
            {
                "tools": "tools",
                END: END
            }
        )
        
        graph.add_conditional_edges(
            "comparison_county_lookup",
            tools_condition,
            {
                "tools": "tools",
                END: END
            }
        )

        # Tool execution routing
        def route_after_tools(state):
            is_comparison = state.get("is_comparison", False)
            route = "comparison" if is_comparison else "single_state"
            return route
            
        graph.add_conditional_edges(
            "tools",
            route_after_tools,
            {
                "single_state": "summarize_single_state",
                "comparison": "summarize_comparison"
            }
        )

        # Single state flow
        graph.add_edge("summarize_single_state", "insights_single_state")
        graph.add_edge("insights_single_state", "assemble_single_state")

        # Comparison flow
        graph.add_edge("summarize_comparison", "insights_comparison")
        graph.add_edge("insights_comparison", "assemble_comparison")
        
        # End points
        graph.add_edge("assemble_single_state", END)
        graph.add_edge("assemble_comparison", END)
        
        return graph.compile(checkpointer=checkpointer)