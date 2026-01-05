import streamlit as st
import pandas as pd
from db.db import get_connection, get_engine # Added get_engine
import io

# ... [KEEP YOUR PAGE CONFIG AND SESSION STATE AS IS] ...

# =================================================
# USER PANEL
# =================================================
else:
    st.title("📊 Excel-like Data Entry")

    # Use ENGINE for pandas
    engine = get_engine()
    
    meta_df = pd.read_sql("SELECT * FROM experiment_metadata WHERE is_active=1", engine)

    if meta_df.empty:
        st.warning("No active experiment available")
        st.stop()

    exp_id = meta_df.iloc[0]["exp_id"]
    traits_df = pd.read_sql("SELECT trait_name FROM experiment_traits WHERE exp_id=%s", engine, params=[exp_id])
    traits = traits_df["trait_name"].tolist()

    # TRAIT SELECTION
    st.subheader("Select columns (H onwards)")
    selected_traits = st.multiselect("Traits", traits, default=st.session_state.selected_traits)

    if st.button("▶ Start Entry") and selected_traits:
        st.session_state.entry_started = True
        st.session_state.selected_traits = selected_traits

    # TABLE RENDER
    if st.session_state.entry_started and st.session_state.selected_traits:
        selected_traits = st.session_state.selected_traits
        fixed_cols = ["exp_id","location","year","season","replication","block","treatment"]
        all_cols = fixed_cols + selected_traits

        # Fetch ALL existing observation data at once (MUCH FASTER)
        obs_df = pd.read_sql("SELECT metadata_id, attribute_name, attribute_value FROM observation_data", engine)

        is_locked = meta_df["entry_status"].eq("Submitted").any()

        with st.form("entry_form"):
            values = {}
            for _, r in meta_df.iterrows():
                cols = st.columns(len(all_cols))
                for i, c in enumerate(fixed_cols):
                    cols[i].write(r[c])

                for j, t in enumerate(selected_traits):
                    idx = len(fixed_cols) + j
                    key = f"{r['id']}|{t}"

                    # Instead of a query inside the loop, we filter the obs_df we fetched earlier
                    match = obs_df[(obs_df['metadata_id'] == r['id']) & (obs_df['attribute_name'] == t)]
                    default = float(match.iloc[0]['attribute_value']) if not match.empty else 0.0

                    values[key] = cols[idx].number_input(
                        t, value=default, key=f"in_{r['id']}_{t}",
                        label_visibility="collapsed", disabled=is_locked
                    )

            c1, c2 = st.columns(2)
            save = c1.form_submit_button("💾 Save")
            submit = c2.form_submit_button("✅ Submit")

        if save or submit:
            conn = get_connection() # Use standard connection for saving
            cur = conn.cursor()
            for k, v in values.items():
                mid, trait = k.split("|")
                cur.execute("DELETE FROM observation_data WHERE metadata_id=%s AND attribute_name=%s", (int(mid), trait))
                cur.execute("INSERT INTO observation_data (metadata_id, attribute_name, attribute_value) VALUES (%s,%s,%s)", (int(mid), trait, float(v)))
            
            status = 'Submitted' if submit else 'Draft'
            cur.execute(f"UPDATE experiment_metadata SET entry_status='{status}'")
            conn.commit()
            conn.close()
            st.success(f"Status updated to {status}")
            if submit:
                st.session_state.entry_started = False
                st.rerun()
