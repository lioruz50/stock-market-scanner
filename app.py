import streamlit as st
import yfinance as yf
import pandas as pd
import random # הוספת ספריית ערבוב

# --- 1. הגדרות דף ---
st.set_page_config(page_title="Alpha Hunter - Deep Scanner", layout="wide")

# --- 2. משיכת רשימה מלאה וערבוב ---
@st.cache_data(ttl=3600) # מטמון קצר יותר כדי לאפשר רענון
def get_shuffled_tickers():
    try:
        # משיכת S&P 500
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
        # משיכת NASDAQ 100
        nasdaq100 = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4]['Ticker'].tolist()
        
        full_list = list(set(sp500 + nasdaq100))
        full_list = [t.replace('.', '-') for t in full_list]
        
        # הקסם: ערבוב הרשימה כדי שלא תקבל תמיד את אותן מניות
        random.shuffle(full_list) 
        return full_list
    except:
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "NFLX"]

# --- 3. פונקציית ניתוח (ללא שינוי) ---
def analyze_stock(ticker, p):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get('currentPrice', 0)
        if price == 0: return None
        
        roe = info.get('returnOnEquity', 0)
        margin = info.get('profitMargins', 0)
        eps = info.get('trailingEps', 1)
        
        future_eps = eps * ((1 + p['growth']) ** 5)
        fair_value = (future_eps * p['target_pe']) / 1.6 
        upside = ((fair_value / price) - 1) * 100
        
        return {
            "Ticker": ticker, "Name": info.get('shortName', ticker),
            "Price": f"${price:.2f}", "ROE": f"{roe*100:.1f}%",
            "Margin": f"{margin*100:.1f}%", "Upside": f"{upside:.1f}%",
            "Score": round((roe * 50) + (upside * 0.5), 1)
        }
    except: return None

# --- 4. ממשק משתמש ---
st.title("🛡️ סורק שוק עמוק (Randomized)")

limit = st.sidebar.number_input("כמות מניות לסריקה אקראית", 10, 500, 30)
growth = st.sidebar.slider("צמיחה חזויה", 1, 50, 10) / 100
target_pe = st.sidebar.number_input("מכפיל יעד", 5, 50, 18)

if st.button("🚀 הרץ סריקה על מניות חדשות"):
    full_list = get_shuffled_tickers()
    selected = full_list[:int(limit)] # עכשיו אלו יהיו מניות אקראיות מכל ה-600!
    
    results = []
    prog = st.progress(0)
    for i, t in enumerate(selected):
        res = analyze_stock(t, {'growth': growth, 'target_pe': target_pe})
        if res: results.append(res)
        prog.progress((i + 1) / len(selected))
    
    if results:
        df = pd.DataFrame(results).sort_values(by="Score", ascending=False)
        st.subheader("📊 תוצאות סריקה אקראית מהשוק המלא")
        st.dataframe(df, use_container_width=True)
