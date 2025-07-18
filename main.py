import streamlit as st
import pandas as pd
import io

def upload_csv_files():
    """
    Display file upload widgets and return the uploaded DataFrames.
    """
    st.title("📊 TRANSFORMER")
    st.write("Upload report and dump Excel files to get started.")

    file1 = st.file_uploader("Upload Report Excel File", type="xlsx", key="file1")
    file2 = st.file_uploader("Upload Dump Excel File", type="xlsx", key="file2")

    df1, df2 = None, None

    if file1:
        df1 = pd.read_excel(file1, sheet_name="Data")

    if file2:
        df2 = pd.read_excel(file2)

    return df1, df2

def clean_and_filter_data(df_report, df_dump):
    try:
        # Step 1: Convert 'Created On' to datetime
        df_report["Created On"] = pd.to_datetime(df_report["Created On"], format="%m/%d/%Y %H:%M:%S")
        df_dump["Created On"] = pd.to_datetime(df_dump["Created On"], format="%m/%d/%Y %H:%M:%S")

        # Step 2: Get last Created On from report
        last_created_on = df_report["Created On"].max()
        st.info(f"📅 Last 'Created On' in Report: {last_created_on}")

        # Step 3: Check 'ParentID' column presence
        if "ParentID" not in df_report.columns or "ParentID" not in df_dump.columns:
            st.error("❌ 'ParentID' column not found in one or both files.")
            return

        # Step 4: Split dump into before and after report's last timestamp
        before_df = df_dump[df_dump["Created On"] <= last_created_on]
        after_df = df_dump[df_dump["Created On"] > last_created_on]

        # Step 5: Filter before_df by removing rows whose ParentID is not in report
        report_ids = set(df_report["ParentID"].dropna().astype(str))
        before_valid = before_df.dropna(subset=["ParentID"]).copy()
        before_invalid = before_valid[~before_valid["ParentID"].astype(str).isin(report_ids)]

        # Remove these invalid rows from dump
        before_cleaned = before_df.drop(index=before_invalid.index)
        df_cleaned = pd.concat([before_cleaned, after_df], ignore_index=True)

        # Step 6: Remove rows with Record Type = "Change" that are not in report
        if "Record Type" in df_cleaned.columns and "Record Type" in df_report.columns:
            df_changes = df_cleaned[df_cleaned["Record Type"].str.lower() == "change"].copy()
            report_keys = set(
                zip(df_report["Record Type"].str.lower(), df_report["Created On"])
            )
            df_changes["key"] = list(zip(df_changes["Record Type"].str.lower(), df_changes["Created On"]))
            unmatched_changes = df_changes[~df_changes["key"].isin(report_keys)]

            # Drop unmatched 'change' rows
            df_cleaned = df_cleaned.drop(index=unmatched_changes.index)
            st.warning(f"🔍 Removed {len(unmatched_changes)} unmatched 'Change' rows not present in Report.")
        else:
            st.warning("⚠️ 'Record Type' column not found in one or both files. Skipped 'Change' row filtering.")

        # Final Output
        st.success(f"🗑️ Removed {len(before_invalid)} rows from Dump with unmatched ParentID before last Report timestamp.")
        st.success(f"🆕 Found {len(after_df)} new rows in Dump after last Report entry.")
        st.subheader("📄 Cleaned Dump DataFrame")
        st.dataframe(df_cleaned)

        return df_cleaned

    except Exception as e:
        st.error(f"❌ Error during cleaning/filtering: {e}")

def download_csv(df_cleaned):
    # DOWNLOAD XLSX FILE
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_cleaned.to_excel(writer, index=False, sheet_name="CleanedDump")
        output.seek(0)

        st.download_button(
            label="📥 Download Cleaned Dump as XLSX",
            data=output,
            file_name="cleaned_dump.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

def main():
    st.set_page_config(page_title="CSV Transformer", layout="centered")
    df_report, df_dump = upload_csv_files()

    # Button to clean & filter
    if st.button("🚀 Clean & Filter Dump Data"):
        if df_report is None or df_dump is None:
            st.warning("⚠️ Please upload both Report and Dump Excel files before proceeding.")
        else:
            df_cleaned = clean_and_filter_data(df_report, df_dump)
            if df_cleaned is not None:
                st.session_state["df_cleaned"] = df_cleaned  # ✅ Store in session_state

    # Show download button if cleaned data exists
    if "df_cleaned" in st.session_state:
        download_csv(st.session_state["df_cleaned"])

if __name__ == "__main__":
    main()