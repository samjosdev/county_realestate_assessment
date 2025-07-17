import statistics
from typing import Dict, Any

def calculate_comprehensive_scores(county, state_medians, user_budget):
    """
    Calculate multiple scoring dimensions for more nuanced ranking.
    Crime data is optional - if not available, uses other metrics.
    Returns a dictionary of scores (0-100 scale).
    """
    scores = {}
    
    # Extract key metrics
    home_value = county.get("B25077_001E", 0)
    income = county.get("B19013_001E", 0)
    population = county.get("B01003_001E", 0)
    households_with_kids = county.get("B11005_002E", 0)
    total_households = county.get("B25003_001E", 0)
    owner_occupied = county.get("B25003_002E", 0)
    college_rate = county.get('college_degree_rate', 0)
    
    # 1. AFFORDABILITY SCORE (0-100)
    if income > 0:
        price_to_income = home_value / income
        if price_to_income <= 2.5:
            scores['affordability'] = 100
        elif price_to_income <= 3.5:
            scores['affordability'] = 80
        elif price_to_income <= 4.5:
            scores['affordability'] = 60
        elif price_to_income <= 6.0:
            scores['affordability'] = 40
        else:
            scores['affordability'] = 20
    else:
        scores['affordability'] = 0
    
    # 2. FAMILY FRIENDLINESS SCORE (0-100)
    family_score = 0
    
    # Kids factor (0-40 points)
    if total_households > 0:
        kids_ratio = households_with_kids / total_households
        family_score += min(kids_ratio * 100, 40)
    
    # Income stability (0-30 points)
    if income >= 70000:
        family_score += 30
    elif income >= 50000:
        family_score += 20
    elif income >= 35000:
        family_score += 10
    
    # Population size (0-30 points) - sweet spot for families
    if 50000 <= population <= 200000:
        family_score += 30
    elif 25000 <= population <= 300000:
        family_score += 20
    elif 10000 <= population <= 500000:
        family_score += 10
    
    scores['family_friendly'] = min(family_score, 100)
    
    # 3. ECONOMIC VITALITY SCORE (0-100)
    vitality_score = 0
    
    # Income relative to state (0-40 points)
    if state_medians.get("income", 0) > 0:
        income_ratio = income / state_medians["income"]
        vitality_score += min(income_ratio * 40, 40)
    
    # Education level (0-35 points)
    if college_rate >= 35:
        vitality_score += 35
    elif college_rate >= 25:
        vitality_score += 25
    elif college_rate >= 15:
        vitality_score += 15
    
    # Population growth potential (0-25 points)
    if population >= 100000:
        vitality_score += 25
    elif population >= 50000:
        vitality_score += 15
    elif population >= 25000:
        vitality_score += 10
    
    scores['economic_vitality'] = min(vitality_score, 100)
    
    # 4. HOUSING MARKET STABILITY (0-100)
    stability_score = 0
    
    # Homeownership rate (0-50 points)
    if total_households > 0:
        homeownership_rate = owner_occupied / total_households
        stability_score += homeownership_rate * 50
    
    # Home value relative to state (0-50 points)
    if state_medians.get("home_value", 0) > 0:
        value_ratio = home_value / state_medians["home_value"]
        if 0.8 <= value_ratio <= 1.5:
            stability_score += 50
        elif 0.6 <= value_ratio <= 2.0:
            stability_score += 35
        elif 0.4 <= value_ratio <= 3.0:
            stability_score += 20
    
    scores['housing_stability'] = min(stability_score, 100)
    
    # 5. BUDGET COMPATIBILITY (0-100)
    budget_score = 0
    tier = detect_tier(user_budget)
    
    if tier == "affordable":
        # Prioritize affordability and value
        if home_value <= user_budget * 3:
            budget_score += 50
        if income >= 40000:
            budget_score += 30
        if price_to_income <= 3.5:
            budget_score += 20
    elif tier == "move_up":
        # Balance of quality and price
        if user_budget * 2 <= home_value <= user_budget * 4:
            budget_score += 40
        if income >= 70000:
            budget_score += 30
        if college_rate >= 20:
            budget_score += 30
    elif tier == "luxury":
        # Quality and prestige
        if home_value >= user_budget * 2:
            budget_score += 30
        if income >= 100000:
            budget_score += 35
        if college_rate >= 30:
            budget_score += 35
    elif tier == "ultra_luxury":
        # Premium everything
        if home_value >= user_budget * 1.5:
            budget_score += 25
        if income >= 150000:
            budget_score += 25
        if college_rate >= 35:
            budget_score += 25
        if population >= 100000:
            budget_score += 25
    
    scores['budget_compatibility'] = min(budget_score, 100)
    
    # 6. SAFETY SCORE (0-100) - OPTIONAL
    crime_data = county.get('crime_data')
    if crime_data:
        safety_score = crime_data.get('overall_safety_score', 50)
        if isinstance(safety_score, (int, float)) and safety_score > 0:
            scores['safety'] = safety_score
        else:
            scores['safety'] = 50  # Neutral score if invalid data
    # If no crime data, don't include safety in scores
    
    return scores

def calculate_weighted_score(scores, user_priority, tier):
    """
    Calculate final weighted score based on user priorities and tier.
    Automatically adjusts weights if safety data is not available.
    """
    has_safety = 'safety' in scores
    
    if has_safety:
        # Base weights including safety
        weights = {
            'affordability': 0.18,
            'family_friendly': 0.18,
            'economic_vitality': 0.16,
            'housing_stability': 0.13,
            'budget_compatibility': 0.15,
            'safety': 0.20
        }
    else:
        # Weights without safety - redistribute safety weight
        weights = {
            'affordability': 0.22,  # +0.04
            'family_friendly': 0.23,  # +0.05  
            'economic_vitality': 0.20,  # +0.04
            'housing_stability': 0.16,  # +0.03
            'budget_compatibility': 0.19   # +0.04
        }
    
    # Adjust weights based on user priorities
    if user_priority.get("family"):
        weights['family_friendly'] += 0.10
        if has_safety:
            weights['safety'] += 0.10
        else:
            weights['affordability'] += 0.05  # Extra emphasis if no safety data
            weights['housing_stability'] += 0.05
        
        # Reduce other weights proportionally
        reduction_per_category = 0.20 / (len(weights) - 1 - (1 if has_safety else 0))
        for key in weights:
            if key not in ['family_friendly', 'safety']:
                weights[key] = max(0.05, weights[key] - reduction_per_category)
    
    if user_priority.get("growth"):
        weights['economic_vitality'] += 0.15
        # Reduce other weights proportionally
        reduction_per_category = 0.15 / (len(weights) - 1)
        for key in weights:
            if key != 'economic_vitality':
                weights[key] = max(0.05, weights[key] - reduction_per_category)
    
    # Tier-based weight adjustments
    if tier in ["luxury", "ultra_luxury"]:
        weights['budget_compatibility'] += 0.08
        if has_safety:
            weights['safety'] += 0.07
        weights['affordability'] = max(0.05, weights['affordability'] - 0.15)
    elif tier == "affordable":
        weights['affordability'] += 0.15
        weights['budget_compatibility'] = max(0.05, weights['budget_compatibility'] - 0.08)
        weights['economic_vitality'] = max(0.05, weights['economic_vitality'] - 0.07)
    
    # Normalize weights to sum to 1
    total_weight = sum(weights.values())
    weights = {k: v/total_weight for k, v in weights.items()}
    
    # Calculate weighted score using only available metrics
    final_score = sum(scores.get(metric, 50) * weight for metric, weight in weights.items() if metric in scores)
    return final_score

def get_lifestyle_description(county, scores):
    """Generate lifestyle description based on scores"""
    descriptions = []
    
    if scores['affordability'] >= 80:
        descriptions.append("excellent affordability")
    elif scores['affordability'] >= 60:
        descriptions.append("good value")
    
    if scores['family_friendly'] >= 80:
        descriptions.append("family-oriented community")
    elif scores['family_friendly'] >= 60:
        descriptions.append("family-friendly")
    
    if scores['economic_vitality'] >= 80:
        descriptions.append("strong local economy")
    elif scores['economic_vitality'] >= 60:
        descriptions.append("stable employment opportunities")
    
    # Safety indicators (only if available)
    if 'safety' in scores:
        if scores['safety'] >= 75:
            descriptions.append("very safe community")
        elif scores['safety'] >= 60:
            descriptions.append("safe neighborhood")
    
    return "; ".join(descriptions)

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

def detect_tier(user_budget):
    """Detect budget tier based on user budget"""
    if user_budget < 200000:
        return "affordable"
    elif user_budget < 500000:
        return "move_up"
    elif user_budget < 1000000:
        return "luxury"
    else:
        return "ultra_luxury"

def calculate_college_degree_rate(county):
    """Calculate college degree rate for a county"""
    try:
        total_pop = county.get('B15003_001E', 0)
        if total_pop == 0:
            return 0
        
        # Sum all bachelor's degree and higher
        college_plus = (
            county.get('B15003_022E', 0) +  # Bachelor's degree
            county.get('B15003_023E', 0) +  # Master's degree
            county.get('B15003_024E', 0) +  # Professional degree
            county.get('B15003_025E', 0)    # Doctorate degree
        )
        
        rate = (college_plus / total_pop) * 100
        return round(rate, 1)  # Round to 1 decimal place
    except:
        return 0

def calculate_state_medians(counties_data):
    """Calculate median values for a state"""
    if not counties_data:
        return {}
    
    home_values = [c.get('B25077_001E', 0) for c in counties_data if c.get('B25077_001E', 0) > 0]
    incomes = [c.get('B19013_001E', 0) for c in counties_data if c.get('B19013_001E', 0) > 0]
    populations = [c.get('B01003_001E', 0) for c in counties_data if c.get('B01003_001E', 0) > 0]
    
    return {
        "home_value": statistics.median(home_values) if home_values else 0,
        "income": statistics.median(incomes) if incomes else 0,
        "population": statistics.median(populations) if populations else 0
    }

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