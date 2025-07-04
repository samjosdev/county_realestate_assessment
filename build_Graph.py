import asyncio
from typing import TypedDict, Annotated, List, Optional, Any
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, AIMessage
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt
from datetime import datetime
from models import get_supervisor_llm, get_formatter_llm
from prompts import (
    FOLLOWUP_QUESTIONS_PROMPT,
    MULTI_STATE_FIPS_EXTRACTION_PROMPT,
    SINGLE_STATE_INSIGHTS_PROMPT,
    COMPARISON_INSIGHTS_PROMPT,
    FIPS_CONTEXT,
    NON_REAL_ESTATE_RESPONSE,
    SINGLE_STATE_TOOL_CALL_PROMPT,
    COMPARISON_TOOL_CALL_PROMPT,
    PARSE_FOUR_FACTORS_PROMPT
)
from langchain_core.output_parsers import JsonOutputParser
from tools import real_estate_investment_tool, process_counties_with_tagging, extract_tool_results_from_messages, detect_tier, parse_user_priority, calculate_state_medians
from langgraph.prebuilt import tools_condition, ToolNode
from langchain.prompts import PromptTemplate
from formatting import format_single_state_report, format_comparison_report

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
        print("🔧 Setting up USCensusAgent...")
        
        # Initialize LLMs
        self.supervisor_llm = get_supervisor_llm()
        self.formatter_llm = get_formatter_llm()
        self.tools = [real_estate_investment_tool]
        self.needs_followup = True
        print (f'self.needs_followup: {self.needs_followup}')
        # Bind tools to LLMs for tool calling
        self.supervisor_llm_with_tools = self.supervisor_llm.bind_tools(self.tools)
        self.formatter_llm_with_tools = self.formatter_llm.bind_tools(self.tools)
        
        print("✅ Initialization complete!")
        
        # Build the graph
        self.graph = await self.build_graph()
        print("✅ USCensusAgent setup complete!")
        return self.graph

    # --- New Workflow Nodes as staticmethods ---
    def extract_states_and_flag(self, state):
        print("🔄 Executing: extract_states_and_flag node")
        print (f'Inside extract_states_and_flag:state["needs_followup"]: {state.get("needs_followup")}')
        # If states are already populated, skip extraction but ensure proper routing
        existing_states = state.get("states")
        if existing_states:
            print(f"✅ States already extracted: {existing_states}, skipping re-extraction")
            # Determine route based on existing states
            is_comparison = len(existing_states) > 1
            return {
                **state,
                "is_comparison": is_comparison,
                "route": "continue"  # Always continue to followup_question for proper routing
            }
        # Extract states from the first message (original query)
        messages = state.get("messages", [])
        if not messages:
            raise ValueError("Messages to extract states from not found!")
        user_query = messages[0].content
        
        try:
            multi_state_prompt = PromptTemplate(
                input_variables=["query", "context"],
                template=MULTI_STATE_FIPS_EXTRACTION_PROMPT
            )
            chain = multi_state_prompt | self.supervisor_llm | JsonOutputParser()
            result = chain.invoke({"query": user_query, "context": FIPS_CONTEXT})
            states = result.get("states", [])
            if not states:
                print(f"⚠️ No states found in query - routing to non-real estate handler")
                return {
                    **state,
                    "route": "non_real_estate",
                    "states": [],
                    "is_comparison": False
                }
            is_comparison = len(states) > 1
        except Exception as e:
            print(f"❌ Error in state extraction: {e} - routing to non-real estate handler")
            return {
                **state,
                "route": "non_real_estate", 
                "states": [],
                "is_comparison": False
            }
        print(f"✅ Completed: extract_states_and_flag -> {states} (is_comparison={is_comparison})")
        return {
            **state,
            "states": states,
            "is_comparison": is_comparison,
        }

    def ask_followup_question(self, state):
        print("🔄 Executing: ask_followup_question")
        messages = state.get("messages", [])
        # If we have more than one message, user has answered the followup
        print (f'Inside Followup Question:state["needs_followup"]: {state.get("needs_followup")}')
        if self.needs_followup ==True:
            # Use the original query (first message) for generating followup questions
            user_query = messages[0].content if messages else ""
            questions_chain = FOLLOWUP_QUESTIONS_PROMPT | self.supervisor_llm
            result = questions_chain.invoke({"user_query": user_query})
            question_text = result.content if hasattr(result, 'content') else str(result)
            print("✅ Completed: ask_followup_question -> interrupting")
            self.needs_followup = False
            return interrupt({**state, "followup_question": question_text, "needs_followup": self.needs_followup})
        print("[DEBUG] User has answered followup, proceeding to routing.")
        self.needs_followup ==False
        # Step 2: LLM parses both queries to populate 4 factors
        user_response = messages[-1].content if len(messages) > 1 else ""
        original_query = messages[0].content if messages else ""
        
        try:
            # Use LLM to parse and populate the 4 factors
            parsing_chain = PARSE_FOUR_FACTORS_PROMPT | self.supervisor_llm | JsonOutputParser()
            four_factors = parsing_chain.invoke({
                "original_query": original_query,
                "user_response": user_response
            })
            print(f"[DEBUG] LLM parsed 4 factors: {four_factors}")
            
            # Extract values with defaults
            income = four_factors.get("budget_income", "150000")
            user_preferences = f"Family: {four_factors.get('family_situation', 'family-friendly')}, Lifestyle: {four_factors.get('lifestyle_preference', 'mixed communities')}, Growth: {four_factors.get('growth_priorities', 'balanced')}"
            
        except Exception as e:
            print(f"[DEBUG] Error parsing factors: {e}, using defaults")
            income = "150000"
            user_preferences = f"Original: {original_query}\nResponse: {user_response}"
        
        # Determine routing based on state
        if state.get("route") == "non_real_estate":
            route = "non_real_estate"
        elif state.get("is_comparison"):
            route = "comparison"
        else:
            route = "single_state"
        
        print(f"[DEBUG] Routing to: {route}")
        print(f"[DEBUG] Final income: {income}")
        
        return {
            **state, 
            "needs_followup": self.needs_followup, 
            "route": route,
            "user_preferences": user_preferences,
            "income": income
        }

    def single_state_county_lookup(self, state):
        """County lookup node for single state flow - LLM generates tool call"""
        print("🔄 Executing: single_state_county_lookup (LLM generates tool call)")
        
        state_info = state["states"][0]
        prompt = SINGLE_STATE_TOOL_CALL_PROMPT.format(
            state_info=state_info,
            state_name=state_info["state_name"],
            state_fips=state_info["fips_code"]
        )
        
        # LLM generates tool call
        response = self.supervisor_llm_with_tools.invoke([{"role": "user", "content": prompt}])
        
        # Add the AI message with tool calls to state
        return {
            **state,
            "messages": state.get("messages", []) + [response]
        }

    def comparison_county_lookup(self, state):
        """County lookup node for comparison flow - LLM generates tool calls"""
        print("🔄 Executing: comparison_county_lookup (LLM generates tool calls)")
        
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
        print("🔄 Executing: summarize_single_state with tagging and sorting")
        
        # Extract tool results from messages
        messages = state.get("messages", [])
        tool_output = extract_tool_results_from_messages(messages)
        
        state_info = state["states"][0]
        state_name = state_info["state_name"]
        counties = tool_output.get("data", {}).get(state_name, {}).get("data", [])
        
        # Process counties with tagging system using function from tools.py
        user_preferences = state.get("user_preferences", "")
        user_budget = int(state.get("income", "150000"))
        user_priority = parse_user_priority(user_preferences)
        state_medians = calculate_state_medians(counties)
        
        processed_counties = process_counties_with_tagging(
            counties, user_priority, state_medians, user_budget
        )
        
        # Update tool_output with processed counties
        if processed_counties:
            tool_output["data"][state_name]["data"] = processed_counties
            summary = f"Top 5 counties in {state_name}: " + ", ".join([c["name"] for c in processed_counties[:5]])
        else:
            summary = f"No counties found in {state_name}"
        
        return {**state, "summary": summary, "tool_output": tool_output}
    
    def insights_single_state(self, state):
        print("🔄 Executing: insights_single_state (LLM-based)")
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
        
        # Use the prompt from prompts.py
        chain = SINGLE_STATE_INSIGHTS_PROMPT | self.formatter_llm
        response = chain.invoke({
            "state_name": state_name,
            "summary": summary,
            "tool_output": str(tool_output),
            "income": income,
            "user_preferences": f"{user_preferences} (Budget tier: {tier_description})"
        })
        
        # Parse response (simple split)
        content = response.content if hasattr(response, 'content') else str(response)
        insights, recommendation = "", ""
        if "Recommendation:" in content:
            parts = content.split("Recommendation:")
            insights = parts[0].replace("Insights:", "").strip()
            recommendation = parts[1].strip()
        else:
            insights = content.strip()
        return {**state, "insights": insights, "recommendation": recommendation}

    def assemble_single_state(self, state):
        print("🔄 Executing: assemble_single_state (detailed report)")
        insights = state.get("insights", "")
        recommendation = state.get("recommendation", "")
        tool_output = state.get("tool_output", {})
        state_info = state["states"][0]
        state_name = state_info["state_name"]
        income_raw = state.get("income", "150000")
        # Format income for display (add commas)
        income = f"{int(income_raw):,}" if income_raw.isdigit() else income_raw
        counties = tool_output.get("data", {}).get(state_name, {}).get("data", [])
        
        # Use formatting function from formatting.py
        final_report = format_single_state_report(
            state_name=state_name,
            income=income,
            counties=counties,
            insights=insights,
            recommendation=recommendation
        )
        
        # Reset state flags for next query
        return {
            "messages": state.get("messages", []),
            "final_result": final_report
        }

    def summarize_comparison(self, state):
        """Summarize comparison results using tagging and sorting"""
        print("🔄 Executing: summarize_comparison with tagging and sorting")
        
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
            counties1, user_priority, state_medians1, user_budget
        )
        processed_counties2 = process_counties_with_tagging(
            counties2, user_priority, state_medians2, user_budget
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
        print("🔄 Executing: insights_comparison (LLM-based)")
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
        
        # Use the prompt from prompts.py
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
        return {**state, "insights": takeaways, "recommendation": recommendation}

    def handle_non_real_estate(self, state):
        print("🔄 Executing: handle_non_real_estate")
        messages = state.get("messages", [])
        user_query = messages[0].content if messages else "your query"
        
        # Use the imported prompt template instead of hardcoded response
        response = NON_REAL_ESTATE_RESPONSE.format(user_query=user_query)
        
        print("✅ Completed: handle_non_real_estate")
        return {
            "messages": state.get("messages", []),
            "final_result": response
        }

    def assemble_comparison(self, state):
        print("🔄 Executing: assemble_comparison (detailed report)")
        insights = state.get("insights", "")
        recommendation = state.get("recommendation", "")
        tool_output = state.get("tool_output", {})
        state1, state2 = state["states"][:2]
        name1, name2 = state1["state_name"], state2["state_name"]
        income_raw = state.get("income", "150000")
        # Format income for display (add commas)
        income = f"{int(income_raw):,}" if income_raw.isdigit() else income_raw
        counties1 = tool_output.get("state1", {}).get("data", {}).get(name1, {}).get("data", [])
        counties2 = tool_output.get("state2", {}).get("data", {}).get(name2, {}).get("data", [])
        
        # Use formatting function from formatting.py
        final_report = format_comparison_report(
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
        # If not initialized yet, call setup_graph
        if self.tools is None or self.supervisor_llm is None:
            await self.setup_graph()
            return self.graph
            
        graph = StateGraph(AgentState)
        
        # Create a single ToolNode for executing tools
        tool_node = ToolNode(self.tools)

        # Add all nodes to the graph
        graph.add_node("extract_states", self.extract_states_and_flag)
        graph.add_node("followup_question", self.ask_followup_question)
        graph.add_node("single_state_county_lookup", self.single_state_county_lookup)
        graph.add_node("comparison_county_lookup", self.comparison_county_lookup)
        graph.add_node("tools", tool_node)
        graph.add_node("summarize_single_state", self.summarize_single_state)
        graph.add_node("insights_single_state", self.insights_single_state)
        graph.add_node("assemble_single_state", self.assemble_single_state)
        graph.add_node("summarize_comparison", self.summarize_comparison)
        graph.add_node("insights_comparison", self.insights_comparison)
        graph.add_node("assemble_comparison", self.assemble_comparison)
        graph.add_node("handle_non_real_estate", self.handle_non_real_estate)
        
        # Entry point
        graph.set_entry_point("extract_states")
        
        # Routing from extract_states
        graph.add_conditional_edges(
            "extract_states",
            lambda state: state.get("route", "continue"),
            {
                "non_real_estate": "handle_non_real_estate",
                "continue": "followup_question"
            }
        )
        
        # Routing from followup_question
        graph.add_conditional_edges(
            "followup_question",
            lambda state: state.get("route", "continue"),
            {
                "single_state": "single_state_county_lookup",
                "comparison": "comparison_county_lookup", 
                "non_real_estate": "handle_non_real_estate",
                "continue": "followup_question"
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

        # Tool execution routing with debug logging
        def route_after_tools(state):
            is_comparison = state.get("is_comparison", False)
            route = "comparison" if is_comparison else "single_state"
            print(f"🔀 Tool routing: is_comparison={is_comparison} → route={route}")
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
        
        return graph.compile(checkpointer=checkpointer)