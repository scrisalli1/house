import streamlit as st
import pandas as pd
import requests

ZIP_CODE = "13421"
API_URL = "https://api.rentcast.io/v1/listings/sale"

# This securely pulls your API key from the Streamlit Secrets box
API_KEY = st.secrets["RENTCAST_API_KEY"]

st.set_page_config(page_title="Oneida Real Estate Tracker", layout="wide")
st.title(f"📍 Real-Time Pricing Dashboard: Oneida, NY ({ZIP_CODE})")

with st.sidebar:
    st.header("⚙️ Settings")
    my_price = st.number_input("My Current Price", value=289000, step=1000)
    my_dom = st.number_input("My Days on Market", value=21, step=1)
    st.markdown("---")
    st.markdown("**Target Property:**\n71 Seneca Ave\nOneida, NY")

@st.cache_data(ttl=3600)
def fetch_listings(status, key):
    headers = {"X-Api-Key": key, "accept": "application/json"}
    params = {"zipCode": ZIP_CODE, "status": status, "propertyType": "Single Family", "limit": 100}
    response = requests.get(API_URL, headers=headers, params=params)
    
    if response.status_code == 200:
        return pd.DataFrame(response.json())
    else:
        # This will print the exact error directly on your dashboard if the API fails
        st.error(f"API Error for {status} listings: {response.status_code} - {response.text}")
        return pd.DataFrame()

with st.spinner("Fetching live MLS data..."):
    df_active = fetch_listings("Active", API_KEY)
    df_pending = fetch_listings("Pending", API_KEY)

if not df_active.empty and not df_pending.empty:
    median_dom = df_active['daysOnMarket'].median()
    stale_threshold = median_dom * 1.5
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Active Single-Family Comps", len(df_active))
    col2.metric("Median Active Price", f"${df_active['price'].median():,.0f}")
    col3.metric("Pending Comps", len(df_pending))
    col4.metric("Median Pending Price", f"${df_pending['price'].median():,.0f}")
    
    st.subheader("⏱️ 71 Seneca Ave: Status Matrix")
    
    if my_dom < median_dom:
        status_text = "🟢 On Track"
        action_text = "Hold price unless showings are dead (under 3 in 14 days)."
    elif my_dom < stale_threshold:
        status_text = "🟡 Market Shift Warning"
        action_text = "Consider a 3-5% drop to align with pending sales."
    else:
        status_text = "🔴 Stale Listing"
        action_text = "Immediate 5-10% drop required to reset buyer pool."

    colA, colB, colC = st.columns(3)
    colA.metric("My DOM vs. Median", f"{my_dom} Days", 
                delta=f"{my_dom - median_dom} days from Median", delta_color="inverse")
    colB.metric("Status", status_text)
    colC.info(action_text)
    
    st.divider()
    
    st.subheader("Active Competitors")
    st.dataframe(df_active[['formattedAddress', 'price', 'daysOnMarket', 'bedrooms', 'squareFootage']].sort_values('price'))
    
    st.subheader("Pending Sales")
    st.dataframe(df_pending[['formattedAddress', 'price', 'daysOnMarket', 'bedrooms', 'squareFootage']].sort_values('price'))
else:
    st.warning("No listings found. Please check the red error messages above if the API connection failed.")
