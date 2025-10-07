import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime

# config
API_KEY = "89AE4B206C2A492A9D605554CAF2D453"  # BlueCart API key
API_URL = "https://api.bluecartapi.com/request"

# setup
st.set_page_config(page_title="Walmart Product Extractor", layout="centered")
st.title("🛒 Walmart Product Data Extractor")
st.write(
    "Enter one or more Walmart product IDs (comma-separated) to fetch price, brand, and manufacturing info."
)

# inputs
ids_input = st.text_area(
    "Enter Product IDs (comma-separated):",
    placeholder="e.g., 155568127, 27672251",
)
fetch_button = st.button("Fetch Product Data")


# fetching function
def fetch_product(item_id):
    """Fetch product info from BlueCart API — retry indefinitely until success."""
    params = {"api_key": API_KEY, "type": "product", "item_id": item_id}
    attempt = 0
    delay = 5  # start with 5 seconds

    while True:
        attempt += 1
        try:
            response = requests.get(API_URL, params=params, timeout=None)
            data = response.json()

            # check if valid data
            if data.get("product"):
                product = data.get("product", {})
                buybox = product.get("buybox_winner", {}) or {}
                seller = buybox.get("seller", {}) or {}
                location = data.get("location_info", {}) or {}
                specs = {
                    s.get("name"): s.get("value")
                    for s in product.get("specifications", [])
                    if isinstance(s, dict)
                }

                manufacturer = (
                    specs.get("Manufacturer")
                    or specs.get("Brand")
                    or product.get("brand")
                )

                # build flat record
                return {
                    "extraction_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "product_id": product.get("item_id"),
                    "product_title": product.get("title"),
                    "brand": product.get("brand"),
                    "manufacturer": manufacturer,
                    "price": buybox.get("price"),
                    "currency": buybox.get("currency_symbol"),
                    "seller": seller.get("name"),
                    "availability": buybox.get("availability", {}).get("raw")
                    if isinstance(buybox.get("availability"), dict)
                    else None,
                    "rating": product.get("rating"),
                    "ratings_total": product.get("ratings_total"),
                    "product_link": product.get("link"),
                    "location_city": location.get("city"),
                    "location_state": location.get("state"),
                    "location_zipcode": location.get("zipcode"),
                }

            # no data yet → wait and retry
            else:
                st.warning(
                    f"⚠️ No product data found for ID {item_id} (Attempt {attempt}). Retrying in {delay}s..."
                )
                time.sleep(delay)
                delay = min(delay * 2, 60)  # exponential backoff
                continue

        except Exception as e:
            st.warning(
                f"⏱️ Attempt {attempt}: Error fetching {item_id}: {e} — retrying in {delay}s..."
            )
            time.sleep(delay)
            delay = min(delay * 2, 60)
            continue


# handle button click
if fetch_button:
    if not ids_input.strip():
        st.warning("⚠️ Please enter at least one product ID.")
    else:
        item_ids = [x.strip() for x in ids_input.split(",") if x.strip()]
        st.info(f"Fetching data for {len(item_ids)} product(s)...")

        results = []
        progress = st.progress(0)

        for i, item_id in enumerate(item_ids, start=1):
            st.write(f"🔍 Fetching product ID: {item_id} ...")
            product_data = fetch_product(item_id)
            if product_data:
                results.append(product_data)
                st.success(f"✅ Successfully fetched data for {item_id}")
            time.sleep(1)  # small delay between items
            progress.progress(i / len(item_ids))

        if results:
            df = pd.DataFrame(results)
            st.success(f"🎯 Successfully fetched {len(df)} of {len(item_ids)} products.")
            st.dataframe(df)

            # csv download
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"walmart_products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )
        else:
            st.error("❌ No product data fetched. Please check IDs or API key.")
