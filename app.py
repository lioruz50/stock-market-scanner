import streamlit as st
import yfinance as yf
import pandas as pd
import random

# --- 1. הגדרות דף ---
st.set_page_config(page_title="Alpha Hunter - Deep Scanner", layout="wide")

# עיצוב עברית
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    html, body, [data-testid="stSidebar"], .main {
        direction: rtl; text-align: right; font-family: 'Assistant', sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. משיכת רשימה מלאה עם מנגנון גיבוי ---
@st.cache_data(ttl=3600)
def get_all_sp500_tickers():
    try:
        # ניסיון למשוך מוויקיפדיה (פותר את השגיאה ב-image_b17703)
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        table = pd.read_html(url)
        return table[0]['Symbol'].tolist()
    except:
        # גיבוי רחב אם ויקיפדיה חסומה
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "V", "JPM", "UNH", "MA", "PG", "HD"]

# --- 3. פונקציית ניתוח מתוקנת (פותרת את image_b1e480) ---
def analyze_stock(ticker, p):
    try:
        stock = yf.Ticker(ticker.replace('.', '-'))
        info = stock.info
        price = info.get('currentPrice', 0)
        if price <= 0: return None

        roe = info.get('returnOnEquity', 0)
        margin = info.get('profitMargins', 0)
        eps = info.get('trailingEps', 1)
        
        # חישוב שווי הוגן
        future_eps = eps * ((1 + p['growth']) ** 5)
        fair_value = (future_eps * p['target_pe']) / 1.6 
        upside = ((fair_value / price) - 1) * 100
        
        # החזרת מילון תקין (סגור היטב)
        return {
            "Ticker": ticker,
            "Name": info.get('shortName', ticker),
            "Price": f"${price:.2f}",
            "ROE": f"{roe*100:.1f}%",
            "Margin": f"{margin*100:.1f}%",
            "Upside": f"{upside:.1f}%",
            "Score": round((roe * 50) + (upside * 0.5), 1)
        }
    except:
        return None

# --- 4. ממשק משתמש ---
st.title("🛡️ סורק שוק עמוק - מדגם אקראי")

st.sidebar.header("⚙️ הגדרות")
limit = st.sidebar.number_input("כמות מניות לסריקה אקראית", 10, 500, 30)
growth = st.sidebar.slider("צמיחה חזויה", 1, 50, 10) / 100
target_pe = st.sidebar.number_input("מכפיל יעד", 5, 50, 18)

if st.button("🔄 רענן והרץ סריקה על מניות חדשות"):
    all_tickers = get_all_sp500_tickers()
    
    # הבטחת אקראיות: בחירת מדגם אקראי מתוך הרשימה המלאה
    sample_size = min(len(all_tickers), int(limit))
    selected = random.sample(all_tickers, sample_size)
    
    results = []
    progress = st.progress(0)
    
    for i, t in enumerate(selected):
        res = analyze_stock(t, {'growth': growth, 'target_pe': target_pe})
        if res: results.append(res)
        progress.progress((i + 1) / len(selected))
    
    if results:
        df = pd.DataFrame(results).sort_values(by="Score", ascending=False)
        st.subheader("📊 דירוג השוק המלא (מדגם אקראי)")
        st.dataframe(df, use_container_width=True)
    else:
        st.error("לא הצלחנו למשוך נתונים. נסה שוב בעוד כמה דקות.")
