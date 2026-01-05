import streamlit as st
from sqlalchemy import create_engine
import mysql.connector

# We keep this for cursor operations (Admin tasks)
def get_connection():
    return mysql.connector.connect(
        host=st.secrets["db_host"],
        port=int(st.secrets["db_port"]),
        user=st.secrets["db_user"],
        password=st.secrets["db_password"],
        database=st.secrets["db_name"]
    )

# WE ADD THIS for Pandas operations (Reading Data)
def get_engine():
    conn_url = (
        f"mysql+mysqlconnector://{st.secrets['db_user']}:"
        f"{st.secrets['db_password']}@{st.secrets['db_host']}:"
        f"{st.secrets['db_port']}/{st.secrets['db_name']}"
    )
    return create_engine(conn_url)
