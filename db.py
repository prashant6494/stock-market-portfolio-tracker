
import streamlit as st
import mysql.connector


def get_connection():
    return mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        port=int(st.secrets["mysql"]["port"]),
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database="StockPortfolioDB",
        connection_timeout=10
    )
