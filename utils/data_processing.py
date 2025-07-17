def extract_tool_results_from_messages(messages):
    """Extract tool results from LangChain messages"""
    tool_results = []
    tool_messages = []
    
    for message in messages:
        # Check for ToolMessage which contains the actual tool results
        if hasattr(message, 'content') and hasattr(message, 'tool_call_id'):
            tool_messages.append(message)
        
        # Also check for tool_calls (legacy approach)
        if hasattr(message, 'tool_calls') and message.tool_calls:
            for tool_call in message.tool_calls:
                if hasattr(tool_call, 'args') and tool_call.args:
                    tool_results.append({
                        'tool_name': tool_call.name,
                        'args': tool_call.args,
                        'result': getattr(tool_call, 'result', None)
                    })
    
    # Handle ToolMessages (new approach)
    if tool_messages:
        import json
        
        # If we have multiple tool messages, this is likely a comparison
        if len(tool_messages) > 1:
            combined_results = {}
            for i, tool_msg in enumerate(tool_messages):
                try:
                    result_data = json.loads(tool_msg.content)
                    # For comparison, use consistent structure
                    state_key = f"state{i+1}"
                    combined_results[state_key] = result_data
                except:
                    continue
            return combined_results
        else:
            # Single tool message
            try:
                result_data = json.loads(tool_messages[0].content)
                return result_data
            except:
                return {}
    
    # Handle legacy tool_results approach
    if tool_results:
        # For real estate tool, return the actual result data
        for result in tool_results:
            if result['tool_name'] == 'real_estate_investment_tool' and result['result']:
                # Handle case where result might be a string (JSON) or dict
                if isinstance(result['result'], str):
                    import json
                    try:
                        return json.loads(result['result'])
                    except:
                        return {}
                elif isinstance(result['result'], list):
                    return {"data": result['result']}
                return result['result']
        
        # If no real estate tool found, return the first result
        if tool_results[0]['result']:
            result_data = tool_results[0]['result']
            if isinstance(result_data, str):
                import json
                try:
                    return json.loads(result_data)
                except:
                    return {}
            elif isinstance(result_data, list):
                return {"data": result_data}
            return result_data
    
    return {}

def format_currency(value):
    """Format a number as currency"""
    if value is None or value == 0:
        return "N/A"
    return f"${value:,.0f}"

def format_percentage(value):
    """Format a number as percentage"""
    if value is None:
        return "N/A"
    return f"{value:.1f}%"

def format_number(value):
    """Format a number with commas"""
    if value is None:
        return "N/A"
    return f"{value:,.0f}" 