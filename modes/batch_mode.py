import streamlit as st
import pandas as pd
import io
import datetime
from gitlab_utils import batch

DEFAULT_ICFAI_USERS = """saikrishna_b
MohanaSriBhavitha
praneethashish
kanukuntagreeshma2004
vandana1735
vandana_rajuldev
Mukthanand21
Shanmukh16
Sathwikareddy_Damanagari
Sahasraa
laxmanreddypatlolla
Abhilash653
LagichettyKushal
Lakshy
Suma2304
koushik_18
kumari123
Habeebunissa
Bhaskar_Battula
Pranav_rs
Pavani_Pothuganti
prav2702"""

DEFAULT_RCTS_USERS = """vai5h
Saiharshavardhan
Rushika_1105
swarna_4539
satish05
aravindswamy
pavaninagireddi
jeevana_31
saiteja3005
SandhyaRani_111
klaxmi1908
Kaveri_Mamidi
dasari_Askhaya
Ashritha_P"""

def render_batch_mode_ui(client, report_type):
    st.subheader(f"🚀 Batch Analytics - {report_type}")

    default_value = DEFAULT_ICFAI_USERS if report_type == "ICFAI" else DEFAULT_RCTS_USERS

    # Date Filter Section
    st.markdown("### 📅 Date Filter")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=None,
            help="Filter contributions from this date onwards",
            key="batch_start_date"
        )
    with col2:
        end_date = st.date_input(
            "End Date",
            value=None,
            help="Filter contributions up to this date",
            key="batch_end_date"
        )

    # Show date range info if dates are selected
    if start_date and end_date:
        if start_date > end_date:
            st.error("⚠️ Start Date must be before End Date")
            return
        st.info(f"📊 Showing contributions from **{start_date}** to **{end_date}**")
    elif start_date:
        st.info(f"📊 Showing contributions from **{start_date}** onwards")
    elif end_date:
        st.info(f"📊 Showing contributions up to **{end_date}**")

    user_input = st.text_area(
        "Enter Usernames (one per line)",
        height=200,
        value=default_value,
        placeholder="user1\nuser2\n...",
        key="batch_users"
    )

    if st.button("Run Batch Analysis", key="batch_run"):
        usernames = [line.strip() for line in user_input.splitlines() if line.strip()]
        if not usernames:
            st.warning("Please enter at least one username.")
            return

        st.info(f"Processing {len(usernames)} users...")

        with st.spinner("Fetching data in parallel..."):
            results = batch.process_batch_users(client, usernames, start_date=start_date, end_date=end_date)

        st.success("Batch processing complete!")

        # Prepare Data based on Report Type
        report_data = []

        for res in results:
            u = res.get("username")
            status = res.get("status")
            err = res.get("error", "")

            data = res.get("data", {})
            projects = data.get("projects", {})

            # Stats Access
            c_stats = data.get("commit_stats", {"total":0, "morning_commits":0, "afternoon_commits":0})
            m_stats = data.get("mr_stats", {"total":0, "merged":0, "opened":0, "closed":0})
            i_stats = data.get("issue_stats", {"total":0, "opened":0, "closed":0})

            p_personal = len(projects.get("personal", []))
            p_contributed = len(projects.get("contributed", []))
            g_count = len(data.get("groups", []))

            row = {}
            row["Username"] = u
            row["Status"] = status

            # Add Generation Timestamp
            now_ist = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
            row["Report Date"] = now_ist.strftime("%Y-%m-%d")
            row["Report Time"] = now_ist.strftime("%I:%M %p")

            if status == "Success":
                if report_type == "ICFAI":
                    # ICFAI Columns
                    row["Personal Projects"] = p_personal
                    row["Contributed Projects"] = p_contributed
                    row["Total Commits"] = c_stats["total"]
                    row["Morning Count"] = c_stats["morning_commits"]
                    row["Afternoon Count"] = c_stats["afternoon_commits"]
                    row["MR Open"] = m_stats["opened"]
                    row["MR Closed"] = m_stats["closed"]
                    row["MR Merged"] = m_stats["merged"]
                    row["Issues Opened"] = i_stats["opened"]
                    row["Issues Closed"] = i_stats["closed"]
                    row["Groups Count"] = g_count

                elif report_type == "RCTS":
                    # RCTS Columns
                    row["Total Projects"] = p_personal + p_contributed
                    row["Total Commits"] = c_stats["total"]
                    row["MR Total"] = m_stats["total"]
                    row["MR Merged"] = m_stats["merged"]
                    row["MR Pending"] = m_stats["opened"]
                    row["Issues Total"] = i_stats["total"]
                    row["Issues Opened"] = i_stats["opened"]
                    row["Issues Closed"] = i_stats["closed"]
                    row["Groups"] = g_count
                    row["Morning Active"] = "Yes" if c_stats["morning_commits"] > 0 else "No"
                    row["Afternoon Active"] = "Yes" if c_stats["afternoon_commits"] > 0 else "No"
            else:
                row["Error"] = err

            report_data.append(row)

        # Display Summary
        date_range_note = ""
        if start_date or end_date:
            if start_date and end_date:
                date_range_note = f" ({start_date} to {end_date})"
            elif start_date:
                date_range_note = f" (from {start_date})"
            elif end_date:
                date_range_note = f" (up to {end_date})"
        
        st.write(f"### 📊 Batch Summary ({report_type}){date_range_note}")
        df_report = pd.DataFrame(report_data)
        st.dataframe(df_report, width="stretch")

        # Export
        try:
            output = io.BytesIO()
            now_ist = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
            today = now_ist.strftime("%Y-%m-%d")
            filename = f"{report_type}_Report_{today}.xlsx"

            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Sheet 1: Report
                df_report.to_excel(writer, index=False, sheet_name='Report')

                # Sheet 2: Raw Errors (if any)
                errors = [r for r in report_data if r.get("Status") == "Error"]
                if errors:
                    pd.DataFrame(errors).to_excel(writer, index=False, sheet_name='Errors')

            st.download_button(
                label=f"Download {report_type} Report",
                data=output.getvalue(),
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="batch_download"
            )

        except Exception as e:
            st.error(f"Error creating Excel: {e}")
