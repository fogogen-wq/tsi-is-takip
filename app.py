import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os
import json

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="TSI Yönetim Paneli", layout="wide", page_icon="🚀")

# --- MODERN UI CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    div[data-testid="metric-container"] {
        background-color: #ffffff; border: 1px solid #e0e0e0; padding: 5% 10%;
        border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); transition: transform 0.2s ease-in-out;
    }
    div[data-testid="metric-container"]:hover { transform: translateY(-3px); box-shadow: 0 8px 15px rgba(0,0,0,0.1); }
    div[data-testid="stExpander"], div[data-testid="stVerticalBlock"] > div > div { border-radius: 10px; }
    div.stButton > button { border-radius: 8px; font-weight: 600; transition: all 0.3s ease; }
</style>
""", unsafe_allow_html=True)

# --- 1. VERİTABANI YÖNETİMİ ---
DB_FILE = "tsi_is_takip_veritabani.csv"
USER_DB = "kullanicilar.csv"

# Kullanıcı Veritabanı
def kullanici_yukle():
    if os.path.exists(USER_DB):
        return pd.read_csv(USER_DB)
    else:
        df = pd.DataFrame([
            {"KULLANICI_ADI": "Yönetici", "SIFRE": "admin123",
