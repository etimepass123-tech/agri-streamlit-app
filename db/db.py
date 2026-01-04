import streamlit as st
import mysql.connector

def get_connection():
    # This line tells the app: "Don't look at 127.0.0.1. 
    # Look at the 'Secrets' box in my Streamlit settings instead!"
    return mysql.connector.connect(
        host=st.secrets["db_host"],
        port=int(st.secrets["db_port"]),
        user=st.secrets["db_user"],
        password=st.secrets["db_password"],
        database=st.secrets["db_name"]
    )
