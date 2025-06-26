import streamlit as st
import mysql.connector
import pandas as pd
from io import StringIO
from datetime import date, timedelta
import io

import json

host = st.secrets["mysql"]["host"]
user = st.secrets["mysql"]["user"]
password = st.secrets["mysql"]["password"]
database = st.secrets["mysql"]["database"]

valid_users = json.loads(st.secrets["app"]["valid_users_json"])
# --- Streamlit app ---
st.title("MySQL Data Downloader")

# --- Login form ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    with st.form("login_form"):
        username = st.text_input("Username")
        password_input = st.text_input("Password", type="password")
        login_btn = st.form_submit_button("Login")

        if login_btn:
            if username in valid_users and valid_users[username] == password_input:
                st.session_state["authenticated"] = True
                st.success(f"Welcome, {username}!")
                st.session_state["username"] = username
                st.session_state["password_input"] = None  # Clear stored password
            else:
                st.error("Invalid username or password.")
if st.session_state["authenticated"]:
    st.header("Filters")

    # Default yesterday date range
    yesterday = date.today() - timedelta(days=1)

    # Mapping display names to table names
    table_options = {
        "Google Ads Ecom": "report_ecom_google_ads",
        "Facebook Ads Ecom": "report_ecom_facebook_ads",
        "Tiktok Ads Ecom": "report_ecom_tiktok_ads",
        "Lazada Discovery Campaign": "lazada_discovery_campaign_daily",
        "Lazada Discovery KW": "lazada_discovery_kw_daily",
        "Lazada Discovery Product": "lazada_discovery_product_daily"
    }

    with st.form("filter_form"):
        c1, c2 = st.columns(2)

        # Show display names in multiselect
        selected_display_tables = c1.multiselect(
            "Tables",
            options=list(table_options.keys())
        )

        date_range = c2.date_input(
            "Date Range",
            (yesterday, yesterday)  # default to yesterday
        )

        submitted = st.form_submit_button("Fetch Data")

    if submitted:
        try:
            conn = mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                database=database
            )

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                for display_name in selected_display_tables:
                    table = table_options[display_name]  # get actual table name

                    query = f"SELECT * FROM {table}"
                    if date_range and len(date_range) == 2:
                        start_date = date_range[0]
                        end_date = date_range[1]
                        query += f" WHERE report_date BETWEEN '{start_date}' AND '{end_date}'"

                    df = pd.read_sql(query, conn)
                    st.success(f"✅ {display_name}: Retrieved {len(df)} rows.")
                    st.dataframe(df, use_container_width=True)

                    df.to_excel(writer, index=False, sheet_name=display_name[:31])

            output.seek(0)
            st.download_button(
                label="⬇ Download XLSX",
                data=output,
                file_name="multi_table_filtered.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except mysql.connector.Error as e:
            st.error(f"Database error: {e}")
        except Exception as ex:
            st.error(f"Error: {ex}")
        finally:
            try:
                conn.close()
            except:
                pass
