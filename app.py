import streamlit as st
import pandas as pd
from db.db import get_connection
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
# SESSION STATE (CRITICAL FOR SAVE)
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
                st.error("Excel must have at least 8 columns (A–G + traits)")
                st.stop()

            st.dataframe(df.head(), width="stretch")

            exp_id = str(df.iloc[0, 0])
            traits = df.columns[7:].tolist()

            if st.button("Initialize Experiment"):
                conn = get_connection()
                cur = conn.cursor()

                for _, r in df.iterrows():
                    cur.execute("""
                        INSERT INTO experiment_metadata
                        (exp_id, location, year, season, replication, block, treatment)
                        VALUES (%s,%s,%s,%s,%s,%s,%s)
                    """, (
                        str(r.iloc[0]), str(r.iloc[1]), int(r.iloc[2]),
                        str(r.iloc[3]), int(r.iloc[4]), int(r.iloc[5]),
                        str(r.iloc[6])
                    ))

                cur.execute("DELETE FROM experiment_traits WHERE exp_id=%s", (exp_id,))
                for t in traits:
                    cur.execute(
                        "INSERT INTO experiment_traits (exp_id, trait_name) VALUES (%s,%s)",
                        (exp_id, t)
                    )

                conn.commit()
                conn.close()
                st.success("Experiment initialized")

    # ---------------- TAB 2: MANAGE ----------------
    with tab2:
        st.subheader("Manage Treatments")

        conn = get_connection()
        df = pd.read_sql("""
            SELECT id, exp_id, treatment, block, replication,
                   entry_status, is_active
            FROM experiment_metadata
        """, conn)

        st.dataframe(df, width="stretch")

        st.divider()
        tid = st.number_input("Treatment ID", step=1)

        c1, c2, c3 = st.columns(3)

        if c1.button("🔓 Reopen"):
            conn.cursor().execute(
                "UPDATE experiment_metadata SET entry_status='Draft' WHERE id=%s",
                (tid,)
            )
            conn.commit()
            st.success("Reopened")

        if c2.button("❌ Deactivate"):
            conn.cursor().execute(
                "UPDATE experiment_metadata SET is_active=0 WHERE id=%s",
                (tid,)
            )
            conn.commit()
            st.warning("Deactivated")

        if c3.button("➕ Restore"):
            conn.cursor().execute(
                "UPDATE experiment_metadata SET is_active=1 WHERE id=%s",
                (tid,)
            )
            conn.commit()
            st.success("Restored")

        conn.close()

    # ---------------- TAB 3: DOWNLOAD ----------------
    with tab3:
        st.subheader("Download Submitted Data")

        if st.button("Generate Excel"):
            conn = get_connection()
            df = pd.read_sql("""
                SELECT m.exp_id, m.location, m.year, m.season,
                       m.replication, m.block, m.treatment,
                       o.attribute_name, o.attribute_value
                FROM experiment_metadata m
                JOIN observation_data o ON m.id=o.metadata_id
                WHERE m.entry_status='Submitted' AND m.is_active=1
            """, conn)
            conn.close()

            if df.empty:
                st.warning("No submitted data found")
            else:
                wide = df.pivot_table(
                    index=["exp_id","location","year","season",
                           "replication","block","treatment"],
                    columns="attribute_name",
                    values="attribute_value"
                ).reset_index()

                output = io.BytesIO()
                wide.to_excel(output, index=False)

                st.download_button(
                    "⬇ Download Excel",
                    output.getvalue(),
                    "final_experiment_data.xlsx"
                )

# =================================================
# USER PANEL
# =================================================
else:
    st.title("📊 Excel-like Data Entry")

    conn = get_connection()

    meta_df = pd.read_sql(
        "SELECT * FROM experiment_metadata WHERE is_active=1",
        conn
    )

    if meta_df.empty:
        st.warning("No active experiment available")
        conn.close()
        st.stop()

    exp_id = meta_df.iloc[0]["exp_id"]

    traits_df = pd.read_sql(
        "SELECT trait_name FROM experiment_traits WHERE exp_id=%s",
        conn, params=[exp_id]
    )
    traits = traits_df["trait_name"].tolist()

    # -------------------------------------------------
    # TRAIT SELECTION (RESTORED ON SAVE)
    # -------------------------------------------------
    st.subheader("Select columns (H onwards)")

    selected_traits = st.multiselect(
        "Traits",
        traits,
        default=st.session_state.selected_traits
    )

    if st.button("▶ Start Entry") and selected_traits:
        st.session_state.entry_started = True
        st.session_state.selected_traits = selected_traits

    # -------------------------------------------------
    # TABLE RENDER
    # -------------------------------------------------
    if st.session_state.entry_started and st.session_state.selected_traits:

        selected_traits = st.session_state.selected_traits

        fixed_cols = [
            "exp_id","location","year",
            "season","replication","block","treatment"
        ]
        all_cols = fixed_cols + selected_traits

        is_locked = meta_df["entry_status"].eq("Submitted").any()

        header = st.columns(len(all_cols))
        for i, c in enumerate(all_cols):
            header[i].markdown(f"**{c.upper()}**")

        with st.form("entry_form"):
            values = {}

            for _, r in meta_df.iterrows():
                cols = st.columns(len(all_cols))

                for i, c in enumerate(fixed_cols):
                    cols[i].write(r[c])

                for j, t in enumerate(selected_traits):
                    idx = len(fixed_cols) + j
                    key = f"{r['id']}|{t}"

                    old = pd.read_sql(
                        """
                        SELECT attribute_value FROM observation_data
                        WHERE metadata_id=%s AND attribute_name=%s
                        """,
                        conn, params=[r["id"], t]
                    )

                    default = float(old.iloc[0][0]) if not old.empty else 0.0

                    values[key] = cols[idx].number_input(
                        t,
                        value=default,
                        key=f"in_{r['id']}_{t}",
                        label_visibility="collapsed",
                        disabled=is_locked
                    )

            c1, c2 = st.columns(2)
            save = c1.form_submit_button("💾 Save")
            submit = c2.form_submit_button("✅ Submit")

        cur = conn.cursor()

        if save:
            for k, v in values.items():
                mid, trait = k.split("|")

                cur.execute(
                    "DELETE FROM observation_data WHERE metadata_id=%s AND attribute_name=%s",
                    (int(mid), trait)
                )
                cur.execute(
                    """
                    INSERT INTO observation_data
                    (metadata_id, attribute_name, attribute_value)
                    VALUES (%s,%s,%s)
                    """,
                    (int(mid), trait, float(v))
                )

            cur.execute("UPDATE experiment_metadata SET entry_status='Draft'")
            conn.commit()
            st.success("Saved — you can continue later")

        if submit:
            cur.execute("UPDATE experiment_metadata SET entry_status='Submitted'")
            conn.commit()

            # RESET SESSION (IMPORTANT)
            st.session_state.entry_started = False
            st.session_state.selected_traits = []

            st.success("Submitted — data locked")

    conn.close()
