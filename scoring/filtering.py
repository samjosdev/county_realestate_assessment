from best_counties_by_state import BEST_COUNTIES_PER_STATE
from .county_scoring import calculate_college_degree_rate, detect_tier

def smart_filter_counties(counties_data, user_priority, user_budget, keep_top_n=30):
    """
    Simplified version - main filtering happens in process_counties_with_tagging
    """
    if not counties_data:
        return []
    
    # Just basic viability check - detailed filtering happens later
    min_population = 10000
    min_income = 30000
    min_home_value = 50000
    
    viable_counties = []
    for county in counties_data:
        if (county.get('B01003_001E', 0) >= min_population and
            county.get('B19013_001E', 0) >= min_income and
            county.get('B25077_001E', 0) >= min_home_value):
            viable_counties.append(county)
    
    return viable_counties

def apply_smart_filtering(counties, user_priority, user_budget, tier):
    """
    Apply realistic filtering that works with real county data.
    """
    lifestyle = user_priority.get("lifestyle", "").lower()
    community_type = user_priority.get("community_type", "")
    
    # VERY REALISTIC county-level requirements
    if tier == "ultra_luxury":
        min_population = 100000      # Major metros only
        min_income = 45000          # Realistic county medians
        min_home_value = 150000     # Realistic minimums
        min_college_rate = 12       # Achievable education levels
    elif tier == "luxury":
        min_population = 75000      # Substantial counties
        min_income = 40000          # Very achievable
        min_home_value = 130000     # Reasonable minimum
        min_college_rate = 10       # Basic education filter
    elif tier == "move_up":
        min_population = 50000
        min_income = 35000
        min_home_value = 100000
        min_college_rate = 8
    else:  # affordable
        min_population = 25000
        min_income = 30000
        min_home_value = 80000
        min_college_rate = 6
    
    # Lifestyle adjustments (moderate)
    if "suburban" in lifestyle or community_type == "suburban":
        if tier in ["luxury", "ultra_luxury"]:
            min_population = max(min_population, 150000)  # Need substantial metros
        else:
            min_population = max(min_population, 75000)
    elif "urban" in lifestyle or community_type == "urban":
        min_population = max(min_population, 100000)
    elif "rural" in lifestyle or community_type == "rural":
        min_population = max(15000, min_population // 2)
    
    # High-income + suburban = major metro requirement (realistic)
    if user_budget >= 800000 and ("suburban" in lifestyle or community_type == "suburban"):
        min_population = max(min_population, 200000)  # Major metros
        min_income = max(min_income, 50000)           # Still realistic
    
    # Apply filters
    filtered = []
    
    for county in counties:
        population = county.get('B01003_001E', 0)
        income = county.get('B19013_001E', 0)
        home_value = county.get('B25077_001E', 0)
        college_rate = calculate_college_degree_rate(county)
        
        # Check each requirement
        if (population >= min_population and
            income >= min_income and
            home_value >= min_home_value and
            college_rate >= min_college_rate):
            filtered.append(county)
    
    # If we need more counties, be more flexible
    if len(filtered) < 3:
        # Emergency relaxed standards
        emergency_pop = max(50000, min_population // 2)
        emergency_income = max(25000, min_income * 0.7)
        emergency_home = max(60000, min_home_value * 0.6)
        emergency_college = max(5, min_college_rate * 0.5)
        
        additional = []
        for county in counties:
            if county in filtered:
                continue
                
            population = county.get('B01003_001E', 0)
            income = county.get('B19013_001E', 0)
            home_value = county.get('B25077_001E', 0)
            college_rate = calculate_college_degree_rate(county)
            
            if (population >= emergency_pop and
                income >= emergency_income and
                home_value >= emergency_home and
                college_rate >= emergency_college):
                additional.append(county)
        
        filtered.extend(additional)
    
    # Sort by population to prioritize major metros
    filtered.sort(key=lambda x: x.get('B01003_001E', 0), reverse=True)
    
    return filtered

def process_counties_with_tagging(counties, user_priority, state_medians, user_budget, state_name=None):
    """
    Apply improved scoring and sorting to counties with strict filtering for high-income users.
    """
    if not counties:
        return []
    
    tier = detect_tier(user_budget)
    
    # STEP 1: Apply strict pre-filtering based on user requirements
    filtered_counties = apply_smart_filtering(counties, user_priority, user_budget, tier)
    
    if not filtered_counties:
        return []
    
    # STEP 2: Apply best counties filter for higher tiers
    if tier in ("move_up", "luxury", "ultra_luxury") and state_name and state_name in BEST_COUNTIES_PER_STATE:
        best_county_names = BEST_COUNTIES_PER_STATE[state_name]
        best_counties = [c for c in filtered_counties if c.get("name") in best_county_names]
        
        if best_counties:
            filtered_counties = best_counties
    
    # STEP 3: Calculate comprehensive scores for each county
    for county in filtered_counties:
        # Add college degree rate
        county['college_degree_rate'] = calculate_college_degree_rate(county)
        
        # Calculate multi-dimensional scores
        from .county_scoring import calculate_comprehensive_scores, calculate_weighted_score
        scores = calculate_comprehensive_scores(county, state_medians, user_budget)
        
        # Calculate final weighted score
        final_score = calculate_weighted_score(scores, user_priority, tier)
        
        # Store scores and metadata
        county['scores'] = scores
        county['final_score'] = final_score
        county['tier'] = tier
        
        # Create user-friendly tags
        county['tags'] = {
            'budget_friendly': scores['affordability'] >= 70,
            'family_oriented': scores['family_friendly'] >= 70,
            'economic_growth': scores['economic_vitality'] >= 70,
            'stable_housing': scores['housing_stability'] >= 70,
            'tier_match': scores['budget_compatibility'] >= 70,
            'homeownership_rate': calculate_homeownership_rate_for_tags(county),
            'notable_family_feature': get_notable_feature(county, scores)
        }
    
    # STEP 4: Sort by final score and return top counties
    filtered_counties.sort(key=lambda x: x['final_score'], reverse=True)
    
    return filtered_counties[:25]

def get_notable_feature(county, scores):
    """Generate a notable feature description based on scores including optional safety"""
    features = []
    
    # Safety indicators (only if available)
    if 'safety' in scores:
        if scores['safety'] >= 90:
            features.append("Exceptionally safe community")
        elif scores['safety'] >= 75:
            features.append("Very safe neighborhood")
    
    if scores['affordability'] >= 90:
        features.append("Exceptional home value")
    elif scores['affordability'] >= 80:
        features.append("Great affordability")
    
    if scores['family_friendly'] >= 85:
        features.append("Excellent for families")
    elif scores['family_friendly'] >= 70:
        features.append("Family-friendly community")
    
    if scores['economic_vitality'] >= 85:
        features.append("Strong local economy")
    elif scores['economic_vitality'] >= 70:
        features.append("Good job market")
    
    if scores['housing_stability'] >= 80:
        features.append("Stable housing market")
    
    if scores['budget_compatibility'] >= 85:
        features.append("Perfect budget match")
    elif scores['budget_compatibility'] >= 70:
        features.append("Good budget fit")
    
    return features[0] if features else "Balanced community"

def calculate_homeownership_rate_for_tags(county):
    """Calculate homeownership rate for county tags"""
    try:
        total = county.get('B25003_001E', 0)
        owner_occupied = county.get('B25003_002E', 0)
        if total > 0:
            return round((owner_occupied / total) * 100, 1)
        return 0
    except:
        return 0 