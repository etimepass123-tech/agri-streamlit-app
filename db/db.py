import streamlit as st
from sqlalchemy import create_engine
import mysql.connector

# This pulls the info from the "Secrets" area of Streamlit Cloud
DB_HOST = st.secrets["db_host"]
DB_PORT = st.secrets["db_port"]
DB_USER = st.secrets["db_user"]
DB_PASS = st.secrets["db_password"]
DB_NAME = st.secrets["db_name"]

def get_engine():
    # Construct connection string for SQLAlchemy
    conn_url = f"mysql+mysqlconnector://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return create_engine(conn_url)

def get_connection():
    # Construct standard connection for Cursors
    return mysql.connector.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )
