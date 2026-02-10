import streamlit as st
import yfinance as yf
import pandas as pd
import requests

# --- 1. הגדרות דף ---
st.set_page_config(page_title="Alpha Market Hunter PRO", layout="wide")

# --- 2. משיכת רשימות מניות (S&P 500 + NASDAQ 100) ---
@st.cache_data(ttl=86400)
def get_all_tickers():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        # משיכת S&P 500
        sp500_url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        sp500_res = requests.get(sp500_url, headers=headers)
        sp500 = pd.read_html(sp500_res.text, flavor='bs4')[0]['Symbol'].tolist()
        
        # משיכת NASDAQ 100
        ndaq_url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
        ndaq_res = requests.get(ndaq_url, headers=headers)
        ndaq = pd.read_html(ndaq_res.text, flavor='bs4')[4]['Ticker'].tolist()
        
        all_tickers = list(set(sp500 + ndaq))
        return sorted([t.replace('.', '-') for t in all_tickers])
    except Exception as e:
        st.error(f"שגיאה במשיכת רשימות: {e}")
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"]

# --- 3. מנוע ניתוח סנטימנט (למניעת מלכודות כמו PayPal) ---
def get_sentiment(ticker):
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        if not news: return 70
        neg_words = ['uncertainty', 'weak', 'cut', 'warning', 'miss', 'negative', 'drop']
        score = 80
        for n in news[:5]:
            if any(w in n['title'].lower() for w in neg_words): score -= 15
        return max(score, 0)
    except: return 50

# --- 4. פונקציית הניתוח המרכזית ---
def analyze_stock(ticker, p):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # שימוש ב-.get() למניעת KeyError
        price = info.get('currentPrice', 0)
        roe = info.get('returnOnEquity', 0)
        debt = info.get('debtToEquity', 999)
        peg = info.get('pegRatio', 0)
        eps = info.get('trailingEps', 0)
        
        # פילטר טכני (ממוצע נע 200)
        hist = stock.history(period="1y")
        if len(hist) < 200: return None
        ma200 = hist['Close'].rolling(200).mean().iloc[-1]
        
        if p['use_ma200'] and price < ma200: return None
        if roe < (p['min_roe']/100) or debt > p['max_debt'] or peg > p['max_peg'] or peg <= 0:
            return None
            
        # חישוב שווי הוגן (DCF שמרני)
        future_eps = eps * ((1 + p['growth']) ** 5)
        fair_value = (future_eps * p['target_pe']) / ((1.10) ** 5)
        upside = ((fair_value / price) - 1) * 100
        
        if upside < p['min_upside']: return None
        
        sentiment = get_sentiment(ticker)
        
        return {
            "Symbol": ticker,
            "Name": info.get('shortName', ticker),
            "Price": f"${price:.2f}",
            "ROE": f"{roe*100:.1f}%",
            "Upside": f"{upside:.1f}%",
            "Sentiment": f"{sentiment}/100",
            "Score": round((roe*40) + (sentiment*0.3) + (upside*0.3), 1)
        }
    except: return None

# --- 5. ממשק משתמש ---
st.title("🛡️ Alpha Market Hunter - סורק הזדמנויות")

st.sidebar.header("⚙️ פרמטרים לחיפוש")
params = {
    'min_roe': st.sidebar.slider("מינימום ROE (%)", 0, 50, 15),
    'max_debt': st.sidebar.slider("מקסימום חוב/הון", 0, 200, 100),
    'max_peg': st.sidebar.slider("מקסימום PEG", 0.5, 3.0, 1.5),
    'min_upside': st.sidebar.slider("מינימום Upside (%)", 0, 100, 20),
    'target_pe': st.sidebar.number_input("מכפיל יעד", 10, 40, 20),
    'growth': st.sidebar.slider("צמיחה שנתית (%)", 5, 30, 12) / 100,
    'use_ma200': st.sidebar.checkbox("פסול מניות במגמת ירידה", value=True),
    'limit': st.sidebar.number_input("כמות מניות לסריקה", 10, 600, 50)
}

if st.button("🚀 התחל סריקה עמוקה"):
    all_tickers = get_all_tickers()
    selected = all_tickers[:params['limit']]
    results = []
    
    progress = st.progress(0)
    status = st.empty()
    
    for i, t in enumerate(selected):
        status.text(f"מנתח את {t}...")
        res = analyze_stock(t, params)
        if res: results.append(res)
        progress.progress((i + 1) / len(selected))
    
    status.empty()
    if results:
        df = pd.DataFrame(results).sort_values(by="Score", ascending=False)
        st.subheader(f"✅ נמצאו {len(df)} הזדמנויות אטרקטיביות")
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("לא נמצאו מניות העונות לקריטריונים אלו כרגע.")
