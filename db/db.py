import streamlit as st
import mysql.connector

def get_connection():
    # This reads the database info from the "Secrets" area of Streamlit Cloud
    return mysql.connector.connect(
        host=st.secrets["db_host"],
        port=int(st.secrets["db_port"]),
        user=st.secrets["db_user"],
        password=st.secrets["db_password"],
        database=st.secrets["db_name"]
    )
    
