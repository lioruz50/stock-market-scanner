import streamlit as st
import yfinance as yf
import pandas as pd

# --- 1. הגדרות דף ---
st.set_page_config(page_title="Alpha Market Hunter PRO", layout="wide")

# --- 2. משיכת רשימת מניות יציבה (בלי צורך ב-lxml חיצוני) ---
@st.cache_data(ttl=86400)
def get_all_tickers():
    # רשימה איכותית קבועה למניעת תקלות התחברות לויקיפדיה
    return [
        "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AVGO", "COST", "NFLX",
        "ADBE", "CRM", "AMD", "QCOM", "TXN", "INTC", "MU", "AMAT", "LRCX", "TSM",
        "V", "MA", "JPM", "BAC", "WMT", "DIS", "NKE", "ORCL", "UNH", "PFE",
        "XOM", "CVX", "LLY", "ABBV", "MRK", "HD", "PEP", "KO", "TMO", "COST"
    ]

# --- 3. פונקציית ניתוח עם "הגמשת שגיאות" ---
def analyze_stock(ticker, p):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # שימוש ב-.get() עם ערכי ברירת מחדל כדי לא לפסול מניות על מידע חסר
        price = info.get('currentPrice', 0)
        roe = info.get('returnOnEquity', 0.10) # אם חסר, נניח 10%
        debt = info.get('debtToEquity', 50)   # אם חסר, נניח חוב סביר
        peg = info.get('pegRatio', 1.0)       # אם חסר, נניח מכפיל הוגן
        eps = info.get('trailingEps', 1)
        
        if price == 0: return None

        # בדיקת ממוצע נע - אם המשתמש ביקש
        if p['use_ma200']:
            hist = stock.history(period="1y")
            if len(hist) >= 200:
                ma200 = hist['Close'].rolling(200).mean().iloc[-1]
                if price < ma200: return None

        # סינון לפי קריטריונים (בדיקה שמרנית)
        if roe < (p['min_roe']/100) or debt > p['max_debt']:
            return None
            
        # חישוב שווי הוגן פשוט יותר (מכפיל יעד כפול רווח חזוי)
        # נוסחה: Fair Value = EPS * (1 + Growth)^5 * Target_PE / Discount_Factor
        future_eps = eps * ((1 + p['growth']) ** 5)
        fair_value = (future_eps * p['target_pe']) / 1.6 # מהוון ב-10% ל-5 שנים
        upside = ((fair_value / price) - 1) * 100
        
        if upside < p['min_upside']: return None
        
        return {
            "Symbol": ticker,
            "Name": info.get('shortName', ticker),
            "Price": f"${price:.2f}",
            "ROE": f"{roe*100:.1f}%",
            "Upside": f"{upside:.1f}%",
            "Score": round((roe*50) + (upside*0.5), 1)
        }
    except:
        return None

# --- 4. ממשק משתמש ---
st.title("🛡️ Alpha Market Hunter - סורק הזדמנויות")

st.sidebar.header("⚙️ פרמטרים לחיפוש")
params = {
    'min_roe': st.sidebar.slider("מינימום ROE (%)", 0, 50, 10),
    'max_debt': st.sidebar.slider("מקסימום חוב/הון", 0, 200, 150),
    'max_peg': st.sidebar.slider("מקסימום PEG", 0.5, 5.0, 2.5),
    'min_upside': st.sidebar.slider("מינימום Upside (%)", -20, 100, 5),
    'target_pe': st.sidebar.number_input("מכפיל יעד", 5, 50, 15),
    'growth': st.sidebar.slider("צמיחה שנתית (%)", 1, 50, 10) / 100,
    'use_ma200': st.sidebar.checkbox("פסול מניות במגמת ירידה", value=False),
    'limit': st.sidebar.number_input("כמות מניות לסריקה", 10, 100, 40)
}

if st.button("🚀 התחל סריקה עמוקה"):
    all_tickers = get_all_tickers()
    selected = all_tickers[:int(params['limit'])]
    results = []
    
    progress = st.progress(0)
    for i, t in enumerate(selected):
        res = analyze_stock(t, params)
        if res: results.append(res)
        progress.progress((i + 1) / len(selected))
    
    if results:
        df = pd.DataFrame(results).sort_values(by="Score", ascending=False)
        st.subheader(f"✅ נמצאו {len(df)} מניות מתאימות")
        st.dataframe(df, use_container_width=True)
    else:
        st.error("עדיין לא נמצאו תוצאות. נסה להעלות את 'מכפיל יעד' ל-25 או להוריד 'מינימום ROE' ל-5.")
