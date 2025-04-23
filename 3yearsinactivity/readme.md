#   CBUAE Dormancy Checker Script

This script identifies dormant bank accounts according to CBUAE regulations, using a Streamlit web app. It processes a CSV file to find accounts with no customer-initiated transactions for 3+ years.

##  Functionality

1.  **Data Upload:** Upload a CSV file containing account data (account_id, account_type, last_transaction_date, etc.).
2.  **Data Processing:** Reads and cleans the CSV data using Pandas.
3.  **Dormancy Check:** Flags 'Savings/Call/Current' accounts as dormant if inactive for 3+ years.
4.  **Results:** Displays a table of dormant accounts or a message if none are found.  Provides a CSV download of results.
5.  **User Interface:** Streamlit provides a file upload and displays results.

##  How to Use

1.  Upload account data in CSV format.
2.  View the displayed results.
3.  Optionally, download the dormant account data as a CSV.

##  Dependencies

* streamlit
* pandas

##  Assumptions

* CSV data includes columns like account_id, account_type, last_transaction_date.
* Account type 'savings/call/current' is used (case-insensitive).
* last_transaction_date is in a parsable format.
