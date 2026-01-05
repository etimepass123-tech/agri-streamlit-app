import streamlit as st
import mysql.connector
from sqlalchemy import create_engine

# METHOD 1: Standard Connector (Used for Admin tasks and saving data)
def get_connection():
    return mysql.connector.connect(
        host=st.secrets["db_host"],
        port=int(st.secrets["db_port"]),
        user=st.secrets["db_user"],
        password=st.secrets["db_password"],
        database=st.secrets["db_name"]
    )

# METHOD 2: SQLAlchemy Engine (Used for pd.read_sql to fix your error)
def get_engine():
    # Construct connection string
    conn_url = (
        f"mysql+mysqlconnector://{st.secrets['db_user']}:"
        f"{st.secrets['db_password']}@{st.secrets['db_host']}:"
        f"{st.secrets['db_port']}/{st.secrets['db_name']}"
    )
    return create_engine(conn_url)
