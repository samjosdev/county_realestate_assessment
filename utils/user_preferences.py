def parse_user_priority(user_preferences: str) -> dict:
    """Enhanced priority parsing that captures lifestyle preferences."""
    priority = {
        "budget": True,
        "family": False,
        "community_type": None,
        "growth": False,
        "lifestyle": user_preferences.lower() if user_preferences else ""
    }
    
    if not user_preferences:
        return priority
    
    pref_lower = user_preferences.lower()
    
    # Budget priority
    if any(word in pref_lower for word in ["affordability", "affordable", "budget", "cost", "cheap", "value"]):
        priority["budget"] = True
    
    # Family priority
    if any(word in pref_lower for word in ["family", "families", "children", "kids", "schools", "safety", "safe"]):
        priority["family"] = True
        
    # Community type - ENHANCED detection
    if any(word in pref_lower for word in ["urban", "city", "downtown", "metropolitan"]):
        priority["community_type"] = "urban"
    elif any(word in pref_lower for word in ["suburban", "suburb", "neighborhood", "good schools", "family"]):
        priority["community_type"] = "suburban"  
    elif any(word in pref_lower for word in ["rural", "small town", "country", "quiet"]):
        priority["community_type"] = "rural"
    
    # Growth priority
    if any(word in pref_lower for word in ["growth", "investment", "appreciation", "job market", "economy"]):
        priority["growth"] = True
    
    return priority 