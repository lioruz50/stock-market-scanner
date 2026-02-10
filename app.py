import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- 1. הגדרות דף ---
st.set_page_config(page_title="Pro Stock Screener 2026", layout="wide")

# --- 2. פונקציות משיכת רשימות מניות ---
@st.cache_data
def get_sp500_tickers():
    # משיכת רשימת S&P 500 מעודכנת
    table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
    return table[0]['Symbol'].tolist()

@st.cache_data(ttl=3600)
def analyze_stock_pro(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1y")
        
        if len(hist) < 200: return None
        
        # 1. פילטר טכני - מניעת "סכינים נופלות"
        current_price = info.get('currentPrice', 0)
        ma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
        if current_price < ma200: return None # המניה במגמת ירידה חזקה
        
        # 2. מדדי איכות (Quality)
        roe = info.get('returnOnEquity', 0)
        debt_to_equity = info.get('debtToEquity', 100) # מעל 100 זה מסוכן
        
        # 3. הערכת שווי (Valuation)
        f_pe = info.get('forwardPE', 0)
        peg = info.get('pegRatio', 0) # PEG מתחת ל-1 נחשב מציאה
        
        # חישוב "ציון איכות" (0-100)
        quality_score = 0
        if roe > 0.15: quality_score += 40  # ROE מעל 15%
        if debt_to_equity < 50: quality_score += 30 # חוב נמוך
        if 0 < peg < 1.5: quality_score += 30 # צמיחה במחיר הוגן
        
        if quality_score < 60: return None # מסננים רק את הטובות ביותר
        
        return {
            "Symbol": ticker,
            "Name": info.get('longName', ticker),
            "Sector": info.get('sector', 'N/A'),
            "Price": current_price,
            "Forward P/E": f_pe,
            "ROE (%)": round(roe * 100, 2),
            "Quality Score": quality_score
        }
    except: return None

# --- 3. ממשק משתמש ---
st.title("🏆 Pro Fundamental & Momentum Screener")
st.write("הסורק מחפש מניות ב-S&P 500 שנמצאות במגמה חיובית, עם חוב נמוך ותשואה גבוהה על ההון.")

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    if st.text_input("Password", type="password") == "3535":
        st.session_state["authenticated"] = True
        st.rerun()
    st.stop()

if st.button("🚀 הרץ סריקה מקצועית (S&P 500)"):
    tickers = get_sp500_tickers()[:50] # נסרוק 50 ראשונות כדוגמה למהירות
    results = []
    
    progress_bar = st.progress(0)
    for i, t in enumerate(tickers):
        res = analyze_stock_pro(t)
        if res: results.append(res)
        progress_bar.progress((i + 1) / len(tickers))
    
    if results:
        df = pd.DataFrame(results).sort_values(by="Quality Score", ascending=False)
        st.subheader("💎 5 המניות המומלצות ביותר לקנייה")
        st.dataframe(df.head(5), use_container_width=True)
    else:
        st.warning("לא נמצאו מניות שעומדות בקריטריונים הקשוחים כרגע.")

st.sidebar.markdown("""
### קריטריונים לסריקה:
1. **מגמה:** מחיר מעל ממוצע נע 200 (מונע מקרי PayPal).
2. **איכות:** תשואה על ההון (ROE) מעל **15%**.
3. **מינוף:** יחס חוב-הון נמוך מ-**50%**.
4. **תמחור:** יחס PEG הוגן (צמיחה ביחס למכפיל).
""")
