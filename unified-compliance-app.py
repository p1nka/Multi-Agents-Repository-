import os
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
from langchain_groq import ChatGroq
from langchain.chains import ConversationChain, LLMChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from fpdf import FPDF

# === Authentication ===
def login():
    st.sidebar.title("🔐 Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        if username == "admin" and password == "pass123":
            st.session_state.logged_in = True
        else:
            st.sidebar.error("Invalid username or password")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login()
    st.stop()

# === App Setup ===
st.set_page_config(page_title="Unified Banking Compliance Solution", layout="wide")

# === Load LLM ===
@st.cache_resource(show_spinner=False)
def load_llm():
    os.environ["GROQ_API_KEY"] = "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"  # Replace with your actual key
    return ChatGroq(temperature=0.3, model_name="llama3-70b-8192")

llm = load_llm()

# === Database Setup ===
def init_db():
    conn = sqlite3.connect("unified_compliance.db")
    cursor = conn.cursor()
    # Dormant flag table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dormant_flags (
            account_id TEXT PRIMARY KEY,
            flag_instruction TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Dormant ledger table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dormant_ledger (
            account_id TEXT PRIMARY KEY,
            classification TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Insight log table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS insight_log (
            timestamp TEXT,
            observation TEXT,
            trend TEXT,
            insight TEXT,
            action TEXT
        )
    """)
    conn.commit()
    return conn

conn = init_db()

# === File Upload ===
uploaded_file = st.sidebar.file_uploader("Upload Account Dataset (CSV)", type="csv")

@st.cache_data(show_spinner=False)
def parse_csv(file):
    df = pd.read_csv(file)
    df['Last Transaction Date'] = pd.to_datetime(df['Last Transaction Date'], errors='coerce')
    return df

def save_to_db(df, table_name="accounts_data"):
    conn = sqlite3.connect("unified_compliance.db")
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.close()

def save_summary_to_db(observation, trend, insight, action):
    conn = sqlite3.connect("unified_compliance.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO insight_log VALUES (?, ?, ?, ?, ?)",
                   (datetime.now().isoformat(), observation, trend, insight, action))
    conn.commit()
    conn.close()

# === Main App Mode Selection ===
app_mode = st.sidebar.selectbox("Select Application Mode", [
    "🏦 Dormant Account Analyzer", 
    "🔒 Compliance Multi-Agent"
])

st.title(f"{app_mode}")

if uploaded_file:
    df = parse_csv(uploaded_file)
    save_to_db(df)
    st.success("Dataset uploaded successfully!")
    
    # === DORMANT ACCOUNT ANALYZER MODE ===
    if app_mode == "🏦 Dormant Account Analyzer":
        threshold = datetime.now() - timedelta(days=3 * 365)
        
        agent_option = st.selectbox("🧭 Choose Dormant Detection Agent", [
            "🔐 Safe Deposit Box Agent",
            "💼 Investment Inactivity Agent",
            "🏦 Fixed Deposit Agent",
            "📉 3-Year General Inactivity Agent",
            "📵 Unreachable + No Active Accounts Agent"
        ])

        if agent_option == "🔐 Safe Deposit Box Agent":
            data = df[(df['Account Type'].str.contains("Safe Deposit", case=False, na=False)) &
                    (df['Last Transaction Date'] < threshold) &
                    (df['Email Contact Attempt'].str.lower() == 'no') &
                    (df['SMS Contact Attempt'].str.lower() == 'no') &
                    (df['Phone Call Attempt'].str.lower() == 'no')]
        elif agent_option == "💼 Investment Inactivity Agent":
            data = df[(df['Account Type'].str.contains("Investment", case=False, na=False)) &
                    (df['Last Transaction Date'] < threshold) &
                    (df['Email Contact Attempt'].str.lower() == 'no') &
                    (df['SMS Contact Attempt'].str.lower() == 'no') &
                    (df['Phone Call Attempt'].str.lower() == 'no')]
        elif agent_option == "🏦 Fixed Deposit Agent":
            data = df[(df['Account Type'].str.lower() == 'fixed deposit') & (df['Last Transaction Date'] < threshold)]
        elif agent_option == "📉 3-Year General Inactivity Agent":
            data = df[(df['Account Type'].isin(["Savings", "Call", "Current"])) & (df['Last Transaction Date'] < threshold)]
        else:
            data = df[(df['Email Contact Attempt'].str.lower() == 'no') &
                    (df['SMS Contact Attempt'].str.lower() == 'no') &
                    (df['Phone Call Attempt'].str.lower() == 'no') &
                    (df['Account Status'].str.lower() == 'dormant')]

        st.success(f"{len(data)} accounts detected. Data stored for compliance processing.")
        st.dataframe(data.head(15))
        
        # === Multi-Agent Insight Chains ===
        sample_data = data.sample(n=min(15, len(data))).to_csv(index=False)

        observation_prompt = PromptTemplate(
            input_variables=["data"],
            template="""
            You are a senior bank analyst. Provide insights on:
            - 📈 Dormancy Trends
            - 🔁 Activity Shift
            - 🏦 Branch-Level Observations
            - 🧍‍♂️ Customer Segments
            - ⚠️ Risk Pockets
            - 💰 Balance Irregularities

            Data:
            {data}

            Output only observations.
            """
        )
        trend_prompt = PromptTemplate(
            input_variables=["data"],
            template="""
            You are a data strategist. Analyze the following:
            - 📉 Dormancy Risk Movement
            - 🧭 Key Contributors
            - 🧮 Change Metrics

            Data:
            {data}

            Output analytical narrative only.
            """
        )
        narration_prompt = PromptTemplate(
            input_variables=["observation", "trend"],
            template="""
            You are writing a CXO summary.

            🔎 Observation:
            {observation}

            📊 Trend:
            {trend}

            Output a polished executive summary.
            """
        )
        action_prompt = PromptTemplate(
            input_variables=["observation", "trend"],
            template="""
            You are a strategic advisor. Based on:
            🔎 Observation:
            {observation}

            📊 Trend:
            {trend}

            Suggest actionable steps to reduce dormancy and risk.
            """
        )

        obs_chain = LLMChain(llm=llm, prompt=observation_prompt)
        trend_chain = LLMChain(llm=llm, prompt=trend_prompt)
        narration_chain = LLMChain(llm=llm, prompt=narration_prompt)
        action_chain = LLMChain(llm=llm, prompt=action_prompt)

        with st.spinner("Running insight agents..."):
            obs_output = obs_chain.run(data=sample_data)
            trend_output = trend_chain.run(data=sample_data)
            final_insight = narration_chain.run(observation=obs_output, trend=trend_output)
            action_output = action_chain.run(observation=obs_output, trend=trend_output)

        save_summary_to_db(obs_output, trend_output, final_insight, action_output)

        with st.expander("🔍 Observation Insight"):
            st.markdown(obs_output)
        with st.expander("📊 Trend Insight"):
            st.markdown(trend_output)
        with st.expander("📌 CXO Summary"):
            st.markdown(final_insight)
        with st.expander("🚀 Recommended Actions"):
            st.markdown(action_output)

        # PDF Export
        if st.button("📄 Download Executive Summary PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.multi_cell(0, 10, "Executive Summary Report")
            pdf.multi_cell(0, 10, f"Observation:\n{obs_output}")
            pdf.multi_cell(0, 10, f"Trend:\n{trend_output}")
            pdf.multi_cell(0, 10, f"Insight:\n{final_insight}")
            pdf.multi_cell(0, 10, f"Action Plan:\n{action_output}")
            pdf_path = "executive_summary.pdf"
            pdf.output(pdf_path)
            with open(pdf_path, "rb") as f:
                st.download_button("Download PDF", f, file_name="executive_summary.pdf")
    
    # === COMPLIANCE MULTI-AGENT MODE ===
    elif app_mode == "🔒 Compliance Multi-Agent":
        agent = st.selectbox("Select Compliance Agent", [
            "📨 Contact Attempt Agent",
            "🚩 Flag Dormant Agent",
            "📘 Dormant Ledger Agent",
            "❄️ Freeze Account Agent",
            "🏦 Transfer to CBUAE Agent"
        ])

        output_df = pd.DataFrame()

        if agent == "📨 Contact Attempt Agent":
            results = []
            for _, row in df.iterrows():
                channels = []
                if str(row.get("Email Contact Attempt", "")).strip().lower() == "yes":
                    channels.append("Email")
                if str(row.get("SMS Contact Attempt", "")).strip().lower() == "yes":
                    channels.append("SMS")
                if str(row.get("Phone Call Attempt", "")).strip().lower() == "yes":
                    channels.append("Phone Call")
                results.append({
                    "Account ID": row.get("Account ID"),
                    "Channels Used": ", ".join(channels) or "None",
                    "Contact Attempt Status": "Pass" if len(channels) == 3 else "Fail"
                })
            output_df = pd.DataFrame(results)
            st.subheader("📨 Contact Attempt Agent")
            st.dataframe(output_df)
            st.markdown(f"**Summary:** {len(output_df)} accounts processed. {len(output_df[output_df['Contact Attempt Status'] == 'Pass'])} passed.")
            st.markdown("- Retry contact for failed attempts\n- Verify communication data\n- Automate follow-ups")

        elif agent == "🚩 Flag Dormant Agent":
            cursor = conn.cursor()
            results = []
            for _, row in df.iterrows():
                status = str(row.get("Account Status", "")).strip().lower()
                if status == "dormant" or not row.get("Last Transaction Date"):
                    acc_id = row["Account ID"]
                    results.append({"Account ID": acc_id, "Flag Update Instruction": "Apply Dormancy Flag"})
                    cursor.execute("INSERT OR REPLACE INTO dormant_flags (account_id, flag_instruction) VALUES (?, ?)", 
                                  (acc_id, "Apply Dormancy Flag"))
            conn.commit()
            output_df = pd.DataFrame(results)
            st.subheader("🚩 Flag Dormant Agent")
            st.dataframe(output_df)
            st.markdown(f"**Summary:** {len(output_df)} accounts flagged as dormant.")
            st.markdown("- Apply flags in system\n- Notify clients\n- Log and audit actions")

        elif agent == "📘 Dormant Ledger Agent":
            cursor = conn.cursor()
            results = []
            for _, row in df.iterrows():
                if str(row.get("Account Status", "")).strip().lower() == "dormant":
                    acc_id = row["Account ID"]
                    results.append({"Account ID": acc_id, "Ledger Reclassification": "Move to Internal Dormant Ledger"})
                    cursor.execute("INSERT OR REPLACE INTO dormant_ledger (account_id, classification) VALUES (?, ?)", 
                                  (acc_id, "Moved to Dormant Ledger"))
            conn.commit()
            output_df = pd.DataFrame(results)
            st.subheader("📘 Dormant Ledger Agent")
            st.dataframe(output_df)
            st.markdown(f"**Summary:** {len(output_df)} accounts moved to dormant ledger.")
            st.markdown("- Maintain internal classification\n- Use for audit purposes\n- Review yearly")

        elif agent == "❄️ Freeze Account Agent":
            df["Freeze Status"] = df.apply(
                lambda row: "Frozen" if row.get("Account Status", "").lower() == "dormant" and 
                            pd.to_datetime(row.get("Last Transaction Date")) < pd.to_datetime("2022-01-01") and 
                            row.get("KYC Status", "").lower() == "expired" else "Active",
                axis=1
            )
            output_df = df[df["Freeze Status"] == "Frozen"]
            st.subheader("❄️ Freeze Account Agent")
            st.dataframe(output_df[["Account ID", "Account Type", "Branch", "Freeze Status"]])
            st.markdown(f"**Summary:** {len(output_df)} accounts frozen.")
            st.markdown("- Restrict withdrawals\n- Trigger KYC update\n- Notify stakeholders")

        elif agent == "🏦 Transfer to CBUAE Agent":
            cutoff = datetime.strptime("2020-04-24", "%Y-%m-%d")
            df["Transfer Status"] = df["Last Transaction Date"].apply(
                lambda d: "Eligible for Transfer" if pd.notna(d) and d <= cutoff else "Not Eligible"
            )
            output_df = df[df["Transfer Status"] == "Eligible for Transfer"]
            st.subheader("🏦 Transfer to CBUAE Agent")
            st.dataframe(output_df[["Account ID", "Account Type", "Branch", "Transfer Status"]])
            st.markdown(f"**Summary:** {len(output_df)} accounts eligible for central bank transfer.")
            st.markdown("- Prepare documentation\n- Coordinate with CBUAE\n- Archive data")

        if not output_df.empty:
            csv = output_df.to_csv(index=False).encode("utf-8")
            st.download_button("📁 Download Agent Output", data=csv, file_name="compliance_output.csv", mime="text/csv")

# === Chatbot Section (Available in both modes) ===
st.subheader("💬 Ask Compliance Bot")
user_input = st.text_input("Ask a question:")

if "chatbot_memory" not in st.session_state:
    # Fix: Make sure memory uses the right key that matches what the prompt expects
    st.session_state.chatbot_memory = ConversationBufferMemory(memory_key="chat_history")

if "chatbot_chain" not in st.session_state:
    prompt_template = PromptTemplate(
        input_variables=["chat_history", "input"],
        template="""
        You are a banking compliance assistant with expertise in dormant accounts, regulatory compliance, 
        and account management. Use the chat history and your knowledge to answer questions about:
        
        - Dormancy detection and management
        - Account flagging and reclassification
        - Regulatory compliance requirements
        - Best practices for dormant accounts
        - Contact requirements
        - Risk management
        
        Chat History:
        {chat_history}
        
        Human: {input}
        AI: """
    )
    
    st.session_state.chatbot_chain = ConversationChain(
        llm=llm,
        prompt=prompt_template,
        memory=st.session_state.chatbot_memory,
        verbose=False
    )

if user_input:
    response = st.session_state.chatbot_chain.run(input=user_input)
    st.markdown(f"**Bot:** {response}")

# Show database status
st.sidebar.subheader("Database Status")
conn = sqlite3.connect("unified_compliance.db")
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM dormant_flags")
flag_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM dormant_ledger")
ledger_count = cursor.fetchone()[0]
cursor.execute("SELECT COUNT(*) FROM insight_log")
insight_count = cursor.fetchone()[0]
conn.close()

st.sidebar.info(f"""
📊 System Status:
- Dormant Flags: {flag_count}
- Ledger Entries: {ledger_count}
- Insight Records: {insight_count}
""")
