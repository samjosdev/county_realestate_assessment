import gradio as gr
import asyncio
import os
import uuid
from dotenv import load_dotenv
from build_graph import USCensusAgent
from langchain_core.messages import HumanMessage

load_dotenv(override=True)

# Global variables
us_census_agent = None

async def setup_graph():
    """Setup the USCensusAgent and workflow graph once at startup"""
    global us_census_agent
    if us_census_agent is None:
        print("🔧 Setting up USCensusAgent...")
        us_census_agent = USCensusAgent()
        await us_census_agent.setup_graph()
        print("✅ USCensusAgent ready!")
    return us_census_agent.graph

async def generate_report(analysis_type, state1, state2, income, family_size, 
                         lifestyle, priorities, progress=gr.Progress()):
    """Generate real estate report based on user inputs"""
    
    # Reset progress tracking for new report
    progress(0, desc="🔄 Starting new analysis...")
    
    # Validation
    if not state1:
        return "❌ Please select at least one state for analysis."
    
    if not income or income <= 0:
        return "❌ Please enter a valid household income."
    
    # Setup graph
    progress(0.1, desc="🔧 Setting up analysis engine...")
    graph = await setup_graph()
    
    # Build query based on inputs
    if analysis_type == "Single State Analysis":
        if state2 and state2 != "None":
            analysis_type = "State Comparison"  # Auto-switch if second state selected
    
    progress(0.2, desc="📝 Building analysis query...")
    
    if analysis_type == "State Comparison" and state2 and state2 != "None":
        query = f"Compare {state1} vs {state2} for real estate investment"
    else:
        query = f"Find me a good place to buy a house in {state1}"
    
    # Add family context
    if family_size > 1:
        query += f" for my family of {family_size}"
    
    # Add income context  
    if income >= 1000000:
        query += f" with ${income:,} income"
    elif income >= 1000:
        income_k = int(income / 1000)
        query += f" with ${income_k}k income"
    else:
        query += f" with ${income} income"
    
    progress(0.3, desc="🔍 Analyzing states and requirements...")
    
    # Create user preferences string
    preferences = f"Family size: {family_size}. Lifestyle: {lifestyle}. Priorities: {priorities}"
    
    # Build states list based on selections
    states = []
    
    # Add primary state
    state1_fips = get_state_fips(state1)
    if state1_fips:
        states.append({"state_name": state1, "fips_code": state1_fips})
    
    # Add second state if comparison
    if analysis_type == "State Comparison" and state2 and state2 != "None":
        state2_fips = get_state_fips(state2)
        if state2_fips:
            states.append({"state_name": state2, "fips_code": state2_fips})
    
    # Create fresh state for workflow - all structured data, no NLP needed
    # Use unique thread ID to ensure fresh state
    thread_id = f"report_{uuid.uuid4().hex[:8]}"
    state = {
        "messages": [HumanMessage(content=query)],  # Keep for compatibility
        "states": states,  # Pre-structured state data
        "income": str(income),
        "user_preferences": preferences,
        "needs_followup": False  # Skip all followup logic
    }
    
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        progress(0.4, desc="🏘️ Fetching county data...")
        
        result = await asyncio.wait_for(
            graph.ainvoke(state, config=config),
            timeout=600  # 10 minute timeout
        )
        
        progress(0.9, desc="📊 Generating final report...")
        
        if "final_result" in result and result["final_result"]:
            progress(1.0, desc="✅ Report completed!")
            # Return the HTML report - state will be automatically reset by Gradio
            return result["final_result"]
        else:
            return """
            <div class="professional-report">
                <div class="report-header" style="background: #ef4444;">
                    <h1>❌ Report Generation Failed</h1>
                    <p class="subtitle">Unable to generate report with current parameters</p>
                </div>
                <div class="report-content">
                    <p>Sorry, I couldn't generate a report with the selected parameters. Please try:</p>
                    <ul>
                        <li>Selecting different states</li>
                        <li>Adjusting your income range</li>
                        <li>Trying again in a few moments</li>
                    </ul>
                </div>
            </div>
            """
            
    except asyncio.TimeoutError:
        return """
        <div class="professional-report">
            <div class="report-header" style="background: #f59e0b;">
                <h1>⏰ Analysis Timeout</h1>
                <p class="subtitle">Report generation took longer than expected</p>
            </div>
            <div class="report-content">
                <p>The analysis timed out after 10 minutes. This can happen with:</p>
                <ul>
                    <li>High server load</li>
                    <li>Complex multi-state comparisons</li>
                    <li>Network connectivity issues</li>
                </ul>
                <p><strong>Please try again</strong> - most reports generate within 2-7 minutes.</p>
            </div>
        </div>
        """
    except Exception as e:
        print(f"Error generating report: {e}")
        import traceback
        traceback.print_exc()
        return f"""
        <div class="professional-report">
            <div class="report-header" style="background: #ef4444;">
                <h1>❌ System Error</h1>
                <p class="subtitle">An unexpected error occurred</p>
            </div>
            <div class="report-content">
                <p>We encountered a technical issue while generating your report:</p>
                <div style="background: #fee2e2; padding: 16px; border-radius: 8px; margin: 16px 0;">
                    <code>{str(e)}</code>
                </div>
                <p>Please try again or contact support if the issue persists.</p>
            </div>
        </div>
        """

# State FIPS mapping
STATE_FIPS = {
    "Alabama": "01", "Alaska": "02", "Arizona": "04", "Arkansas": "05", 
    "California": "06", "Colorado": "08", "Connecticut": "09", "Delaware": "10", 
    "Florida": "12", "Georgia": "13", "Hawaii": "15", "Idaho": "16", 
    "Illinois": "17", "Indiana": "18", "Iowa": "19", "Kansas": "20", 
    "Kentucky": "21", "Louisiana": "22", "Maine": "23", "Maryland": "24", 
    "Massachusetts": "25", "Michigan": "26", "Minnesota": "27", "Mississippi": "28", 
    "Missouri": "29", "Montana": "30", "Nebraska": "31", "Nevada": "32", 
    "New Hampshire": "33", "New Jersey": "34", "New Mexico": "35", "New York": "36", 
    "North Carolina": "37", "North Dakota": "38", "Ohio": "39", "Oklahoma": "40", 
    "Oregon": "41", "Pennsylvania": "42", "Rhode Island": "44", "South Carolina": "45", 
    "South Dakota": "46", "Tennessee": "47", "Texas": "48", "Utah": "49", 
    "Vermont": "50", "Virginia": "51", "Washington": "53", "West Virginia": "54", 
    "Wisconsin": "55", "Wyoming": "56"
}

def get_state_fips(state_name):
    """Get FIPS code for a state"""
    return STATE_FIPS.get(state_name)

US_STATES = [
    "None", "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", 
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", 
    "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", 
    "Massachusetts", "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana", 
    "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico", "New York", 
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon", "Pennsylvania", 
    "Rhode Island", "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah", 
    "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"
]

# Create the interface
def create_interface():
    with gr.Blocks(
        title="🏡 FamilyHomeFinder - Real Estate Analysis Report",
        theme=gr.themes.Soft(primary_hue="green", secondary_hue="green")
    ) as demo:
        
        gr.Markdown("""
        # 🏡 FamilyHomeFinder
        ### Your Data-Driven Guide to the Best Places to Live
        
        **Generate comprehensive real estate reports** comparing states and finding perfect counties for your family's needs.
        """)
        
        with gr.Row():
            # LEFT PANEL - User Inputs
            with gr.Column(scale=1):
                gr.Markdown("## 📋 Analysis Settings")
                
                analysis_type = gr.Radio(
                    choices=["Single State Analysis", "State Comparison"],
                    value="Single State Analysis",
                    label="Analysis Type",
                    info="Choose between analyzing one state or comparing two states"
                )
                
                with gr.Row():
                    state1 = gr.Dropdown(
                        choices=[s for s in US_STATES if s != "None"],
                        value="Oregon",
                        label="Primary State",
                        info="State to analyze"
                    )
                    state2 = gr.Dropdown(
                        choices=US_STATES,
                        value="None", 
                        label="Compare with (Optional)",
                        info="Second state for comparison",
                        interactive=False  # Initially disabled
                    )
                
                gr.Markdown("## 👨‍👩‍👧‍👦 Family Details")
                
                income = gr.Slider(
                    minimum=30000,
                    maximum=5000000,
                    value=120000,
                    step=5000,
                    label="Annual Household Income ($)",
                    info="Your total family income per year"
                )
                
                family_size = gr.Slider(
                    minimum=1,
                    maximum=8,
                    value=4,
                    step=1,
                    label="Family Size",
                    info="Total number of people in your household"
                )
                
                gr.Markdown("## 🏘️ Lifestyle Preferences")
                
                lifestyle = gr.Radio(
                    choices=[
                        "Urban (city amenities, walkable, public transit)",
                        "Suburban (family neighborhoods, good schools, parks)", 
                        "Rural (space, nature, quiet, lower cost)"
                    ],
                    value="Suburban (family neighborhoods, good schools, parks)",
                    label="Preferred Lifestyle",
                    info="What type of community do you prefer?"
                )
                
                priorities = gr.Radio(
                    choices=[
                        "Affordability (lower cost of living, value for money)",
                        "Investment Growth (property appreciation, job markets)",
                        "Family Safety (low crime, good schools, healthcare)",
                        "Balanced (mix of affordability, growth, and safety)"
                    ],
                    value="Balanced (mix of affordability, growth, and safety)",
                    label="Top Priority",
                    info="What matters most in your decision?"
                )
                
                # Status indicator
                status_text = gr.Markdown(
                    value="Configure your preferences above, then click 'Generate Report' to get started.",
                    elem_classes=["status-indicator"]
                )
                
                # Form validation logic
                def update_state2_interactive(analysis_type_val):
                    """Update state2 dropdown interactivity based on analysis type"""
                    if analysis_type_val == "Single State Analysis":
                        return gr.Dropdown(value="None", interactive=False)
                    else:
                        return gr.Dropdown(interactive=True)
                
                def update_status(analysis_type_val, state1_val, state2_val):
                    """Update status text based on current selections"""
                    if analysis_type_val == "Single State Analysis":
                        is_valid = bool(state1_val)
                        return "Ready to generate report!" if is_valid else "Please select a state"
                    else:
                        is_valid = bool(state1_val) and bool(state2_val) and state2_val != "None" and state1_val != state2_val
                        return "Ready to generate report!" if is_valid else "Please select two different states"
                
                # Update state2 interactivity when analysis type changes
                analysis_type.change(
                    update_state2_interactive,
                    inputs=[analysis_type],
                    outputs=[state2]
                )
                
                # Update status when any relevant input changes
                analysis_type.change(
                    update_status,
                    inputs=[analysis_type, state1, state2],
                    outputs=[status_text]
                )
                state1.change(
                    update_status,
                    inputs=[analysis_type, state1, state2],
                    outputs=[status_text]
                )
                state2.change(
                    update_status,
                    inputs=[analysis_type, state1, state2],
                    outputs=[status_text]
                )
            
            # RIGHT PANEL - Reports with Tiles
            with gr.Column(scale=2):
                gr.Markdown("## 📊 Real Estate Analysis Report")
                
                # PERSISTENT TILES SECTION - Always visible
                tiles_output = gr.HTML(
                    value="""
<div class="welcome-container">
    <div class="welcome-header">
        <h2>🏡 Welcome to FamilyHomeFinder!</h2>
        <p>Configure your preferences on the left and click "Generate Report" to get started.</p>
    </div>
    
    <div class="features-grid">
        <div class="feature-card active-card" id="top-counties-card">
            <div class="feature-icon">🏆</div>
            <h3>Top Counties</h3>
            <p>Ranked specifically for your family's needs and budget</p>
            <div class="status-badge available">Available Now</div>
        </div>
        
        <div class="feature-card disabled-card">
            <div class="feature-icon">📊</div>
            <h3>Market Analysis</h3>
            <p>Housing market insights for your budget tier</p>
            <div class="status-badge coming-soon">Coming Soon</div>
        </div>
        
        <div class="feature-card disabled-card">
            <div class="feature-icon">📈</div>
            <h3>Investment Insights</h3>
            <p>Growth potential and investment opportunities</p>
            <div class="status-badge coming-soon">Coming Soon</div>
        </div>
        
        <div class="feature-card disabled-card">
            <div class="feature-icon">🏫</div>
            <h3>Family Features</h3>
            <p>Schools, safety, and family-friendly amenities</p>
            <div class="status-badge coming-soon">Coming Soon</div>
        </div>
    </div>
    
    <div class="report-note">
        <p><strong>📊 Professional Reports:</strong> Comprehensive data analysis typically takes 2-7 minutes to generate.</p>
    </div>
</div>
                    """,
                    elem_classes=["tiles-container"]
                )
                
                # GENERATE REPORT BUTTON - Below tiles
                generate_btn = gr.Button(
                    "🚀 Generate Report",
                    variant="primary",
                    size="lg",
                    elem_classes=["generate-btn"]
                )
                
                # SEPARATE REPORT CONTENT AREA
                report_output = gr.HTML(
                    value="",
                    elem_classes=["report-container"]
                )
        
        # Generate Report button click handler
        generate_btn.click(
            fn=lambda: ("🔄 Generating your real estate report...", "Generating..."),
            outputs=[status_text, report_output],
            queue=False
        ).then(
            fn=generate_report,
            inputs=[analysis_type, state1, state2, income, family_size, lifestyle, priorities],
            outputs=[report_output],
            show_progress=True
        ).then(
            fn=lambda: "✅ Report completed! Adjust settings above to generate a new report.",
            outputs=[status_text],
            queue=False
        )
        
        # Update status when any input changes
        for component in [state1, state2, income, family_size, lifestyle, priorities, analysis_type]:
            component.change(
                fn=lambda *args: "Settings updated. Ready to generate new report.",
                outputs=[status_text],
                queue=False
            )
        
        # Enhanced CSS with tile styling and button styling
        demo.css = """
        .tiles-container {
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
            padding: 0;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            margin-bottom: 20px;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            overflow: hidden;
        }
        
        .generate-btn {
            margin: 20px 0 !important;
            background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%) !important;
            border: none !important;
            color: white !important;
            font-weight: 600 !important;
            font-size: 1.1em !important;
            padding: 16px 32px !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 15px rgba(34, 197, 94, 0.3) !important;
            transition: all 0.3s ease !important;
        }
        
        .generate-btn:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 25px rgba(34, 197, 94, 0.4) !important;
            background: linear-gradient(135deg, #16a34a 0%, #15803d 100%) !important;
        }
        
        .report-container {
            background: white;
            padding: 0;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            overflow: hidden;
            min-height: 200px;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        
        /* Welcome Screen Styling */
        .welcome-container {
            padding: 40px;
            text-align: center;
        }
        
        .welcome-header h2 {
            color: #1e293b;
            font-size: 2.2em;
            margin-bottom: 16px;
            font-weight: 700;
        }
        
        .welcome-header p {
            color: #475569;
            font-size: 1.1em;
            margin-bottom: 40px;
        }
        
        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 40px 0;
        }
        
        .feature-card {
            background: white;
            padding: 24px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            border: 1px solid #e2e8f0;
            transition: transform 0.2s ease;
            position: relative;
        }
        
        .active-card {
            border: 2px solid #22c55e;
            box-shadow: 0 8px 25px rgba(34, 197, 94, 0.15);
        }
        
        .disabled-card {
            opacity: 0.6;
            background: #f8f9fa;
        }
        
        .feature-icon {
            font-size: 2.5em;
            margin-bottom: 16px;
        }
        
        .feature-card h3 {
            color: #1e293b;
            font-size: 1.2em;
            margin-bottom: 8px;
            font-weight: 600;
        }
        
        .feature-card p {
            color: #64748b;
            font-size: 0.95em;
            line-height: 1.5;
        }
        
        .status-badge {
            position: absolute;
            top: 12px;
            right: 12px;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.7em;
            font-weight: 600;
        }
        
        .available {
            background: #dcfce7;
            color: #166534;
        }
        
        .coming-soon {
            background: #fef3c7;
            color: #92400e;
        }
        
        .report-note {
            background: #f1f5f9;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #3b82f6;
            margin-top: 30px;
        }
        
        .report-note p {
            color: #475569;
            margin: 0;
            font-size: 0.95em;
        }
        
        /* Professional Report Styling */
        .professional-report {
            background: white;
            padding: 0;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            overflow: hidden;
        }
        
        .report-header {
            background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        
        .report-header h1 {
            font-size: 2.5em;
            margin: 0 0 10px 0;
            font-weight: 700;
        }
        
        .report-header .subtitle {
            font-size: 1.2em;
            opacity: 0.9;
            margin: 0;
        }
        
        .report-content {
            padding: 40px;
        }
        
        .county-card {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 24px;
            margin: 20px 0;
            transition: box-shadow 0.2s ease;
        }
        
        .county-card:hover {
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        }
        
        .county-header {
            display: flex;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .county-rank {
            background: #3b82f6;
            color: white;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            margin-right: 16px;
        }
        
        .county-name {
            font-size: 1.4em;
            font-weight: 600;
            color: #1e293b;
            margin: 0;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 16px;
            margin: 20px 0;
        }
        
        .stat-item {
            background: white;
            padding: 16px;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
        }
        
        .stat-label {
            font-size: 0.85em;
            color: #64748b;
            margin-bottom: 4px;
        }
        
        .stat-value {
            font-size: 1.2em;
            font-weight: 600;
            color: #1e293b;
        }
        
        .county-description {
            background: white;
            padding: 16px;
            border-radius: 8px;
            border-left: 4px solid #22c55e;
            margin-top: 16px;
        }
        
        .county-images {
            display: flex;
            gap: 12px;
            margin: 16px 0;
            flex-wrap: wrap;
        }
        
        .county-image {
            width: 200px;
            height: 120px;
            border-radius: 8px;
            object-fit: cover;
            border: 1px solid #e2e8f0;
        }
        
        .insights-section {
            background: #f1f5f9;
            padding: 30px;
            border-radius: 12px;
            margin: 30px 0;
            border-left: 4px solid #3b82f6;
        }
        
        .insights-section h3 {
            color: #1e293b;
            font-size: 1.3em;
            margin-bottom: 16px;
        }
        
        .insights-content,
        .recommendation-content {
            line-height: 1.6;
            color: #374151;
        }
        
        .insights-content p,
        .recommendation-content p {
            margin-bottom: 12px;
        }
        
        .insights-content p:last-child,
        .recommendation-content p:last-child {
            margin-bottom: 0;
        }
        
        .comparison-container {
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
            padding: 24px;
            border-radius: 16px;
            margin: 24px 0;
            border: 1px solid #e2e8f0;
        }
        
        .comparison-grid {
            display: grid;
            grid-template-columns: auto 1fr 1fr;
            gap: 16px;
            align-items: center;
        }
        
        .comparison-rank {
            background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
            color: white;
            width: 48px;
            height: 48px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 1.1em;
            grid-row: span 2;
        }
        
        .state-section {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            border: 1px solid #e5e7eb;
        }
        
        .state-header {
            font-size: 1.1em;
            font-weight: 600;
            color: #1e293b;
            margin-bottom: 8px;
            padding-bottom: 8px;
            border-bottom: 2px solid #e5e7eb;
        }
        
        .county-name {
            font-size: 1em;
            font-weight: 500;
            color: #374151;
            margin-bottom: 12px;
        }
        
        .quick-stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }
        
        .quick-stat {
            text-align: center;
        }
        
        .quick-stat-label {
            font-size: 0.75em;
            color: #6b7280;
            margin-bottom: 4px;
            text-transform: uppercase;
            font-weight: 500;
            letter-spacing: 0.5px;
        }
        
        .quick-stat-value {
            font-size: 0.95em;
            font-weight: 600;
            color: #1f2937;
        }
        
        .gradio-container {
            max-width: 1600px !important;
        }
        
        /* Status indicator styling */
        .status-indicator {
            background: #f1f5f9;
            padding: 12px 16px;
            border-radius: 8px;
            border-left: 4px solid #3b82f6;
            margin: 16px 0;
            font-size: 0.9em;
            color: #475569;
        }
        
        @media (max-width: 768px) {
            .features-grid {
                grid-template-columns: 1fr;
            }
            
            .stats-grid {
                grid-template-columns: 1fr;
            }
            
            .county-images {
                justify-content: center;
            }
            
            .comparison-grid {
                grid-template-columns: 1fr;
                text-align: center;
            }
            
            .comparison-rank {
                grid-row: span 1;
                margin: 0 auto;
            }
            
            .quick-stats {
                grid-template-columns: 1fr;
            }
        }
        """
    
    return demo

if __name__ == "__main__":
    demo = create_interface()
    
    # Use environment variables for configuration
    port = int(os.getenv("PORT", 7860))
    host = os.getenv("HOST", "0.0.0.0")
    
    demo.launch()