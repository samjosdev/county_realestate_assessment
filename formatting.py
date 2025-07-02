from datetime import datetime

# Handle numpy import gracefully
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

def safe_val(val, default="[N/A]"):
    """Safely format values for display in tables"""
    return f"${val:,}" if isinstance(val, int) else (val if val else default)

def calc_state_summary(counties, metrics=("B25077_001E", "B19013_001E", "college_degree_rate", "tags")):
    """
    Returns median/average metrics for a state's top counties.
    """
    def mean(values):
        return sum(values) / len(values) if values else 0
    
    def median(values):
        if not values:
            return 0
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        if n % 2 == 0:
            return (sorted_vals[n//2 - 1] + sorted_vals[n//2]) / 2
        else:
            return sorted_vals[n//2]
    
    summary = {}
    if not counties:
        return {m: None for m in metrics}
    for m in metrics:
        values = [c.get(m, 0) for c in counties if c.get(m, 0)]
        if not values:
            summary[m] = None
        else:
            if m == "tags":
                # For tags like homeownership rate, use average of available
                rates = [c.get("tags", {}).get("homeownership_rate", None) for c in counties if c.get("tags", {}).get("homeownership_rate") is not None]
                if HAS_NUMPY and rates:
                    summary["homeownership_rate"] = round(np.mean(rates), 1)
                elif rates:
                    summary["homeownership_rate"] = round(mean(rates), 1)
                else:
                    summary["homeownership_rate"] = None
            elif m == "college_degree_rate":
                if HAS_NUMPY:
                    summary[m] = round(np.mean(values), 1)
                else:
                    summary[m] = round(mean(values), 1)
            else:
                if HAS_NUMPY:
                    summary[m] = int(np.median(values))
                else:
                    summary[m] = int(median(values))
    return summary

def format_comparison_summary_table(name1, name2, counties1, counties2):
    """Format the state-by-state summary table for comparison reports using medians/averages"""
    # Use top 3-5 counties for each metric for better luxury/affluent targeting
    s1 = calc_state_summary(counties1[:5])
    s2 = calc_state_summary(counties2[:5])

    def pretty(val):
        if val is None:
            return "—"
        if isinstance(val, (float, int)):
            return f"${val:,}" if val > 1000 else f"{val}%"
        return str(val)
    return (
        f"| Metric | {name1} | {name2} | Winner/Notes |\n"
        f"|--------|---------|---------|---------------|\n"
        f"| Median Home Value | {pretty(s1.get('B25077_001E'))} | {pretty(s2.get('B25077_001E'))} | Lower is better (affordability) |\n"
        f"| Median Household Income | {pretty(s1.get('B19013_001E'))} | {pretty(s2.get('B19013_001E'))} | |\n"
        f"| Homeownership Rate | {pretty(s1.get('homeownership_rate'))} | {pretty(s2.get('homeownership_rate'))} | |\n"
        f"| Top County (Family Focus) | {counties1[0]['name'] if counties1 else '—'} | {counties2[0]['name'] if counties2 else '—'} | |\n"
        f"| Avg. School Quality* | {pretty(s1.get('college_degree_rate'))} | {pretty(s2.get('college_degree_rate'))} | (proxy: college grad rate) |\n"
        f"| Population (Top County) | {pretty(counties1[0]['B01003_001E']) if counties1 else '—'} | {pretty(counties2[0]['B01003_001E']) if counties2 else '—'} | |\n"
    )

def format_county_table(counties):
    """Format county data as a markdown table"""
    lines = "| Rank | County | Median Home Value | HH Income | College Degree Rate | Notable Feature |\n"
    lines += "|------|--------|-------------------|-----------|-------------------|------------------|\n"
    for i, county in enumerate(counties[:3], 1):
        college_rate = county.get('college_degree_rate', 0)
        college_rate_str = f"{college_rate}%" if college_rate > 0 else "N/A"
        notable_feature = county.get('tags', {}).get('notable_family_feature', 'Solid housing options')
        lines += (
            f"| {i} | {county['name']} | "
            f"${county.get('B25077_001E', 0):,} | "
            f"${county.get('B19013_001E', 0):,} | "
            f"{college_rate_str} | "
            f"{notable_feature} |\n"
        )
    return lines

def format_single_state_table(counties):
    """Format county data for single state reports as a markdown table"""
    lines = "| Rank | County | Median Home Value | HH Income | H.O. Rate | College Degree Rate | Pop. | Summary |\n"
    lines += "|------|--------|-------------------|-----------|-----------|-------------------|------|----------|\n"
    for i, county in enumerate(counties[:5], 1):
        homeownership = county.get('tags', {}).get('homeownership_rate')
        homeownership_str = f"{homeownership}%" if homeownership is not None else "N/A"
        college_rate = county.get('college_degree_rate', 0)
        college_rate_str = f"{college_rate}%" if college_rate > 0 else "N/A"
        summary = get_county_summary(county)
        lines += (
            f"| {i} | {county['name']} | "
            f"${county.get('B25077_001E', 0):,} | "
            f"${county.get('B19013_001E', 0):,} | "
            f"{homeownership_str} | "
            f"{college_rate_str} | "
            f"{county.get('B01003_001E', 0):,} | "
            f"{summary} |\n"
        )
    return lines

def get_county_summary(county):
    """Generate a short emoji summary for a county"""
    tags = county.get("tags", {})
    population = county.get("B01003_001E", 0)
    community_type = tags.get("community_type", "")
    
    if population > 500000:
        return "🌆 Big-city energy + opportunities"
    elif population > 300000:
        if community_type == "suburban":
            return "🛍️ Suburban balance & job access"
        else:
            return "🎭 Diverse, vibrant urban living"
    elif population > 100000:
        if tags.get("family_friendly"):
            return "🧸 Family-friendly community hub"
        else:
            return "🏘️ Growing suburban lifestyle"
    elif population > 50000:
        if tags.get("budget_friendly"):
            return "🧸 Affordable + family-friendly"
        else:
            return "🏞️ Small-town charm with amenities"
    else:
        return "🏞️ Rural calm with solid income"

def format_comparison_report(name1, name2, income, counties1, counties2, insights, recommendation):
    """Format the complete comparison report"""
    date = datetime.now().strftime("%B %d, %Y")
    summary_table = format_comparison_summary_table(name1, name2, counties1, counties2)
    
    final_report = f"""🏡 Residential Homebuyer State Comparison Report

**Comparing:** {name1} vs. {name2}  
**Criteria:** Family of Four, ${income} Annual Income  
**Date:** {date}

## 🏆 State-by-State Summary Table

{summary_table}

## 🥇 Top 3 Counties in Each State for Families

### {name1}
{format_county_table(counties1)}

### {name2}
{format_county_table(counties2)}

## 💡 Key Takeaways

{insights}

## ✨ Recommendation

{recommendation}
"""
    return final_report

def format_single_state_report(state_name, income, counties, insights, recommendation):
    """Format the complete single state report"""
    date = datetime.now().strftime("%B %d, %Y")
    state_emoji = get_state_emoji(state_name)
    
    final_report = f"""{state_emoji} Where {state_name} Families Thrive: Top 5 Counties for ${income} Buyers
🏡 Smart & Safe — {state_name}'s Best Family Havens on a ${income} Budget
Date: {date}

🏆 Top 5 Counties for Homebuyers in {state_name}

{format_single_state_table(counties)}

💡 Key Insights
{insights}

✨ Recommendations
{recommendation}

ℹ️ About This Data
*Latest U.S. Census ACS estimates. College Degree Rate serves as a proxy for school quality and educational environment. For detailed school ratings and neighborhood specifics, consult local resources.*
"""
    return final_report

def get_state_emoji(state_name):
    """Get an emoji that represents the state"""
    state_emojis = {
        "Oregon": "🌲",
        "California": "☀️", 
        "Washington": "🏔️",
        "Florida": "🌴",
        "Texas": "🤠",
        "New York": "🗽",
        "Colorado": "⛰️",
        "Arizona": "🌵",
        "Nevada": "🎰",
        "Utah": "🏔️",
        "Idaho": "🏞️",
        "Montana": "🦬",
        "Wyoming": "🐎",
        "North Dakota": "🌾",
        "South Dakota": "🦅",
        "Nebraska": "🌽",
        "Kansas": "🌻",
        "Oklahoma": "🛢️",
        "Arkansas": "🦆",
        "Louisiana": "🐊",
        "Mississippi": "🎺",
        "Alabama": "🏈",
        "Tennessee": "🎸",
        "Kentucky": "🐎",
        "West Virginia": "⛰️",
        "Virginia": "🏛️",
        "North Carolina": "🏖️",
        "South Carolina": "🏖️",
        "Georgia": "🍑",
        "Maine": "🦞",
        "New Hampshire": "🍂",
        "Vermont": "🍁",
        "Massachusetts": "⚓",
        "Rhode Island": "⛵",
        "Connecticut": "🍂",
        "New Jersey": "🌊",
        "Pennsylvania": "🔔",
        "Delaware": "🏖️",
        "Maryland": "🦀",
        "Ohio": "🏭",
        "Michigan": "🚗",
        "Indiana": "🏁",
        "Illinois": "🌆",
        "Wisconsin": "🧀",
        "Minnesota": "❄️",
        "Iowa": "🌽",
        "Missouri": "🎺",
        "Alaska": "🐻",
        "Hawaii": "🌺"
    }
    return state_emojis.get(state_name, "🏡") 