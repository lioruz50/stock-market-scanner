import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- 1. הגדרות דף ---
st.set_page_config(page_title="Market Hunter Pro v4", layout="wide")

# --- 2. פונקציות משיכת רשימות (S&P 500 + NASDAQ 100) ---
@st.cache_data
def get_market_tickers():
    # S&P 500 מויקיפדיה
    sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
    # NASDAQ 100 מויקיפדיה
    nasdaq100 = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4]['Ticker'].tolist()
    
    # איחוד והסרת כפילויות
    all_tickers = list(set(sp500 + nasdaq100))
    return sorted([t.replace('.', '-') for t in all_tickers])

# --- 3. מנוע הניתוח המקצועי ---
def get_sentiment_score(ticker):
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        if not news: return 50
        neg_words = ['uncertainty', 'weak', 'cut', 'lawsuit', 'drop', 'warning', 'bad', 'miss']
        score = 80
        for n in news[:3]:
            if any(w in n['title'].lower() for w in neg_words): score -= 20
        return max(score, 0)
    except: return 50

def analyze_stock(ticker, params):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1y")
        
        if len(hist) < 200: return None
        
        # נתונים בסיסיים
        price = info.get('currentPrice', 0)
        roe = info.get('returnOnEquity', 0)
        debt_to_equity = info.get('debtToEquity', 999)
        peg = info.get('pegRatio', 0)
        eps_growth = info.get('earningsGrowth', 0)
        ma200 = hist['Close'].rolling(200).mean().iloc[-1]
        
        # בדיקת קריטריונים דינמית (לפי בחירת המשתמש)
        if params['use_ma200'] and price < ma200: return None
        if roe < (params['min_roe'] / 100): return None
        if debt_to_equity > params['max_debt']: return None
        if peg > params['max_peg'] or peg <= 0: return None
        
        # חישוב Upside (שווי פנימי שמרני)
        fair_value = (info.get('trailingEps', 0) * (1 + params['growth_est'])) * params['target_pe']
        upside = ((fair_value / price) - 1) * 100
        
        if upside < params['min_upside']: return None
        
        sentiment = get_sentiment_score(ticker)
        
        return {
            "Symbol": ticker,
            "Name": info.get('shortName', ticker),
            "Price": price,
            "ROE%": round(roe * 100, 1),
            "Debt/Equity": debt_to_equity,
            "Upside%": round(upside, 1),
            "Sentiment": sentiment,
            "Score": round((roe * 30) + (sentiment * 0.3) + (upside * 0.4), 1)
        }
    except:
        return None

# --- 4. ממשק משתמש (לוח בקרה) ---
st.sidebar.title("⚙️ הגדרות סריקה")
st.sidebar.subheader("קריטריונים פונדמנטליים")
min_roe = st.sidebar.slider("מינימום ROE (%)", 0, 50, 15)
max_debt = st.sidebar.slider("מקסימום יחס חוב/הון", 0, 200, 100)
max_peg = st.sidebar.slider("מקסימום יחס PEG", 0.5, 3.0, 1.5)

st.sidebar.subheader("הערכת שווי (Valuation)")
min_upside = st.sidebar.slider("מינימום Upside מבוקש (%)", 0, 100, 20)
target_pe = st.sidebar.number_input("מכפיל יעד לחישוב שווי", 10, 40, 20)
growth_est = st.sidebar.slider("הערכת צמיחה שנתית (%)", 5, 30, 12) / 100

st.sidebar.subheader("פילטר טכני")
use_ma200 = st.sidebar.checkbox("פסול מניות במגמת ירידה (מתחת ל-MA200)", value=True)

limit_scan = st.sidebar.number_input("כמה מניות לסרוק? (לסריקה מלאה רשום 600)", 10, 600, 50)

# --- 5. הרצת הסריקה ---
st.title("🔍 Market Hunter Pro - סורק הזדמנויות עומק")
st.write(f"הסורק רץ כרגע על מדדי ה-S&P 500 וה-NASDAQ 100 ומחפש מניות שעומדות בהגדרות שלך.")

if st.button("🚀 התחל סריקה מקיפה"):
    all_tickers = get_market_tickers()
    selected_tickers = all_tickers[:limit_scan]
    
    params = {
        'min_roe': min_roe, 'max_debt': max_debt, 'max_peg': max_peg,
        'min_upside': min_upside, 'target_pe': target_pe, 'growth_est': growth_est,
        'use_ma200': use_ma200
    }
    
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, t in enumerate(selected_tickers):
        status_text.text(f"בודק את {t} ({i+1}/{len(selected_tickers)})...")
        res = analyze_stock(t, params)
        if res: results.append(res)
        progress_bar.progress((i + 1) / len(selected_tickers))
    
    status_text.text("הסריקה הושלמה!")
    
    if results:
        df = pd.DataFrame(results).sort_values(by="Score", ascending=False)
        st.subheader(f"✅ נמצאו {len(df)} הזדמנויות קנייה")
        
        # תצוגה מעוצבת
        st.dataframe(df.style.background_gradient(subset=['Score', 'Upside%'], cmap='RdYlGn'), use_container_width=True)
        
        # כפתור הורדה למכירה/דוח
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 הורד דוח הזדמנויות (CSV)", csv, "opportunities.csv", "text/csv")
    else:
        st.error("לא נמצאו מניות שעונות על כל הקריטריונים. נסה להקל מעט בהגדרות (למשל להוריד ROE או להעלות PEG).")

# --- 6. הסבר למשקיע ---
with st.expander("ℹ️ איך עובד מודל ה-Score?"):
    st.write("""
    הציון הסופי משקלל שלושה עולמות:
    1. **איכות הניהול (30%):** מבוסס על ROE - כמה החברה יודעת לייצר כסף מההון שלה.
    2. **ביטחון וסנטימנט (30%):** ניתוח חדשות ופילטר טכני למניעת כניסה לחברות ב'משבר אמון'.
    3. **פוטנציאל כלכלי (40%):** הפער בין המחיר הנוכחי לשווי הפנימי (DCF שמרני).
    """)
