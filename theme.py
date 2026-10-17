import streamlit as st

def apply_skyrim_theme():
    st.markdown("""
        <style>
        .stApp {
            background-color: #1a1612;
            color: #d4c4a8;
            font-family: 'Georgia', serif;
        }
        h1, h2, h3, h4 {
            color: #dfb76c !important;
            text-shadow: 2px 2px #000000;
        }
        .stButton>button {
            background-color: #4a3b2c;
            color: #dfb76c;
            border: 1px solid #dfb76c;
            width: 100%;
        }
        .stButton>button:hover {
            background-color: #614e3a;
            color: #fff;
            border: 1px solid #fff;
        }
        div[data-testid="stExpander"] {
            background-color: #26201a;
            border: 1px solid #4a3b2c;
        }
        </style>
        """, unsafe_allow_html=True)
