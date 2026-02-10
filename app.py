import streamlit as st
import yfinance as yf
import pandas as pd
import random
import time

# --- 1. הגדרות דף ותיקון עברית ---
st.set_page_config(page_title="Alpha Hunter - Random Market Scanner", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    html, body, [data-testid="stSidebar"], .main {
        direction: rtl; text-align: right; font-family: 'Assistant', sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. משיכת רשימה גלובלית וערבוב אקראי ---
def get_fresh_shuffled_tickers():
    try:
        # משיכת S&P 500
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
        # משיכת NASDAQ 100
        nasdaq100 = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4]['Ticker'].tolist()
        
        full_list = list(set(sp500 + nasdaq100))
        full_list = [t.replace('.', '-') for t in full_list]
        
        # ערבוב הרשימה
        random.shuffle(full_list)
        return full_list
    except:
        # גיבוי במקרה של שגיאת תקשורת
        fallback = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "NFLX", "AVGO", "COST", "BRK-B", "V", "MA"]
        random.shuffle(fallback)
        return fallback

# --- 3. פונקציית ניתוח ---
def analyze_stock(ticker, p):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get('currentPrice', 0)
        if price <= 0: return None

        roe = info.get('returnOnEquity', 0)
        margin = info.get('profitMargins', 0)
        eps = info.get('trailingEps', 1)
        
        # חישוב שווי הוגן (מתכון באפט)
        future_eps = eps * ((1 + p['growth']) ** 5)
        fair_value = (future_eps * p['target_pe']) / 1.6 
        upside = ((fair_value / price) - 1) * 100
        
        # סינון לפי הפרמטרים שהגדרת
        passed = (roe >= (p['min_roe']/100)) and (upside >= p['min_upside']) and (margin >= 0.08)
        
        return {
            "Ticker": ticker,
