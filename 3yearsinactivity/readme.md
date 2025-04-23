#   CBUAE Dormancy Checker Script

This Python script, designed to be used with Streamlit, helps identify dormant bank accounts according to the Central Bank of the U.A.E. (CBUAE) regulations. It processes data from a CSV file to find accounts that have been inactive for a specified period.

##  Functionality

The script performs the following actions:

1.  ** Data Upload:**
    * Allows the user to upload a CSV file containing bank account data.  The file is expected to have columns like `account_id`, `account_type`, `last_transaction_date`, `customer_type`, `account_balance`, and `account_status`.
2.  ** Data Processing:**
    * Reads the CSV file into a Pandas DataFrame.
    * Cleans up the column names by converting them to lowercase and replacing spaces with underscores.
    * Parses the `last_transaction_date` column.
    * If present, attempts to parse a `maturity_date` column.
    * Renames some columns for consistency.
3.  ** Dormancy Check:**
    * Defines a dormancy period of 3 years.
    * ** Rule 1: Savings/Call/Current Accounts:**
        * Filters for "savings/call/current" accounts.
        * Calculates the date from which the account is considered dormant.
        * Flags accounts as dormant if the last transaction was over 3 years ago.
    * ** Rule 2: Fixed Deposit Accounts:**
        * Filters for "fixed deposit" accounts.
        * If a `maturity_date` column exists:
            * Calculates the date from which the account is considered dormant (3 years after maturity).
            * Flags accounts as dormant if the maturity date was over 3 years ago.
        * If `maturity_date` is missing, it displays a warning.
4.  ** Results:**
    * Combines the results from both rules.
    * If dormant accounts are found:
        * Displays a table of dormant accounts in the Streamlit app, showing relevant details.
        * Provides a button to download the dormant accounts data as a CSV file.
    * If no dormant accounts are found, displays a success message.
5.  ** User Interface:**
    * Uses Streamlit to create a simple web-based user interface.
    * Provides a file upload widget.
    * Displays results and messages in the app.

##  How to Use

1.  ** Upload Data:** Upload a CSV file containing the bank account data.
2.  ** View Results:** The script will process the data and display any accounts that meet the dormancy criteria.
3.  ** Download Data (Optional):** If dormant accounts are found, you can download the results as a CSV file.

##  Dependencies

The script requires the following Python libraries:

* streamlit
* pandas

##  Assumptions

* The input CSV file contains columns with names similar to `account_id`, `account_type`, `last_transaction_date`, `customer_type`, `account_balance`, and `account_status`.
* Account types are represented as strings, including "savings/call/current" and "fixed deposit" (case-insensitive).
* The date format in the `last_transaction_date` column is consistent and parsable by Pandas.
* For Fixed Deposits, the CSV may contain a `maturity_date` column.

