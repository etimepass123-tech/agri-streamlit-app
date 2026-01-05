import streamlit as st
import pandas as pd
import io
from sqlalchemy import text
from db.db import get_engine, get_connection

# --------------------------------------------------
# CONFIG
# --------------------------------------------------
st.set_page_config(
    page_title="Agri Data Entry System",
    layout="wide",
    page_icon="🌾"
)

engine = get_engine()

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------
st.sidebar.title("🌾 Navigation")
role = st.sidebar.radio("Select Role", ["Admin", "User"])

# ==================================================
# ADMIN PANEL
# ==================================================
if role == "Admin":
    st.title("⚙️ Admin Control Panel")

    if st.text_input("Admin Password", type="password") != "admin123":
        st.stop()

    tabs = st.tabs([
        "📤 Upload Excel",
        "🧪 Treatments",
        "📊 Traits",
        "📋 View Data",
        "📥 Download",
        "💣 Danger Zone"
    ])

    # --------------------------------------------------
    # TAB 1: UPLOAD EXCEL
    # --------------------------------------------------
    with tabs[0]:
        st.subheader("Upload Experiment Excel (A–G fixed, H+ traits)")
        file = st.file_uploader("Upload Excel", type=["xlsx"])

        if file:
            df = pd.read_excel(file)
            st.dataframe(df.head(), width="stretch")

            if df.shape[1] < 8:
                st.error("Excel must contain at least A–G + trait columns")
                st.stop()

            if st.button("Initialize / Replace Experiment"):
                conn = get_connection()
                cur = conn.cursor()

                # FULL RESET
                cur.execute("DELETE FROM observation_data")
                cur.execute("DELETE FROM experiment_traits")
                cur.execute("DELETE FROM experiment_metadata")

                exp_id = str(df.iloc[0, 0])
                traits = df.columns[7:].tolist()

                # Insert metadata (A–G)
                for _, r in df.iterrows():
                    cur.execute("""
                        INSERT INTO experiment_metadata
                        (exp_id, location, year, season, replication, block, treatment, entry_status)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,'Draft')
                    """, tuple(r.iloc[:7]))

                # Insert traits (H+)
                for t in traits:
                    cur.execute("""
                        INSERT INTO experiment_traits
                        (exp_id, trait_name, data_type, unit, is_active)
                        VALUES (%s,%s,'number','',1)
                    """, (exp_id, t))

                conn.commit()
                conn.close()
                st.success("Experiment initialized successfully")

    # --------------------------------------------------
    # TAB 2: TREATMENTS
    # --------------------------------------------------
    with tabs[1]:
        st.subheader("Manage Treatments")

        meta_df = pd.read_sql("SELECT * FROM experiment_metadata", engine)
        st.dataframe(meta_df, width="stretch")

        st.markdown("### ➕ Add Treatment")
        with st.form("add_treatment"):
            exp_id = st.text_input("Experiment ID")
            location = st.text_input("Location")
            year = st.number_input("Year", step=1)
            season = st.text_input("Season")
            replication = st.number_input("Replication", step=1)
            block = st.number_input("Block", step=1)
            treatment = st.text_input("Treatment Name")
            add_btn = st.form_submit_button("Add Treatment")

        if add_btn:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO experiment_metadata
                (exp_id, location, year, season, replication, block, treatment, entry_status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,'Draft')
            """, (exp_id, location, year, season, replication, block, treatment))
            conn.commit()
            conn.close()
            st.success("Treatment added")

        st.markdown("### 🔧 Reset / Delete Treatment")
        tid = st.number_input("Treatment ID", step=1)

        col1, col2 = st.columns(2)

        if col1.button("Reset Treatment Data"):
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM observation_data WHERE metadata_id=%s", (tid,))
            cur.execute(
                "UPDATE experiment_metadata SET entry_status='Draft' WHERE id=%s",
                (tid,)
            )
            conn.commit()
            conn.close()
            st.success("Treatment reset")

        if col2.button("Delete Treatment"):
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM observation_data WHERE metadata_id=%s", (tid,))
            cur.execute("DELETE FROM experiment_metadata WHERE id=%s", (tid,))
            conn.commit()
            conn.close()
            st.warning("Treatment deleted")

    # --------------------------------------------------
    # TAB 3: TRAITS
    # --------------------------------------------------
    with tabs[2]:
        st.subheader("Manage Traits")

        traits_df = pd.read_sql("SELECT * FROM experiment_traits", engine)
        st.dataframe(traits_df, width="stretch")

        st.markdown("### ➕ Add Trait")
        with st.form("add_trait"):
            trait_name = st.text_input("Trait Name")
            data_type = st.selectbox("Data Type", ["number", "text"])
            unit = st.text_input("Unit")
            add_trait_btn = st.form_submit_button("Add Trait")

        if add_trait_btn:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO experiment_traits
                (exp_id, trait_name, data_type, unit, is_active)
                VALUES ((SELECT exp_id FROM experiment_metadata LIMIT 1),
                        %s,%s,%s,1)
            """, (trait_name, data_type, unit))
            conn.commit()
            conn.close()
            st.success("Trait added")

        st.markdown("### 🔁 Enable / Disable Trait")
        trait_sel = st.selectbox("Select Trait", traits_df["trait_name"].tolist())

        col1, col2 = st.columns(2)

        if col1.button("Disable Trait"):
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "UPDATE experiment_traits SET is_active=0 WHERE trait_name=%s",
                (trait_sel,)
            )
            conn.commit()
            conn.close()
            st.warning(f"{trait_sel} disabled")

        if col2.button("Enable Trait"):
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "UPDATE experiment_traits SET is_active=1 WHERE trait_name=%s",
                (trait_sel,)
            )
            conn.commit()
            conn.close()
            st.success(f"{trait_sel} enabled")

    # --------------------------------------------------
    # TAB 4: VIEW DATA (ADMIN)
    # --------------------------------------------------
    with tabs[3]:
        st.subheader("View Saved / Submitted Data")

        status = st.radio(
            "Select Data Status",
            ["Draft", "Submitted"],
            horizontal=True
        )

        df = pd.read_sql(
            text("""
                SELECT
                    m.exp_id, m.location, m.year, m.season,
                    m.replication, m.block, m.treatment,
                    o.attribute_name, o.attribute_value
                FROM experiment_metadata m
                LEFT JOIN observation_data o
                    ON m.id = o.metadata_id
                LEFT JOIN experiment_traits t
                    ON o.attribute_name = t.trait_name
                WHERE m.entry_status = :status
                  AND (t.is_active = 1 OR t.is_active IS NULL)
            """),
            engine,
            params={"status": status}
        )

        if df.empty:
            st.info("No data available for this status.")
        else:
            wide_df = df.pivot_table(
                index=[
                    "exp_id", "location", "year", "season",
                    "replication", "block", "treatment"
                ],
                columns="attribute_name",
                values="attribute_value"
            ).reset_index()

            st.dataframe(wide_df, width="stretch")

    # --------------------------------------------------
    # TAB 5: DOWNLOAD
    # --------------------------------------------------
    with tabs[4]:
        st.subheader("Download Submitted Data")

        if st.button("Generate Excel"):
            df = pd.read_sql("""
                SELECT
                    m.exp_id, m.location, m.year, m.season,
                    m.replication, m.block, m.treatment,
                    o.attribute_name, o.attribute_value
                FROM experiment_metadata m
                JOIN observation_data o ON m.id=o.metadata_id
                JOIN experiment_traits t ON o.attribute_name=t.trait_name
                WHERE m.entry_status='Submitted'
                  AND t.is_active=1
            """, engine)

            if df.empty:
                st.warning("No submitted data found.")
            else:
                wide = df.pivot_table(
                    index=[
                        "exp_id","location","year","season",
                        "replication","block","treatment"
                    ],
                    columns="attribute_name",
                    values="attribute_value"
                ).reset_index()

                buffer = io.BytesIO()
                wide.to_excel(buffer, index=False)

                st.download_button(
                    "⬇ Download Excel",
                    buffer.getvalue(),
                    "submitted_experiment_data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    # --------------------------------------------------
    # TAB 6: DANGER ZONE
    # --------------------------------------------------
    with tabs[5]:
        st.subheader("⚠️ Delete Everything")

        if st.checkbox("I understand this will permanently delete all data"):
            if st.button("DELETE EVERYTHING"):
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM observation_data")
                cur.execute("DELETE FROM experiment_traits")
                cur.execute("DELETE FROM experiment_metadata")
                conn.commit()
                conn.close()
                st.error("All data deleted")

# ==================================================
# USER PANEL
# ==================================================
else:
    st.title("📊 Excel-like Data Entry")

    meta_df = pd.read_sql("SELECT * FROM experiment_metadata", engine)

    if meta_df.empty:
        st.warning("No active experiment. Contact admin.")
        st.stop()

    traits_df = pd.read_sql(
        "SELECT trait_name FROM experiment_traits WHERE is_active=1",
        engine
    )
    traits = traits_df["trait_name"].tolist()

    selected_traits = st.multiselect("Select Traits (H onwards)", traits)

    if not selected_traits:
        st.info("Select traits to begin entry")
        st.stop()

    # Load existing values (CRITICAL FIX)
    obs_df = pd.read_sql(
        "SELECT metadata_id, attribute_name, attribute_value FROM observation_data",
        engine
    )

    existing = {
        (int(r.metadata_id), r.attribute_name): r.attribute_value
        for _, r in obs_df.iterrows()
    }

    fixed_cols = [
        "exp_id","location","year",
        "season","replication","block","treatment"
    ]
    all_cols = fixed_cols + selected_traits

    header = st.columns(len(all_cols))
    for i, c in enumerate(all_cols):
        header[i].markdown(f"**{c.upper()}**")

    values = {}

    with st.form("entry_form"):
        for _, row in meta_df.iterrows():
            cols = st.columns(len(all_cols))

            for i, col in enumerate(fixed_cols):
                cols[i].write(row[col])

            for j, trait in enumerate(selected_traits):
                idx = len(fixed_cols) + j
                default = existing.get((int(row["id"]), trait), 0.0)

                values[(row["id"], trait)] = cols[idx].number_input(
                    trait,
                    value=float(default),
                    key=f"{row['id']}_{trait}",
                    label_visibility="collapsed"
                )

        save = st.form_submit_button("💾 Save")
        submit = st.form_submit_button("✅ Submit")

    if save or submit:
        conn = get_connection()
        cur = conn.cursor()

        for (mid, trait), val in values.items():
            cur.execute(
                "DELETE FROM observation_data WHERE metadata_id=%s AND attribute_name=%s",
                (mid, trait)
            )
            cur.execute("""
                INSERT INTO observation_data
                (metadata_id, attribute_name, attribute_value)
                VALUES (%s,%s,%s)
            """, (mid, trait, float(val)))

        if submit:
            cur.execute(
                "UPDATE experiment_metadata SET entry_status='Submitted'"
            )

        conn.commit()
        conn.close()
        st.success("Submitted" if submit else "Saved successfully")
