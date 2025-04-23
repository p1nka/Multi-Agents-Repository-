import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta
import io
import base64


class AccountInactivityChecker:
    """
    A class to identify savings, call, and current accounts that have been inactive
    for 3 consecutive years (no customer-initiated transactions).
    Specifically adapted for CBUAE_Compliance_Dormant_Dataset.csv format.
    """

    def __init__(self):
        """Initialize the checker"""
        self.accounts_df = None
        self.inactive_accounts = None
        self.today = datetime.now()

    def load_account_data(self, accounts_file):
        """Load account data from an uploaded file"""
        try:
            # Load accounts data
            self.accounts_df = pd.read_csv(accounts_file)

            # Convert Last Transaction Date to datetime
            self.accounts_df['Last Transaction Date'] = pd.to_datetime(self.accounts_df['Last Transaction Date'])

            return True
        except Exception as e:
            st.error(f"Error loading account data: {str(e)}")
            return False

    def identify_inactive_accounts(self, inactivity_years, account_types):
        """
        Identify accounts that have been inactive for the specified period.
        """
        if self.accounts_df is None:
            st.error("Error: Account data not loaded.")
            return None

        # Calculate the cutoff date
        cutoff_date = self.today - timedelta(days=inactivity_years * 365)

        # Filter accounts based on type and inactivity period
        inactive_accounts = self.accounts_df[
            (self.accounts_df['Account Type'].isin(account_types)) &
            (self.accounts_df['Last Transaction Date'] < cutoff_date)
            ].copy()

        # Add inactivity duration information
        inactive_accounts['days_inactive'] = (self.today - inactive_accounts['Last Transaction Date']).dt.days
        inactive_accounts['years_inactive'] = inactive_accounts['days_inactive'] / 365
        inactive_accounts['years_inactive'] = inactive_accounts['years_inactive'].round(2)

        # Sort by inactivity duration
        inactive_accounts = inactive_accounts.sort_values('days_inactive', ascending=False)

        self.inactive_accounts = inactive_accounts
        return inactive_accounts

    def mark_for_compliance_action(self, notify_years, freeze_years, escalate_years):
        """
        Mark inactive accounts for appropriate compliance action.

        Parameters:
        -----------
        notify_years : float
            Years of inactivity required for NOTIFY action
        freeze_years : float
            Years of inactivity required for FREEZE action
        escalate_years : float
            Years of inactivity required for ESCALATE action

        Returns:
        --------
        pandas.DataFrame
            DataFrame with recommended compliance actions
        """
        if self.inactive_accounts is None or self.inactive_accounts.empty:
            st.warning("No inactive accounts to mark for compliance action.")
            return None

        # Make a copy to avoid SettingWithCopyWarning
        result_df = self.inactive_accounts.copy()

        # Define compliance action based on inactivity duration
        def determine_action(years_inactive):
            if years_inactive > escalate_years:
                return 'ESCALATE'
            elif years_inactive > freeze_years:
                return 'FREEZE'
            elif years_inactive > notify_years:
                return 'NOTIFY'
            else:
                return 'MONITOR'

        result_df['recommended_action'] = result_df['years_inactive'].apply(determine_action)

        # Add contact status
        def determine_contact_status(row):
            attempts = 0
            if row['Email Contact Attempt'] == 'Yes':
                attempts += 1
            if row['SMS Contact Attempt'] == 'Yes':
                attempts += 1
            if row['Phone Call Attempt'] == 'Yes':
                attempts += 1

            if attempts == 0:
                return 'No Contact'
            elif attempts < 3:
                return 'Partial Contact'
            else:
                return 'Full Contact'

        result_df['contact_status'] = result_df.apply(determine_contact_status, axis=1)

        # Add risk category based on account balance
        def determine_risk(balance):
            if balance > 300000:
                return 'HIGH'
            elif balance > 100000:
                return 'MEDIUM'
            else:
                return 'LOW'

        result_df['risk_category'] = result_df['Account Balance'].apply(determine_risk)

        # Add compliance priority based on risk and inactivity
        def determine_priority(row):
            risk_score = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
            action_score = {'ESCALATE': 3, 'FREEZE': 2, 'NOTIFY': 1, 'MONITOR': 0}
            kyc_score = 2 if row['KYC Status'] == 'Expired' else 0

            total_score = risk_score.get(row['risk_category'], 0) + action_score.get(row['recommended_action'],
                                                                                     0) + kyc_score

            if total_score >= 6:
                return 'CRITICAL'
            elif total_score >= 4:
                return 'HIGH'
            elif total_score >= 2:
                return 'MEDIUM'
            else:
                return 'LOW'

        result_df['compliance_priority'] = result_df.apply(determine_priority, axis=1)

        return result_df

    def get_summary_stats(self):
        """Get summary statistics for the inactive accounts"""
        if self.inactive_accounts is None or self.inactive_accounts.empty:
            return None

        summary = {}

        # Count by account type
        summary['type_counts'] = self.inactive_accounts['Account Type'].value_counts().to_dict()

        # Count by branch
        summary['branch_counts'] = self.inactive_accounts['Branch'].value_counts().to_dict()

        # Count by customer type
        summary['customer_type_counts'] = self.inactive_accounts['Customer Type'].value_counts().to_dict()

        # Count by KYC status
        summary['kyc_status_counts'] = self.inactive_accounts['KYC Status'].value_counts().to_dict()

        # Count by recommended action
        if 'recommended_action' in self.inactive_accounts.columns:
            summary['action_counts'] = self.inactive_accounts['recommended_action'].value_counts().to_dict()

        # Count by risk category
        if 'risk_category' in self.inactive_accounts.columns:
            summary['risk_counts'] = self.inactive_accounts['risk_category'].value_counts().to_dict()

        # Count by compliance priority
        if 'compliance_priority' in self.inactive_accounts.columns:
            summary['priority_counts'] = self.inactive_accounts['compliance_priority'].value_counts().to_dict()

        # Count by contact status
        if 'contact_status' in self.inactive_accounts.columns:
            summary['contact_counts'] = self.inactive_accounts['contact_status'].value_counts().to_dict()

        # Calculate statistics for account balance
        summary['avg_balance'] = self.inactive_accounts['Account Balance'].mean()
        summary['total_balance'] = self.inactive_accounts['Account Balance'].sum()
        summary['max_balance'] = self.inactive_accounts['Account Balance'].max()
        summary['min_balance'] = self.inactive_accounts['Account Balance'].min()

        return summary


def get_download_link(df, filename, text):
    """Generate a download link for a dataframe"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}.csv">{text}</a>'
    return href


def main():
    # Set page title and layout
    st.set_page_config(
        page_title="CBUAE Dormant Account Checker",
        page_icon="💰",
        layout="wide",
    )

    # Create sidebar
    st.sidebar.title("CBUAE Dormant Account Checker")
    st.sidebar.markdown("Identify and analyze dormant accounts as per CBUAE requirements.")

    # Initialize session state
    if 'checker' not in st.session_state:
        st.session_state.checker = AccountInactivityChecker()
    if 'results' not in st.session_state:
        st.session_state.results = None
    if 'compliance_results' not in st.session_state:
        st.session_state.compliance_results = None
    if 'summary_stats' not in st.session_state:
        st.session_state.summary_stats = None

    # Main app
    st.title("CBUAE Dormant Account Checker")
    st.markdown("Upload your account data to identify dormant accounts and generate compliance reports.")

    # File upload section
    with st.sidebar.expander("📤 Upload Data", expanded=True):
        accounts_file = st.file_uploader("Upload CBUAE Dormant Account CSV", type=['csv'])

    # Parameters section
    with st.sidebar.expander("⚙️ Configure Parameters", expanded=True):
        # Set parameter defaults
        inactivity_years = st.slider("Inactivity Period (Years)", min_value=1.0, max_value=10.0, value=3.0, step=0.5)

        # Account types to check
        all_account_types = ["Savings/Call/Current", "Fixed Deposit", "Investment", "Safe Deposit"]
        account_types = st.multiselect(
            "Account Types to Check",
            options=all_account_types,
            default=["Savings/Call/Current"]
        )

    # Compliance parameters
    with st.sidebar.expander("🔍 Compliance Parameters", expanded=True):
        notify_years = st.number_input("Years for NOTIFY Action", min_value=1.0, max_value=10.0, value=3.0, step=0.5)
        freeze_years = st.number_input("Years for FREEZE Action", min_value=1.0, max_value=10.0, value=4.0, step=0.5)
        escalate_years = st.number_input("Years for ESCALATE Action", min_value=1.0, max_value=10.0, value=5.0,
                                         step=0.5)

    # Process data if file is uploaded
    if accounts_file:
        checker = st.session_state.checker

        # Load data
        if checker.load_account_data(accounts_file):
            st.sidebar.success("Data loaded successfully!")

            # Run analysis button
            if st.sidebar.button("Run Analysis"):
                with st.spinner("Identifying inactive accounts..."):
                    # Perform analysis
                    results = checker.identify_inactive_accounts(
                        inactivity_years=inactivity_years,
                        account_types=account_types
                    )

                    if results is not None and not results.empty:
                        st.session_state.results = results

                        # Generate compliance recommendations
                        compliance_results = checker.mark_for_compliance_action(
                            notify_years=notify_years,
                            freeze_years=freeze_years,
                            escalate_years=escalate_years
                        )

                        if compliance_results is not None:
                            st.session_state.compliance_results = compliance_results

                            # Calculate summary statistics
                            st.session_state.summary_stats = checker.get_summary_stats()
                    else:
                        st.warning("No inactive accounts found with the specified criteria.")

    # Display results if available
    if st.session_state.results is not None and not st.session_state.results.empty:
        st.success(f"Found {len(st.session_state.results)} inactive accounts!")

        # Create tabs
        tab1, tab2, tab3, tab4 = st.tabs(["Summary", "Data Table", "Visualizations", "Export"])

        # Summary tab
        with tab1:
            if st.session_state.summary_stats:
                stats = st.session_state.summary_stats

                # Account statistics section
                st.header("Account Statistics")
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Total Accounts", f"{len(st.session_state.results)}")
                    st.metric("Total Balance", f"AED {stats['total_balance']:,.2f}")

                with col2:
                    st.metric("Average Balance", f"AED {stats['avg_balance']:,.2f}")
                    st.metric("Maximum Balance", f"AED {stats['max_balance']:,.2f}")

                with col3:
                    st.metric("KYC Expired", f"{stats['kyc_status_counts'].get('Expired', 0)}")
                    if 'contact_counts' in stats:
                        st.metric("No Contact Made", f"{stats['contact_counts'].get('No Contact', 0)}")

                # Action summary section
                if 'action_counts' in stats:
                    st.header("Recommended Actions")
                    action_cols = st.columns(4)

                    for i, (action, count) in enumerate(stats['action_counts'].items()):
                        with action_cols[i % 4]:
                            st.metric(f"{action}", f"{count}")

                # Risk summary section
                if 'risk_counts' in stats:
                    st.header("Risk Profile")
                    risk_cols = st.columns(3)

                    for i, (risk, count) in enumerate(stats['risk_counts'].items()):
                        with risk_cols[i % 3]:
                            st.metric(f"{risk} Risk", f"{count}")

                # Priority summary section
                if 'priority_counts' in stats:
                    st.header("Compliance Priority")
                    priority_cols = st.columns(4)

                    for i, (priority, count) in enumerate(stats['priority_counts'].items()):
                        with priority_cols[i % 4]:
                            st.metric(f"{priority} Priority", f"{count}")

                # Distribution by account type
                st.header("Distribution by Account Type")
                type_cols = st.columns(len(stats['type_counts']))

                for i, (acc_type, count) in enumerate(stats['type_counts'].items()):
                    with type_cols[i]:
                        st.metric(f"{acc_type}", f"{count}")

                # Distribution by branch
                st.header("Distribution by Branch")
                branch_cols = st.columns(len(stats['branch_counts']))

                for i, (branch, count) in enumerate(stats['branch_counts'].items()):
                    with branch_cols[i]:
                        st.metric(f"{branch}", f"{count}")

                # Distribution by customer type
                st.header("Distribution by Customer Type")
                customer_cols = st.columns(len(stats['customer_type_counts']))

                for i, (cust_type, count) in enumerate(stats['customer_type_counts'].items()):
                    with customer_cols[i]:
                        st.metric(f"{cust_type}", f"{count}")

        # Data table tab
        with tab2:
            if st.session_state.compliance_results is not None:
                # Add filters
                st.subheader("Filter Options")
                filter_cols = st.columns(4)

                with filter_cols[0]:
                    account_type_filter = st.multiselect(
                        "Account Type",
                        options=st.session_state.compliance_results['Account Type'].unique(),
                        default=st.session_state.compliance_results['Account Type'].unique()
                    )

                with filter_cols[1]:
                    branch_filter = st.multiselect(
                        "Branch",
                        options=st.session_state.compliance_results['Branch'].unique(),
                        default=st.session_state.compliance_results['Branch'].unique()
                    )

                with filter_cols[2]:
                    customer_type_filter = st.multiselect(
                        "Customer Type",
                        options=st.session_state.compliance_results['Customer Type'].unique(),
                        default=st.session_state.compliance_results['Customer Type'].unique()
                    )

                with filter_cols[3]:
                    kyc_status_filter = st.multiselect(
                        "KYC Status",
                        options=st.session_state.compliance_results['KYC Status'].unique(),
                        default=st.session_state.compliance_results['KYC Status'].unique()
                    )

                # Second row of filters
                filter_cols2 = st.columns(3)

                with filter_cols2[0]:
                    if 'recommended_action' in st.session_state.compliance_results.columns:
                        action_filter = st.multiselect(
                            "Recommended Action",
                            options=st.session_state.compliance_results['recommended_action'].unique(),
                            default=st.session_state.compliance_results['recommended_action'].unique()
                        )
                    else:
                        action_filter = None

                with filter_cols2[1]:
                    if 'risk_category' in st.session_state.compliance_results.columns:
                        risk_filter = st.multiselect(
                            "Risk Category",
                            options=st.session_state.compliance_results['risk_category'].unique(),
                            default=st.session_state.compliance_results['risk_category'].unique()
                        )
                    else:
                        risk_filter = None

                with filter_cols2[2]:
                    if 'compliance_priority' in st.session_state.compliance_results.columns:
                        priority_filter = st.multiselect(
                            "Compliance Priority",
                            options=st.session_state.compliance_results['compliance_priority'].unique(),
                            default=st.session_state.compliance_results['compliance_priority'].unique()
                        )
                    else:
                        priority_filter = None

                # Apply filters
                filtered_df = st.session_state.compliance_results[
                    (st.session_state.compliance_results['Account Type'].isin(account_type_filter)) &
                    (st.session_state.compliance_results['Branch'].isin(branch_filter)) &
                    (st.session_state.compliance_results['Customer Type'].isin(customer_type_filter)) &
                    (st.session_state.compliance_results['KYC Status'].isin(kyc_status_filter))
                    ]

                if action_filter:
                    filtered_df = filtered_df[filtered_df['recommended_action'].isin(action_filter)]

                if risk_filter:
                    filtered_df = filtered_df[filtered_df['risk_category'].isin(risk_filter)]

                if priority_filter:
                    filtered_df = filtered_df[filtered_df['compliance_priority'].isin(priority_filter)]

                # Display table
                st.subheader("Dormant Accounts")
                st.dataframe(filtered_df, use_container_width=True)

        # Visualizations tab
        with tab3:
            if st.session_state.compliance_results is not None:
                st.subheader("Account Distribution Analysis")

                viz_cols = st.columns(2)

                with viz_cols[0]:
                    # Account type distribution
                    fig1 = px.pie(
                        st.session_state.compliance_results,
                        names='Account Type',
                        title='Distribution by Account Type',
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                    st.plotly_chart(fig1, use_container_width=True)

                    # Branch distribution
                    fig3 = px.bar(
                        st.session_state.compliance_results['Branch'].value_counts().reset_index(),
                        x='Branch',  # Changed from 'index'
                        y='count',  # Changed from 'Branch'
                        title='Distribution by Branch',
                        labels={'Branch': 'Branch', 'count': 'Count'},
                        color='Branch',  # Changed from 'index'
                        color_discrete_sequence=px.colors.qualitative.Bold
                    )
                    st.plotly_chart(fig3, use_container_width=True)

                with viz_cols[1]:
                    # Customer type distribution
                    fig2 = px.pie(
                        st.session_state.compliance_results,
                        names='Customer Type',
                        title='Distribution by Customer Type',
                        color_discrete_sequence=px.colors.qualitative.Safe
                    )
                    st.plotly_chart(fig2, use_container_width=True)

                    # KYC status distribution
                    fig4 = px.pie(
                        st.session_state.compliance_results,
                        names='KYC Status',
                        title='Distribution by KYC Status',
                        color_discrete_sequence=px.colors.qualitative.Set1
                    )
                    st.plotly_chart(fig4, use_container_width=True)

                st.subheader("Compliance Analysis")

                viz_cols2 = st.columns(2)

                with viz_cols2[0]:
                    # Recommended action distribution
                    if 'recommended_action' in st.session_state.compliance_results.columns:
                        fig5 = px.bar(
                            st.session_state.compliance_results['recommended_action'].value_counts().reset_index(),
                            x='recommended_action',  # Changed from 'index'
                            y='count',  # Changed from 'recommended_action'
                            title='Recommended Actions',
                            labels={'recommended_action': 'Action', 'count': 'Count'},
                            color='recommended_action',  # Changed from 'index'
                            color_discrete_sequence=px.colors.qualitative.Vivid
                        )
                        st.plotly_chart(fig5, use_container_width=True)

                    # Risk category distribution
                    if 'risk_category' in st.session_state.compliance_results.columns:
                        fig6 = px.pie(
                            st.session_state.compliance_results,
                            names='risk_category',
                            title='Distribution by Risk Category',
                            color_discrete_sequence=px.colors.sequential.Plasma
                        )
                        st.plotly_chart(fig6, use_container_width=True)

                with viz_cols2[1]:
                    # Compliance priority distribution
                    if 'compliance_priority' in st.session_state.compliance_results.columns:
                        fig7 = px.bar(
                            st.session_state.compliance_results['compliance_priority'].value_counts().reset_index(),
                            x='compliance_priority',  # Changed from 'index'
                            y='count',  # Changed from 'compliance_priority'
                            title='Compliance Priority',
                            labels={'compliance_priority': 'Priority', 'count': 'Count'},
                            color='compliance_priority',  # Changed from 'index'
                            color_discrete_sequence=px.colors.sequential.Inferno
                        )
                        st.plotly_chart(fig7, use_container_width=True)

                    # Years inactive histogram
                    fig8 = px.histogram(
                        st.session_state.compliance_results,
                        x='years_inactive',
                        title='Distribution of Inactivity Period',
                        labels={'years_inactive': 'Years Inactive', 'count': 'Number of Accounts'},
                        color_discrete_sequence=px.colors.qualitative.Pastel
                    )
                    st.plotly_chart(fig8, use_container_width=True)

                st.subheader("Financial Analysis")

                # Account balance by account type box plot
                fig9 = px.box(
                    st.session_state.compliance_results,
                    x='Account Type',
                    y='Account Balance',
                    title='Account Balance by Account Type',
                    color='Account Type',
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                st.plotly_chart(fig9, use_container_width=True)

                viz_cols3 = st.columns(2)

                with viz_cols3[0]:
                    # Account balance by branch
                    fig10 = px.box(
                        st.session_state.compliance_results,
                        x='Branch',
                        y='Account Balance',
                        title='Account Balance by Branch',
                        color='Branch',
                        color_discrete_sequence=px.colors.qualitative.Bold
                    )
                    st.plotly_chart(fig10, use_container_width=True)

                with viz_cols3[1]:
                    # Account balance by customer type
                    fig11 = px.box(
                        st.session_state.compliance_results,
                        x='Customer Type',
                        y='Account Balance',
                        title='Account Balance by Customer Type',
                        color='Customer Type',
                        color_discrete_sequence=px.colors.qualitative.Safe
                    )
                    st.plotly_chart(fig11, use_container_width=True)

        # Export tab
        with tab4:
            if st.session_state.compliance_results is not None:
                st.subheader("Export Results")

                # Full report
                st.markdown("### Full Report")
                st.download_button(
                    label="Download Full Dormant Account Report (CSV)",
                    data=st.session_state.compliance_results.to_csv(index=False).encode('utf-8'),
                    file_name="dormant_accounts_full_report.csv",
                    mime="text/csv"
                )

                # Specialized reports
                st.markdown("### Specialized Reports")
                report_cols = st.columns(2)

                with report_cols[0]:
                    # High priority report
                    if 'compliance_priority' in st.session_state.compliance_results.columns:
                        critical_df = st.session_state.compliance_results[
                            st.session_state.compliance_results['compliance_priority'] == 'CRITICAL'
                            ]

                        if not critical_df.empty:
                            st.download_button(
                                label="Download Critical Priority Accounts (CSV)",
                                data=critical_df.to_csv(index=False).encode('utf-8'),
                                file_name="dormant_accounts_critical_priority.csv",
                                mime="text/csv",
                                key="download_critical"
                            )

                    # KYC expired report
                    kyc_expired_df = st.session_state.compliance_results[
                        st.session_state.compliance_results['KYC Status'] == 'Expired'
                        ]

                    if not kyc_expired_df.empty:
                        st.download_button(
                            label="Download KYC Expired Accounts (CSV)",
                            data=kyc_expired_df.to_csv(index=False).encode('utf-8'),
                            file_name="dormant_accounts_kyc_expired.csv",
                            mime="text/csv",
                            key="download_kyc"
                        )

                with report_cols[1]:
                    # Savings/Call/Current report
                    savings_df = st.session_state.compliance_results[
                        st.session_state.compliance_results['Account Type'] == 'Savings/Call/Current'
                        ]

                    if not savings_df.empty:
                        st.download_button(
                            label="Download Savings/Call/Current Accounts (CSV)",
                            data=savings_df.to_csv(index=False).encode('utf-8'),
                            file_name="dormant_accounts_savings_call_current.csv",
                            mime="text/csv",
                            key="download_savings"
                        )

                    # No contact report
                    if 'contact_status' in st.session_state.compliance_results.columns:
                        no_contact_df = st.session_state.compliance_results[
                            st.session_state.compliance_results['contact_status'] == 'No Contact'
                            ]

                        if not no_contact_df.empty:
                            st.download_button(
                                label="Download No Contact Accounts (CSV)",
                                data=no_contact_df.to_csv(index=False).encode('utf-8'),
                                file_name="dormant_accounts_no_contact.csv",
                                mime="text/csv",
                                key="download_no_contact"
                            )

                # Action-based reports
                if 'recommended_action' in st.session_state.compliance_results.columns:
                    st.markdown("### Action-Based Reports")
                    action_report_cols = st.columns(3)

                    actions = st.session_state.compliance_results['recommended_action'].unique()
                    for i, action in enumerate(actions):
                        with action_report_cols[i % 3]:
                            action_df = st.session_state.compliance_results[
                                st.session_state.compliance_results['recommended_action'] == action
                                ]

                            if not action_df.empty:
                                st.download_button(
                                    label=f"Download {action} Accounts (CSV)",
                                    data=action_df.to_csv(index=False).encode('utf-8'),
                                    file_name=f"dormant_accounts_{action.lower()}.csv",
                                    mime="text/csv",
                                    key=f"download_{action}"
                                )


if __name__ == "__main__":
    main()