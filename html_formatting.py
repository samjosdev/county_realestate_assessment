from datetime import datetime
from data_sources.image_apis import get_county_images
import markdown

def clean_markdown_to_html(text):
    """Convert markdown formatting to clean HTML using the markdown package"""
    if not text:
        return ""
    # Convert markdown to HTML
    html = markdown.markdown(text)
    return html

def calculate_homeownership_rate(county):
    """Calculate homeownership rate and return formatted string"""
    owner_occupied = county.get('B25003_002E', 0)
    total_households = county.get('B25003_001E', 0)
    
    if total_households > 0:
        rate = (owner_occupied / total_households) * 100
        return f"{rate:.1f}%"
    return "N/A"

def get_safety_display_data(county):
    """Extract and format safety data for display. Returns None if no crime data available."""
    crime_data = county.get('crime_data')
    
    # If no crime data, return None to indicate it should be omitted
    if not crime_data:
        return None
        
    safety_score = crime_data.get('overall_safety_score')
    safety_tier = crime_data.get('safety_tier', 'Unknown')
    family_rating = crime_data.get('family_friendly_rating', 'Unknown')
    
    # Determine color and badge class
    if isinstance(safety_score, (int, float)):
        if safety_score >= 75:
            color = "#22c55e"  # Green
            badge_class = "safety-excellent-badge"
            color_class = "safety-excellent"
        elif safety_score >= 60:
            color = "#84cc16"  # Light green
            badge_class = "safety-good-badge"
            color_class = "safety-good"
        elif safety_score >= 45:
            color = "#f59e0b"  # Orange
            badge_class = "safety-moderate-badge"
            color_class = "safety-moderate"
        else:
            color = "#ef4444"  # Red
            badge_class = "safety-concern-badge"
            color_class = "safety-concern"
    else:
        color = "#6b7280"  # Gray
        badge_class = "safety-unknown-badge"
        color_class = "safety-unknown"
    
    return {
        'score': safety_score,
        'tier': safety_tier,
        'rating': family_rating,
        'color': color,
        'badge_class': badge_class,
        'color_class': color_class
    }

def format_single_state_html_report(state_name, income, counties, insights, recommendation):
    """Format the complete single state report as professional HTML with optional crime data"""
    date = datetime.now().strftime("%B %d, %Y")
    
    # Check if any counties have crime data to determine if we should show crime columns
    has_crime_data = any(county.get('crime_data') for county in counties[:5])
    
    # Enhanced CSS with comprehensive safety styling (only if needed)
    crime_css = '''
    /* Safety score styling */
    .safety-excellent .stat-value {
        color: #22c55e !important;
        font-weight: 600;
    }
    .safety-good .stat-value {
        color: #84cc16 !important;
        font-weight: 600;
    }
    .safety-moderate .stat-value {
        color: #f59e0b !important;
        font-weight: 600;
    }
    .safety-concern .stat-value {
        color: #ef4444 !important;
        font-weight: 600;
    }
    .safety-unknown .stat-value {
        color: #6b7280 !important;
    }
    
    .safety-badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 0.8em;
        font-weight: 500;
        margin-top: 8px;
        margin-left: 8px;
    }
    
    .safety-excellent-badge {
        background: #dcfce7;
        color: #166534;
    }
    
    .safety-good-badge {
        background: #ecfdf5;
        color: #14532d;
    }
    
    .safety-moderate-badge {
        background: #fef3c7;
        color: #92400e;
    }
    
    .safety-concern-badge {
        background: #fee2e2;
        color: #991b1b;
    }
    
    .safety-unknown-badge {
        background: #f3f4f6;
        color: #374151;
    }
    ''' if has_crime_data else ''
    
    enhanced_css = f'''
    <style>
    .professional-report h1, .professional-report h2, .professional-report h3, .professional-report h4 {{
        margin-top: 1.2em;
        margin-bottom: 0.5em;
        font-weight: bold;
    }}
    .professional-report p {{
        margin: 0.5em 0;
    }}
    .professional-report ul, .professional-report ol {{
        margin: 0.5em 0 0.5em 2em;
    }}
    .professional-report li {{
        margin-bottom: 0.3em;
    }}
    .professional-report table {{
        border-collapse: collapse;
        width: 100%;
        margin: 1em 0;
    }}
    .professional-report th, .professional-report td {{
        border: 1px solid #ddd;
        padding: 8px;
        text-align: left;
    }}
    .professional-report th {{
        background-color: #f2f2f2;
    }}
    
    /* Enhanced stat grid for metrics */
    .stats-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 12px;
        margin: 20px 0;
    }}
    
    .county-header {{
        display: flex;
        align-items: center;
        margin-bottom: 20px;
        flex-wrap: wrap;
    }}
    
    {crime_css}
    </style>
    '''
    
    # Clean the insights and recommendations
    clean_insights = clean_markdown_to_html(insights)
    clean_recommendation = clean_markdown_to_html(recommendation)
    
    # Generate county cards with conditional crime data
    county_cards_html = ""
    used_urls = set()
    
    for i, county in enumerate(counties[:5], 1):
        county_name = county['name']
        county_seat = county.get('county_seat')
        
        # Get images
        image_urls = get_county_images(county_name, state_name, county_seat, used_urls)
        for url, _ in image_urls:
            used_urls.add(url)
        
        # Generate image HTML
        images_html = ""
        for url, source in image_urls[:10]:
            if url and url.strip().lower().startswith('http'):
                images_html += f'<img src="{url}" alt="{county_name}" class="county-image" onerror="this.style.display=\'none\';" />'
        
        # County statistics
        home_value = county.get('B25077_001E', 0)
        household_income = county.get('B19013_001E', 0)
        population = county.get('B01003_001E', 0)
        homeownership = calculate_homeownership_rate(county)
        college_rate = county.get('college_degree_rate', 0)
        
        # Safety data (optional)
        safety_data = get_safety_display_data(county)
        
        # Build stats grid with conditional safety info
        stats_items = f'''
                <div class="stat-item">
                    <div class="stat-label">Median Home Value</div>
                    <div class="stat-value">${home_value:,}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Household Income</div>
                    <div class="stat-value">${household_income:,}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Population</div>
                    <div class="stat-value">{population:,}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Homeownership Rate</div>
                    <div class="stat-value">{homeownership}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">College Degree Rate</div>
                    <div class="stat-value">{college_rate}%</div>
                </div>'''
        
        # Add safety stat only if available
        if safety_data:
            stats_items += f'''
                <div class="stat-item {safety_data['color_class']}">
                    <div class="stat-label">Safety Score</div>
                    <div class="stat-value">{safety_data['score']}</div>
                </div>'''
        
        # County description with conditional safety info
        notable_feature = county.get('tags', {}).get('notable_family_feature', 'Great community for families')
        
        # Build header with conditional safety badge
        header_content = f'''
                <div class="county-rank">{i}</div>
                <h3 class="county-name">{county_name}</h3>'''
        
        if safety_data:
            header_content += f'<div class="safety-badge {safety_data["badge_class"]}">{safety_data["tier"]}</div>'
        
        # Build description with conditional safety info
        description_content = f'<strong>Why you\'ll love it:</strong> {notable_feature}'
        if safety_data:
            description_content += f'<br><strong>Family Safety:</strong> {safety_data["rating"]}'
        
        county_cards_html += f"""
        <div class="county-card">
            <div class="county-header">
                {header_content}
            </div>
            
            <div class="county-images">
                {images_html}
            </div>
            
            <div class="stats-grid">
                {stats_items}
            </div>
            
            <div class="county-description">
                {description_content}
            </div>
        </div>
        """
    
    # Generate insights section with conditional safety disclaimer
    safety_disclaimer = '' if has_crime_data else ''
    
    insights_html = f"""
    <div class="insights-section">
        <h3>💡 Key Insights</h3>
        <div class="insights-content">
            {clean_insights if clean_insights else '<p>Our analysis shows excellent opportunities for your family in the identified counties based on your budget and preferences.</p>'}
        </div>
        
        <h3>✨ Our Recommendation</h3>
        <div class="recommendation-content">
            {clean_recommendation if clean_recommendation else '<p>Focus your search on the top-ranked counties which offer the best combination of value, family amenities, and investment potential.</p>'}
        </div>
        
        {safety_disclaimer}
    </div>
    """
    
    # Complete HTML report
    html_report = f"""
    {enhanced_css}
    <div class="professional-report">
        <div class="report-header">
            <h1>🏡 {state_name} Real Estate Report</h1>
            <p class="subtitle">Family-Focused Analysis for ${income} Budget • Generated {date}</p>
        </div>
        
        <div class="report-content">
            <h2>🏆 Top Counties for Your Family</h2>
            <p>Based on your budget, family needs, and lifestyle preferences, here are the best counties in {state_name}:</p>
            
            {county_cards_html}
            
            {insights_html}
            
            <div class="report-footer">
                <p><small>📊 Data Sources: 2022 U.S. Census ACS • Images: Unsplash, Pexels, Wikipedia</small></p>
            </div>
        </div>
    </div>
    """
    
    return html_report

def format_comparison_html_report(name1, name2, income, counties1, counties2, insights, recommendation):
    """Format the comparison report with optional crime data"""
    date = datetime.now().strftime("%B %d, %Y")
    
    # Check if any counties have crime data
    has_crime_data = any(county.get('crime_data') for county in counties1[:3] + counties2[:3])
    
    # Enhanced CSS for comparison with optional safety data
    crime_css = '''
    .safety-score-display {
        font-weight: 600;
    }
    
    .safety-excellent { color: #22c55e !important; }
    .safety-good { color: #84cc16 !important; }
    .safety-moderate { color: #f59e0b !important; }
    .safety-concern { color: #ef4444 !important; }
    .safety-unknown { color: #6b7280 !important; }
    
    .safety-badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 0.8em;
        font-weight: 500;
        margin-top: 8px;
    }
    
    .safety-excellent-badge {
        background: #dcfce7;
        color: #166534;
    }
    
    .safety-good-badge {
        background: #ecfdf5;
        color: #14532d;
    }
    
    .safety-moderate-badge {
        background: #fef3c7;
        color: #92400e;
    }
    
    .safety-concern-badge {
        background: #fee2e2;
        color: #991b1b;
    }
    
    .safety-unknown-badge {
        background: #f3f4f6;
        color: #374151;
    }
    ''' if has_crime_data else ''
    
    enhanced_comparison_css = f'''
    <style>
    .professional-report h1, .professional-report h2, .professional-report h3, .professional-report h4 {{
        margin-top: 1.2em;
        margin-bottom: 0.5em;
        font-weight: bold;
    }}
    .professional-report p {{
        margin: 0.5em 0;
    }}
    .professional-report ul, .professional-report ol {{
        margin: 0.5em 0 0.5em 2em;
    }}
    .professional-report li {{
        margin-bottom: 0.3em;
    }}
    
    /* Enhanced comparison table styling with optional safety */
    .comparison-container {{
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        padding: 24px;
        border-radius: 16px;
        margin: 24px 0;
        border: 1px solid #e2e8f0;
    }}
    
    .comparison-grid {{
        display: grid;
        grid-template-columns: auto 1fr 1fr;
        gap: 16px;
        align-items: center;
    }}
    
    .comparison-rank {{
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
    }}
    
    .state-section {{
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        border: 1px solid #e5e7eb;
    }}
    
    .state-header {{
        font-size: 1.1em;
        font-weight: 600;
        color: #1e293b;
        margin-bottom: 8px;
        padding-bottom: 8px;
        border-bottom: 2px solid #e5e7eb;
    }}
    
    .county-name {{
        font-size: 1em;
        font-weight: 500;
        color: #374151;
        margin-bottom: 12px;
    }}
    
    .quick-stats {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
    }}
    
    .quick-stat {{
        text-align: center;
    }}
    
    .quick-stat-label {{
        font-size: 0.75em;
        color: #6b7280;
        margin-bottom: 4px;
        text-transform: uppercase;
        font-weight: 500;
        letter-spacing: 0.5px;
    }}
    
    .quick-stat-value {{
        font-size: 0.95em;
        font-weight: 600;
        color: #1f2937;
    }}
    
    .vs-divider {{
        text-align: center;
        margin: 24px 0;
        position: relative;
    }}
    
    .vs-divider::before {{
        content: '';
        position: absolute;
        top: 50%;
        left: 0;
        right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, #d1d5db, transparent);
    }}
    
    .vs-text {{
        background: white;
        padding: 8px 16px;
        font-weight: 600;
        color: #6b7280;
        border-radius: 20px;
        border: 1px solid #e5e7eb;
        display: inline-block;
    }}
    
    .safety-disclaimer {{
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #3b82f6;
        padding: 16px;
        margin: 24px 0;
        border-radius: 8px;
    }}
    
    .safety-disclaimer h4 {{
        margin-top: 0;
        color: #1e293b;
    }}
    
    {crime_css}
    
    @media (max-width: 768px) {{
        .comparison-grid {{
            grid-template-columns: 1fr;
            text-align: center;
        }}
        .comparison-rank {{
            grid-row: span 1;
            margin: 0 auto;
        }}
        .quick-stats {{
            grid-template-columns: 1fr;
        }}
    }}
    </style>
    '''
    
    # Clean the insights and recommendations
    clean_insights = clean_markdown_to_html(insights)
    clean_recommendation = clean_markdown_to_html(recommendation)
    
    # Generate improved comparison section
    comparison_html = ""
    used_urls = set()
    
    max_counties = max(len(counties1), len(counties2))
    for i in range(min(3, max_counties)):  # Top 3 from each state
        county1 = counties1[i] if i < len(counties1) else None
        county2 = counties2[i] if i < len(counties2) else None
        
        rank = i + 1
        
        # County 1 data
        if county1:
            name1_county = county1['name']
            home1 = f"${county1.get('B25077_001E', 0):,}"
            income1 = f"${county1.get('B19013_001E', 0):,}"
            homeownership1 = calculate_homeownership_rate(county1)
            safety1_data = get_safety_display_data(county1)
        else:
            name1_county = "—"
            home1 = income1 = homeownership1 = "—"
            safety1_data = None
        
        # County 2 data
        if county2:
            name2_county = county2['name']
            home2 = f"${county2.get('B25077_001E', 0):,}"
            income2 = f"${county2.get('B19013_001E', 0):,}"
            homeownership2 = calculate_homeownership_rate(county2)
            safety2_data = get_safety_display_data(county2)
        else:
            name2_county = "—"
            home2 = income2 = homeownership2 = "—"
            safety2_data = None
        
        # Build stat grids with conditional safety info
        stats1 = f'''
                        <div class="quick-stat">
                            <div class="quick-stat-label">Home Value</div>
                            <div class="quick-stat-value">{home1}</div>
                        </div>
                        <div class="quick-stat">
                            <div class="quick-stat-label">Income</div>
                            <div class="quick-stat-value">{income1}</div>
                        </div>
                        <div class="quick-stat">
                            <div class="quick-stat-label">Homeownership</div>
                            <div class="quick-stat-value">{homeownership1}</div>
                        </div>'''
        
        if safety1_data:
            stats1 += f'''
                        <div class="quick-stat">
                            <div class="quick-stat-label">Safety Score</div>
                            <div class="quick-stat-value safety-score-display {safety1_data['color_class']}">{safety1_data['score']}</div>
                        </div>'''
        
        stats2 = f'''
                        <div class="quick-stat">
                            <div class="quick-stat-label">Home Value</div>
                            <div class="quick-stat-value">{home2}</div>
                        </div>
                        <div class="quick-stat">
                            <div class="quick-stat-label">Income</div>
                            <div class="quick-stat-value">{income2}</div>
                        </div>
                        <div class="quick-stat">
                            <div class="quick-stat-label">Homeownership</div>
                            <div class="quick-stat-value">{homeownership2}</div>
                        </div>'''
        
        if safety2_data:
            stats2 += f'''
                        <div class="quick-stat">
                            <div class="quick-stat-label">Safety Score</div>
                            <div class="quick-stat-value safety-score-display {safety2_data['color_class']}">{safety2_data['score']}</div>
                        </div>'''
        
        comparison_html += f"""
        <div class="comparison-container">
            <div class="comparison-grid">
                <div class="comparison-rank">#{rank}</div>
                
                <div class="state-section">
                    <div class="state-header">{name1}</div>
                    <div class="county-name">{name1_county}</div>
                    <div class="quick-stats">
                        {stats1}
                    </div>
                </div>
                
                <div class="state-section">
                    <div class="state-header">{name2}</div>
                    <div class="county-name">{name2_county}</div>
                    <div class="quick-stats">
                        {stats2}
                    </div>
                </div>
            </div>
        </div>
        """
        
        # Add VS divider between items (except after the last one)
        if i < min(3, max_counties) - 1:
            comparison_html += '<div class="vs-divider"><span class="vs-text">VS</span></div>'
    
    # Generate detailed county sections
    counties1_html = generate_state_counties_html(name1, counties1[:3], used_urls)
    counties2_html = generate_state_counties_html(name2, counties2[:3], used_urls)
    
    # Safety disclaimer
    safety_disclaimer = ''
    
    # Complete HTML report
    html_report = f"""
    {enhanced_comparison_css}
    <div class="professional-report">
        <div class="report-header">
            <h1>🏡 {name1} vs {name2}</h1>
            <p class="subtitle">State Comparison Analysis for ${income} Budget • Generated {date}</p>
        </div>
        
        <div class="report-content">
            <h2>📊 Quick Comparison</h2>
            {comparison_html}
            
            <h2>🏆 Top Counties in {name1}</h2>
            {counties1_html}
            
            <h2>🌟 Top Counties in {name2}</h2>
            {counties2_html}
            
            <div class="insights-section">
                <h3>💡 Key Takeaways</h3>
                <div class="insights-content">
                    {clean_insights if clean_insights else '<p>Both states offer unique advantages for your family and budget.</p>'}
                </div>
                
                <h3>✨ Our Recommendation</h3>
                <div class="recommendation-content">
                    {clean_recommendation if clean_recommendation else '<p>Consider visiting the top counties in both states to find the best fit for your family needs.</p>'}
                </div>
                
                {safety_disclaimer}
            </div>
            
            <div class="report-footer">
                <p><small>📊 Data Sources: 2022 U.S. Census ACS • Images: Unsplash, Pexels, Wikipedia</small></p>
            </div>
        </div>
    </div>
    """
    
    return html_report

def generate_state_counties_html(state_name, counties, used_urls):
    """Generate HTML for counties in a specific state with optional safety data"""
    counties_html = ""
    
    for i, county in enumerate(counties, 1):
        county_name = county['name']
        county_seat = county.get('county_seat')
        
        # Get images
        image_urls = get_county_images(county_name, state_name, county_seat, used_urls)
        for url, _ in image_urls:
            used_urls.add(url)
        
        # Generate image HTML
        images_html = ""
        for url, source in image_urls[:10]:
            if url and url.strip().lower().startswith('http'):
                images_html += f'<img src="{url}" alt="{county_name}" class="county-image" onerror="this.style.display=\'none\';" />'
        
        # County statistics
        home_value = county.get('B25077_001E', 0)
        household_income = county.get('B19013_001E', 0)
        population = county.get('B01003_001E', 0)
        homeownership = calculate_homeownership_rate(county)
        college_rate = county.get('college_degree_rate', 0)
        
        # Safety data (optional)
        safety_data = get_safety_display_data(county)
        
        # Build stats grid with conditional safety info
        stats_items = f'''
                <div class="stat-item">
                    <div class="stat-label">Median Home Value</div>
                    <div class="stat-value">${home_value:,}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Household Income</div>
                    <div class="stat-value">${household_income:,}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Population</div>
                    <div class="stat-value">{population:,}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Homeownership Rate</div>
                    <div class="stat-value">{homeownership}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">College Degree Rate</div>
                    <div class="stat-value">{college_rate}%</div>
                </div>'''
        
        # Add safety stat only if available
        if safety_data:
            stats_items += f'''
                <div class="stat-item {safety_data['color_class']}">
                    <div class="stat-label">Safety Score</div>
                    <div class="stat-value">{safety_data['score']}</div>
                </div>'''
        
        # County description with conditional safety info
        notable_feature = county.get('tags', {}).get('notable_family_feature', 'Great community for families')
        
        # Build header with conditional safety badge
        header_content = f'''
                <div class="county-rank">{i}</div>
                <h3 class="county-name">{county_name}</h3>'''
        
        if safety_data:
            header_content += f'<div class="safety-badge {safety_data["badge_class"]}">{safety_data["tier"]}</div>'
        
        # Build description with conditional safety info
        description_content = f'<strong>Why you\'ll love it:</strong> {notable_feature}'
        if safety_data:
            description_content += f'<br><strong>Family Safety:</strong> {safety_data["rating"]}'
        
        counties_html += f"""
        <div class="county-card">
            <div class="county-header">
                {header_content}
            </div>
            
            <div class="county-images">
                {images_html}
            </div>
            
            <div class="stats-grid">
                {stats_items}
            </div>
            
            <div class="county-description">
                {description_content}
            </div>
        </div>
        """
    
    return counties_html