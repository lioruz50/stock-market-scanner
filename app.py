import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- 1. הגדרות ועיצוב ---
st.set_page_config(page_title="Opportunity Hunter Pro", layout="wide")

# --- 2. מנוע החישוב של "הזדמנות קנייה" ---
def calculate_intrinsic_value(ticker_data, growth_rate=0.12, discount_rate=0.10):
    """
    מחשב שווי הוגן לפי מודל DCF מקוצר - בדיוק כמו באקסל שלך
    """
    try:
        current_price = ticker_data['price']
        eps = ticker_data['eps'] # רווח למניה
        
        # חישוב רווח חזוי ל-5 שנים
        future_eps = eps * ((1 + growth_rate) ** 5)
        # מכפיל יעד שמרני (ממוצע היסטורי או 20)
        target_pe = min(ticker_data['pe'], 25) 
        
        future_value = future_eps * target_pe
        fair_value_today = future_value / ((1 + discount_rate) ** 5)
        
        upside = ((fair_value_today / current_price) - 1) * 100
        return round(fair_value_today, 2), round(upside, 1)
    except:
        return 0, 0

@st.cache_data(ttl=3600)
def scan_for_opportunities(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1y")
        
        # פילטרים של איכות (Quality)
        data = {
            "price": info.get('currentPrice', 0),
            "eps": info.get('trailingEps', 0),
            "pe": info.get('trailingPE', 20),
            "roe": info.get('returnOnEquity', 0),
            "debt_to_equity": info.get('debtToEquity', 100),
            "fcf": info.get('freeCashflow', 0)
        }
        
        # תנאי סף למניעת "זבל" או "סכינים נופלות"
        ma200 = hist['Close'].rolling(200).mean().iloc[-1]
        if data['price'] < ma200 or data['roe'] < 0.15 or data['eps'] <= 0:
            return None
            
        fair_value, upside = calculate_intrinsic_value(data)
        
        # הגדרת "הזדמנות" - רק אם יש Upside של מעל 15%
        if upside > 15:
            return {
                "Ticker": ticker,
                "Name": info.get('shortName', ticker),
                "Current Price": f"${data['price']:.2f}",
                "Fair Value": f"${fair_value:.2f}",
                "Upside": f"{upside}%",
                "Quality Score": round(data['roe'] * 100, 1)
            }
    except:
        return None

# --- 3. ממשק משתמש ---
st.title("🎯 Opportunity Hunter - איתור הזדמנויות קנייה")
st.write("המערכת סורקת מניות מובילות ומציגה רק את אלו שנסחרות ב'הנחה' משמעותית מתחת לשווי ההוגן שלהן.")

if st.button("🚀 חפש הזדמנויות ב-S&P 500"):
    # רשימה מורחבת של מובילות שוק
    market_leaders = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AVGO", "COST", "NFLX", "ADBE", "CRM", "AMD", "QCOM", "V", "MA", "JPM", "UNH"]
    
    opportunities = []
    bar = st.progress(0)
    
    for i, t in enumerate(market_leaders):
        res = scan_for_opportunities(t)
        if res:
            opportunities.append(res)
        bar.progress((i + 1) / len(market_leaders))
        
    if opportunities:
        df = pd.DataFrame(opportunities).sort_values(by="Upside", ascending=False)
        st.subheader("💎 הזדמנויות קנייה שנמצאו (Sorted by Upside)")
        st.table(df)
    else:
        st.warning("לא נמצאו הזדמנויות קנייה שעומדות בקריטריונים המחמירים כרגע.")
