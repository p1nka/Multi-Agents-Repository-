import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.title("CBUAE Dormancy Checker (Simplified - Last Txn Date Based)")

uploaded_file = st.file_uploader("Upload CBUAE Dormancy Dataset", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file, parse_dates=["Last Transaction Date"])
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    # Rename for consistency
    df.rename(columns={
        "account_id": "account_id",
        "account_type": "account_type",
        "last_transaction_date": "last_transaction_date",
        "customer_type": "customer_type",
        "account_balance": "account_balance",
        "account_status": "existing_account_status"
    }, inplace=True)

    # Filter only 'Savings/Call/Current' accounts
    target_accounts = df[df["account_type"].str.lower() == "savings/call/current"].copy()

    # Define dormancy
    dormancy_period = timedelta(days=3*365)
    today = datetime.today()

    target_accounts["dormant_since"] = target_accounts["last_transaction_date"] + dormancy_period
    target_accounts["is_dormant"] = target_accounts["last_transaction_date"].apply(
        lambda x: (today - x) >= dormancy_period
    )

    dormant_accounts = target_accounts[target_accounts["is_dormant"]]

    st.subheader("Dormant Accounts (No customer-initiated transaction for 3+ years)")
    st.dataframe(dormant_accounts[[
        "account_id", "customer_type", "account_balance", "last_transaction_date", "dormant_since"
    ]])

    csv = dormant_accounts.to_csv(index=False).encode("utf-8")
    st.download_button("Download Dormant Accounts", csv, "dormant_accounts.csv", "text/csv")
else:
    st.info("Please upload the CBUAE Compliance dataset to begin.")

