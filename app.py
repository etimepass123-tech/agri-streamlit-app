import streamlit as st
import pandas as pd
from db.db import get_connection, get_engine
import io

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="Agri Excel-like Data Entry",
    layout="wide",
    page_icon="🌾"
)

# -------------------------------------------------
# SESSION STATE
# -------------------------------------------------
if "entry_started" not in st.session_state:
    st.session_state.entry_started = False

if "selected_traits" not in st.session_state:
    st.session_state.selected_traits = []

# -------------------------------------------------
# SIDEBAR
# -------------------------------------------------
st.sidebar.title("🌾 Navigation")
role = st.sidebar.radio("Select Role", ["Admin", "User"])

# Get Engine for Pandas operations
engine = get_engine()

# =================================================
# ADMIN PANEL
# =================================================
if role == "Admin":
    st.title("⚙️ Admin Panel")

    if st.text_input("Admin Password", type="password") != "admin123":
        st.warning("Enter admin password")
        st.stop()

    tab1, tab2, tab3 = st.tabs([
        "📤 Upload / Initialize",
        "🛠️ Manage Treatments",
        "📥 Download Data"
    ])

    # ---------------- TAB 1: UPLOAD ----------------
    with tab1:
        st.subheader("Upload Experiment Excel (A–G + H+)")
        uploaded = st.file_uploader("Upload Excel", type=["xlsx"])
        if uploaded:
            df = pd.read_excel(uploaded)
            if df.shape[1] < 8:
                st.error("Excel must have at least 8 columns")
                st.stop()

            st.dataframe(df.head(), width="stretch")
            exp_id = str(df.iloc[0, 0])
            traits = df.columns[7:].tolist()

            if st.button("Initialize Experiment"):
                conn = get_connection()
                cur = conn.cursor()
                try:
                    for _, r in df.iterrows():
                        cur.execute("""
                            INSERT INTO experiment_metadata 
                            (exp_id, location, year, season, replication, block, treatment)
                            VALUES (%s,%s,%s,%s,%s,%s,%s)
                        """, (str(r.iloc[0]), str(r.iloc[1]), int(r.iloc[2]), 
                              str(r.iloc[3]), int(r.iloc[4]), int(r.iloc[5]), str(r.iloc[6])))

                    cur.execute("DELETE FROM experiment_traits WHERE exp_id=%s", (exp_id,))
                    for t in traits:
                        cur.execute("INSERT INTO experiment_traits (exp_id, trait_name) VALUES (%s,%s)", (exp_id, t))
                    
                    conn.commit()
                    st.success("Experiment initialized")
                except Exception as e:
                    st.error(f"Error: {e}")
                finally:
                    conn.close()

    # ---------------- TAB 2: MANAGE ----------------
    with tab2:
        st.subheader("Manage Treatments")
        df_manage = pd.read_sql("SELECT id, exp_id, treatment, block, replication, entry_status, is_active FROM experiment_metadata", engine)
        st.dataframe(df_manage, width="stretch")

        st.divider()
        tid = st.number_input("Treatment ID", step=1)
        c1, c2, c3 = st.columns(3)

        if c1.button("🔓 Reopen") or c2.button("❌ Deactivate") or c3.button("➕ Restore"):
            conn = get_connection()
            cur = conn.cursor()
            if c1.button("🔓 Reopen"):
                cur.execute("UPDATE experiment_metadata SET entry_status='Draft' WHERE id=%s", (tid,))
            elif c2.button("❌ Deactivate"):
                cur.execute("UPDATE experiment_metadata SET is_active=0 WHERE id=%s", (tid,))
            elif c3.button("➕ Restore"):
                cur.execute("UPDATE experiment_metadata SET is_active=1 WHERE id=%s", (tid,))
            conn.commit()
            conn.close()
            st.rerun()

    # ---------------- TAB 3: DOWNLOAD ----------------
    with tab3:
        st.subheader("Download Submitted Data")
        if st.button("Generate Excel"):
            df_down = pd.read_sql("""
                SELECT m.exp_id, m.location, m.year, m.season, m.replication, m.block, m.treatment,
                       o.attribute_name, o.attribute_value
                FROM experiment_metadata m
                JOIN observation_data o ON m.id=o.metadata_id
                WHERE m.entry_status='Submitted' AND m.is_active=1
            """, engine)
            if df_down.empty:
                st.warning("No submitted data found")
            else:
                wide = df_down.pivot_table(index=["exp_id","location","year","season","replication","block","treatment"],
                                         columns="attribute_name", values="attribute_value").reset_index()
                output = io.BytesIO()
                wide.to_excel(output, index=False)
                st.download_button("⬇ Download Excel", output.getvalue(), "final_experiment_data.xlsx")

# =================================================
# USER PANEL
# =================================================
else:
    st.title("📊 Excel-like Data Entry")
    
    # 1. Load active metadata using Engine
    meta_df = pd.read_sql("SELECT * FROM experiment_metadata WHERE is_active=1", engine)

    if meta_df.empty:
        st.warning("No active experiment available")
        st.stop()

    exp_id = meta_df.iloc[0]["exp_id"]
    
    # 2. Load traits
    traits_df = pd.read_sql("SELECT trait_name FROM experiment_traits WHERE exp_id=%s", engine, params=[exp_id])
    traits = traits_df["trait_name"].tolist()

    st.subheader("Select columns (H onwards)")
    selected_traits = st.multiselect("Traits", traits, default=st.session_state.selected_traits)

    if st.button("▶ Start Entry") and selected_traits:
        st.session_state.entry_started = True
        st.session_state.selected_traits = selected_traits

    # 3. Table Rendering
    if st.session_state.entry_started and st.session_state.selected_traits:
        selected_traits = st.session_state.selected_traits
        fixed_cols = ["exp_id","location","year","season","replication","block","treatment"]
        all_cols = fixed_cols + selected_traits

        # OPTIMIZATION: Load all observation data at once to avoid loop queries
        obs_df = pd.read_sql("SELECT metadata_id, attribute_name, attribute_value FROM observation_data", engine)

        is_locked = meta_df["entry_status"].eq("Submitted").any()

        with st.form("entry_form"):
            values = {}
            header_cols = st.columns(len(all_cols))
            for i, c in enumerate(all_cols):
                header_cols[i].markdown(f"**{c.upper()}**")

            for _, r in meta_df.iterrows():
                row_cols = st.columns(len(all_cols))
                for i, c in enumerate(fixed_cols):
                    row_cols[i].write(r[c])

                for j, t in enumerate(selected_traits):
                    idx = len(fixed_cols) + j
                    key = f"{r['id']}|{t}"
                    
                    # Filter local dataframe instead of database query
                    match = obs_df[(obs_df['metadata_id'] == r['id']) & (obs_df['attribute_name'] == t)]
                    default = float(match.iloc[0]['attribute_value']) if not match.empty else 0.0

                    values[key] = row_cols[idx].number_input(t, value=default, key=f"in_{r['id']}_{t}",
                                                          label_visibility="collapsed", disabled=is_locked)

            c1, c2 = st.columns(2)
            save_clicked = c1.form_submit_button("💾 Save")
            submit_clicked = c2.form_submit_button("✅ Submit")

        if save_clicked or submit_clicked:
            conn = get_connection()
            cur = conn.cursor()
            try:
                for k, v in values.items():
                    mid, trait = k.split("|")
                    cur.execute("DELETE FROM observation_data WHERE metadata_id=%s AND attribute_name=%s", (int(mid), trait))
                    cur.execute("INSERT INTO observation_data (metadata_id, attribute_name, attribute_value) VALUES (%s,%s,%s)", (int(mid), trait, float(v)))
                
                new_status = 'Submitted' if submit_clicked else 'Draft'
                cur.execute("UPDATE experiment_metadata SET entry_status=%s WHERE exp_id=%s", (new_status, exp_id))
                conn.commit()
                st.success(f"Data {new_status} Successfully!")
                if submit_clicked:
                    st.session_state.entry_started = False
                    st.rerun()
            finally:
                conn.close()
