import streamlit as st
import pandas as pd
import requests

ZIP_CODE = "13421"
API_URL = "https://api.rentcast.io/v1/listings/sale"
API_KEY = st.secrets["RENTCAST_API_KEY"]

st.set_page_config(page_title="Oneida Real Estate Tracker", layout="wide")
st.title(f"📍 Real-Time Pricing Dashboard: Oneida, NY ({ZIP_CODE})")

with st.sidebar:
    st.header("⚙️ Settings & Activity")
    my_price = st.number_input("My Current Price", value=289000, step=1000)
    my_dom = st.number_input("My Days on Market", value=21, step=1)
    
    st.markdown("---")
    st.subheader("🚶‍♂️ Foot Traffic")
    my_showings = st.number_input("Total Showings", value=4, step=1)
    my_open_houses = st.number_input("Total Open Houses", value=0, step=1)
    
    st.markdown("---")
    st.markdown("**Target Property:**\n71 Seneca Ave\nOneida, NY")

@st.cache_data(ttl=3600)
def fetch_listings(status, key):
    headers = {"X-Api-Key": key, "accept": "application/json"}
    params = {"zipCode": ZIP_CODE, "status": status, "propertyType": "Single Family", "limit": 150}
    response = requests.get(API_URL, headers=headers, params=params)
    
    if response.status_code == 200:
        return pd.DataFrame(response.json())
    else:
        st.error(f"API Error for {status} listings: {response.status_code} - {response.text}")
        return pd.DataFrame()

with st.spinner("Fetching live MLS data..."):
    df_active = fetch_listings("Active", API_KEY)
    df_pending = fetch_listings("Pending", API_KEY)
    df_sold = fetch_listings("Sold", API_KEY)

if not df_active.empty and not df_pending.empty:
    median_dom = df_active['daysOnMarket'].median()
    stale_threshold = median_dom * 1.5
    
    # --- Top Metrics Row ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Active Single-Family", len(df_active))
    col2.metric("Median Active Price", f"${df_active['price'].median():,.0f}")
    col3.metric("Pending Comps", len(df_pending))
    col4.metric("Median Pending Price", f"${df_pending['price'].median():,.0f}")
    
    st.divider()
    
    # --- Market Velocity & Pricing Health ---
    st.subheader("📊 Market Velocity & Pricing Health")
    col_v1, col_v2, col_v3 = st.columns(3)
    
    if not df_sold.empty:
        absorption_rate = (len(df_sold) / len(df_active)) * 100
        if absorption_rate > 20:
            abs_status = "🔥 Seller's Market"
        elif absorption_rate < 15:
            abs_status = "🧊 Buyer's Market"
        else:
            abs_status = "⚖️ Balanced Market"
            
        col_v1.metric("Absorption Rate", f"{absorption_rate:.1f}%", delta=abs_status, delta_color="off")
        
        if 'originalPrice' in df_sold.columns:
            valid_sales = df_sold.dropna(subset=['price', 'originalPrice'])
            if len(valid_sales) > 0:
                lts_ratio = (valid_sales['price'] / valid_sales['originalPrice']).median() * 100
                col_v2.metric("Median List-to-Sale Ratio", f"{lts_ratio:.1f}%", help="100% means homes sell exactly at asking price.")
            else:
                col_v2.metric("List-to-Sale Ratio", "N/A")
        else:
            col_v2.metric("List-to-Sale Ratio", "N/A")
            
        col_v3.metric("Recently Sold Homes", len(df_sold))
    else:
        st.info("No recent 'Sold' data available in this zip code to calculate Market Velocity.")

    st.divider()
    
    # --- Advanced Data-Driven Decision Matrix ---
    st.subheader("🧠 71 Seneca Ave: Data-Driven Strategy")
    
    # Calculate showing pace
    showings_per_week = (my_showings / my_dom) * 7 if my_dom > 0 else 0
    
    # Decision Engine Logic
    if my_showings >= 10:
        status_text = "🟡 Price/Condition Mismatch"
        action_text = "You hit the 'No Offer Milestone' (10+ showings). Buyers like the listing online but reject the price/value ratio in person. Drop 3-5%."
    elif my_dom >= 14 and my_showings < 3:
        status_text = "🔴 Dead Showing Threshold"
        action_text = "Fewer than 3 showings in 2+ weeks signals severe market rejection. Immediate 5-10% drop required to reset the buyer pool."
    elif my_dom > stale_threshold:
        status_text = "🔴 Stale Listing"
        action_text = f"You are significantly past the market median DOM ({median_dom} days). Drop price 5-10% immediately."
    elif my_dom > median_dom:
        status_text = "🟡 Market Shift Warning"
        action_text = f"You've crossed the median DOM ({median_dom} days). If showing traffic is slowing down, consider a 3% drop to stay competitive."
    else:
        status_text = "🟢 On Track"
        action_text = f"Hold price. You are averaging {showings_per_week:.1f} showings per week, which is healthy early in the listing cycle."

    # Display Strategy Output
    colA, colB, colC = st.columns(3)
    colA.metric("My DOM vs. Median", f"{my_dom} Days", 
                delta=f"{my_dom - median_dom} days from Median", delta_color="inverse")
    colB.metric("Foot Traffic", f"{my_showings} Showings", 
                delta=f"{my_open_houses} Open Houses", delta_color="off")
    colC.metric("Pace", f"{showings_per_week:.1f} / week")
    
    st.info(f"**Action Plan:** {status_text} — {action_text}")
    
    st.divider()
    
    # --- Data Tables ---
    st.subheader("Active Competitors")
    st.dataframe(df_active[['formattedAddress', 'price', 'daysOnMarket', 'bedrooms', 'squareFootage']].sort_values('price'))
    
    st.subheader("Pending Sales")
    st.dataframe(df_pending[['formattedAddress', 'price', 'daysOnMarket', 'bedrooms', 'squareFootage']].sort_values('price'))
else:
    st.warning("No active or pending listings found. Please check the API connection.")
