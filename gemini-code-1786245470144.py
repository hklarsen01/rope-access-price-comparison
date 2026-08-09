import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re

st.set_page_config(page_title="Work & Rescue Competitor Price Tracker", page_icon="🪢", layout="wide")

st.title("🪢 Competitor Price Comparison Dashboard")
st.caption("Compare Work & Rescue prices against Maple Leaf Ropes, Pacific Ropes, and VPO.")

# --- Competitor Scraper Functions ---

def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

def clean_price(price_str):
    """Extract float value from price string like '$219.99 CAD'"""
    if not price_str:
        return None
    match = re.search(r'\d+[\.,]?\d*', price_str.replace(',', ''))
    return float(match.group()) if match else None

def search_maple_leaf_ropes(sku):
    url = f"https://www.mapleleafropes.com/search?q={sku}"
    try:
        res = requests.get(url, headers=get_headers(), timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            # Look for common price class containers
            price_tag = soup.find('span', class_=re.compile(r'price|amount', re.I))
            if price_tag:
                return clean_price(price_tag.text)
    except Exception:
        pass
    return None

def search_pacific_ropes(sku):
    url = f"https://shop.pacificropes.com/search?q={sku}"
    try:
        res = requests.get(url, headers=get_headers(), timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            price_tag = soup.find('span', class_=re.compile(r'price|amount', re.I))
            if price_tag:
                return clean_price(price_tag.text)
    except Exception:
        pass
    return None

def search_vpo(sku):
    url = f"https://vpo.ca/search?q={sku}"
    try:
        res = requests.get(url, headers=get_headers(), timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            price_tag = soup.find('span', class_=re.compile(r'price|amount|product-price', re.I))
            if price_tag:
                return clean_price(price_tag.text)
    except Exception:
        pass
    return None

# --- Main App Interface ---

st.sidebar.header("📁 Product Input")
input_method = st.sidebar.radio("Choose Input Method:", ["Manual Entry", "Upload WooCommerce CSV"])

products = []

if input_method == "Manual Entry":
    st.subheader("1. Enter Product Details")
    col1, col2, col3 = st.columns(3)
    with col1:
        p_name = st.text_input("Product Name", "Petzl RIG Descender")
    with col2:
        p_sku = st.text_input("SKU / Part Number", "D014BA00")
    with col3:
        p_price = st.number_input("Work & Rescue Price ($)", value=210.00, step=1.0)
    
    products.append({"title": p_name, "sku": p_sku, "work_price": p_price})

else:
    st.subheader("1. Upload WooCommerce Products Export")
    uploaded_file = st.file_uploader("Upload CSV (Must contain 'SKU', 'Name', and 'Regular price' columns)", type=["csv"])
    if uploaded_file:
        df_upload = pd.read_csv(uploaded_file)
        st.dataframe(df_upload.head(3))
        # Map columns
        sku_col = st.selectbox("Select SKU Column", df_upload.columns, index=0)
        name_col = st.selectbox("Select Name Column", df_upload.columns, index=1 if len(df_upload.columns) > 1 else 0)
        price_col = st.selectbox("Select Price Column", df_upload.columns, index=2 if len(df_upload.columns) > 2 else 0)
        
        for _, row in df_upload.dropna(subset=[sku_col]).iterrows():
            products.append({
                "title": str(row[name_col]),
                "sku": str(row[sku_col]),
                "work_price": float(row[price_col]) if pd.notnull(row[price_col]) else 0.0
            })

# --- Run Scraper ---
if st.button("🔍 Compare Competitor Prices", type="primary"):
    if not products:
        st.warning("Please enter or upload at least one product.")
    else:
        results = []
        progress_bar = st.progress(0)
        
        for idx, prod in enumerate(products):
            sku = prod["sku"]
            st.write(f"Checking SKU: `{sku}` ({prod['title']})...")
            
            mlr_price = search_maple_leaf_ropes(sku)
            pac_price = search_pacific_ropes(sku)
            vpo_price = search_vpo(sku)
            
            competitor_prices = [p for p in [mlr_price, pac_price, vpo_price] if p is not None]
            min_competitor = min(competitor_prices) if competitor_prices else None
            
            # Status calculation
            status = "No Competitor Found"
            if min_competitor:
                if prod["work_price"] < min_competitor:
                    status = "✅ Cheapest"
                elif prod["work_price"] == min_competitor:
                    status = "➖ Matched"
                else:
                    status = "⚠️ Higher Than Competitor"

            results.append({
                "SKU": sku,
                "Product Name": prod["title"],
                "Work & Rescue ($)": f"${prod['work_price']:.2f}",
                "Maple Leaf Ropes ($)": f"${mlr_price:.2f}" if mlr_price else "N/A",
                "Pacific Ropes ($)": f"${pac_price:.2f}" if pac_price else "N/A",
                "VPO ($)": f"${vpo_price:.2f}" if vpo_price else "N/A",
                "Status": status
            })
            
            progress_bar.progress((idx + 1) / len(products))

        st.divider()
        st.subheader("2. Comparison Matrix")
        df_results = pd.DataFrame(results)
        st.dataframe(df_results, use_container_width=True)