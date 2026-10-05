import streamlit as st
import pandas as pd
import requests

API_URL = "https://api.rentcast.io/v1/listings/sale"
API_KEY = st.secrets["RENTCAST_API_KEY"]

st.set_page_config(page_title="Upstate NY Real Estate Tracker", layout="wide")
st.title("📍 Real-Time Pricing Dashboard")

with st.sidebar:
    st.header("⚙️ Settings & Activity")
    
    # Multi-select for surrounding areas
    zip_codes = st.multiselect("Zip Codes to Track", 
                               ["13421", "13461", "13476", "13478", "13322"], 
                               default=["13421", "13461"])
    
    st.markdown("---")
    st.subheader("🏠 My Property Details")
    my_price = st.number_input("My Current Price", value=289000, step=1000)
    my_sqft = st.number_input("My Square Footage", value=1800, step=50)
    my_dom = st.number_input("My Days on Market", value=21, step=1)
    
    # NEW: Condition tier selector with a Help Tooltip
    property_tier = st.selectbox(
        "My Home's Condition", 
        ["Average (Standard Comps)", "Premium / Renovated (Top 25% Comps)"],
        index=1,
        help="**Average:** Compares your home to the median (50th percentile) market values.\n\n**Premium:** Ignores fixer-uppers and compares your home only to the Top 25% (75th percentile) of the market. Use this if your home is newly renovated or highly upgraded."
    )
    # NEW: Permanent visible caption below the box
    st.caption("✨ *The Premium Tier evaluates your home against the top 25% of local properties, filtering out lower-end homes to accurately reflect recent renovations.*")
    
    st.markdown("---")
    st.subheader("🚶‍♂️ Foot Traffic")
    my_showings = st.number_input("Total Showings", value=4, step=1)
    my_open_houses = st.number_input("Total Open Houses", value=0, step=1)

@st.cache_data(ttl=3600)
def fetch_listings(status, key, zips):
    all_data = []
    headers = {"X-Api-Key": key, "accept": "application/json"}
    # Loop through each selected zip code to fetch data
    for z in zips:
        params = {"zipCode": z, "status": status, "propertyType": "Single Family", "limit": 100}
        response = requests.get(API_URL, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            if data:
                all_data.extend(data)
        else:
            st.error(f"API Error for {z} ({status}): {response.status_code}")
    return pd.DataFrame(all_data)

if not zip_codes:
    st.warning("Please select at least one zip code from the sidebar to begin.")
    st.stop()

with st.spinner("Fetching live MLS data..."):
    df_active = fetch_listings("Active", API_KEY, zip_codes)
    df_pending = fetch_listings("Pending", API_KEY, zip_codes)

if not df_active.empty and not df_pending.empty:
    
    # Clean data to ensure we have square footage to calculate against
    df_active = df_active.dropna(subset=['squareFootage'])
    df_pending = df_pending.dropna(subset=['squareFootage'])
    
    # Calculate Price per SqFt for the market
    df_active['price_per_sqft'] = df_active['price'] / df_active['squareFootage']
    df_pending['price_per_sqft'] = df_pending['price'] / df_pending['squareFootage']
    
    my_ppsqft = my_price / my_sqft if my_sqft > 0 else 0
    
    # Adjust target metrics based on the selected Property Tier
    if "Premium" in property_tier:
        target_price = df_active['price'].quantile(0.75)
        target_ppsqft = df_active['price_per_sqft'].quantile(0.75)
        tier_label = "Top 25% (Premium)"
    else:
        target_price = df_active['price'].median()
        target_ppsqft = df_active['price_per_sqft'].median()
        tier_label = "Median (Average)"
        
    median_dom = df_active['daysOnMarket'].median()
    stale_threshold = median_dom * 1.5
    
    # --- Top Metrics Row ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(f"Active Comps ({len(zip_codes)} Zips)", len(df_active))
    col2.metric(f"{tier_label} Active Price", f"${target_price:,.0f}")
    col3.metric("Pending Comps", len(df_pending))
    col4.metric(f"{tier_label} Pending Price", f"${df_pending['price'].quantile(0.75) if 'Premium' in property_tier else df_pending['price'].median():,.0f}")
    
    st.divider()
    
    # --- Premium Pricing Analysis ---
    st.subheader("💎 Premium Pricing Analysis")
    col_p1, col_p2, col_p3 = st.columns(3)
    col_p1.metric("My Price / SqFt", f"${my_ppsqft:,.0f}")
    col_p2.metric(f"Market {tier_label} Price / SqFt", f"${target_ppsqft:,.0f}")
    
    ppsqft_diff = my_ppsqft - target_ppsqft
    
    if ppsqft_diff > 10:
        status_ppsqft = "⚠️ Overpriced per SqFt"
    elif ppsqft_diff >= -10:
        status_ppsqft = "✅ Competitively Priced"
    else:
        status_ppsqft = "🔥 Underpriced per SqFt"
        
    col_p3.info(f"**Value Status:** {status_ppsqft}")
    
    st.divider()
    
    # --- Advanced Data-Driven Decision Matrix ---
    st.subheader("🧠 Data-Driven Strategy")
    showings_per_week = (my_showings / my_dom) * 7 if my_dom > 0 else 0
    
    if my_showings >= 10:
        status_text = "🟡 Price/Condition Mismatch"
        action_text = "You hit the 'No Offer Milestone' (10+ showings). Despite the premium renovations, buyers are rejecting the final price tag. Consider dropping 3-5%."
    elif my_dom >= 14 and my_showings < 3:
        status_text = "🔴 Dead Showing Threshold"
        action_text = "Fewer than 3 showings in 2+ weeks. The market might not value the renovations as highly as the premium price suggests. Drop 5-10% to reset."
    elif my_dom > stale_threshold:
        status_text = "🔴 Stale Listing"
        action_text = f"You are significantly past the market median DOM ({median_dom} days). Drop price 5-10% immediately."
    elif my_dom > median_dom:
        status_text = "🟡 Market Shift Warning"
        action_text = f"You've crossed the median DOM ({median_dom} days). If showing traffic is slowing down, consider a small drop to stay competitive."
    else:
        status_text = "🟢 On Track"
        action_text = f"Hold price. You are averaging {showings_per_week:.1f} showings per week, which is healthy."

    colA, colB, colC = st.columns(3)
    colA.metric("My DOM vs. Median", f"{my_dom} Days", delta=f"{my_dom - median_dom} days from Median", delta_color="inverse")
    colB.metric("Foot Traffic", f"{my_showings} Showings", delta=f"{my_open_houses} Open Houses", delta_color="off")
    colC.metric("Pace", f"{showings_per_week:.1f} / week")
    
    st.info(f"**Action Plan:** {status_text} — {action_text}")
    
    st.divider()
    
    # --- Data Tables ---
    st.subheader("Active Competitors")
    st.dataframe(df_active[['formattedAddress', 'price', 'price_per_sqft', 'daysOnMarket', 'bedrooms', 'squareFootage']].sort_values('price'))
    
    st.subheader("Pending Sales")
    st.dataframe(df_pending[['formattedAddress', 'price', 'price_per_sqft', 'daysOnMarket', 'bedrooms', 'squareFootage']].sort_values('price'))
else:
    st.warning("No active or pending listings found. Please check the API connection.")
