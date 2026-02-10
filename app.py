import streamlit as st
import yfinance as yf
import pandas as pd

# --- 1. הגדרות דף ---
st.set_page_config(page_title="Alpha Screener Pro", layout="wide")

# --- 2. מנגנון ניתוח סנטימנט (חדשות) ---
def get_sentiment_score(ticker):
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        if not news: return 50 # נייטרלי
        
        # מילות מפתח שליליות שמתריעות על בעיות (כמו ב-PayPal)
        negative_words = ['warn', 'lawsuit', 'cut', 'miss', 'uncertainty', 'crash', 'drop', 'negative']
        score = 70 # נקודת פתיחה חיובית
        
        for n in news[:5]: # בודק 5 כותרות אחרונות
            title = n['title'].lower()
            if any(word in title for word in negative_words):
                score -= 15
        return max(score, 0)
    except: return 50

# --- 3. פונקציית ניתוח פונדמנטלי עמוק ---
@st.cache_data(ttl=3600)
def deep_analyze(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1y")
        
        # פילטר 1: מגמה (MA200) - מונע קניית "סכינים נופלות"
        price = info.get('currentPrice', 0)
        ma200 = hist['Close'].rolling(200).mean().iloc[-1]
        if price < ma200: return None 
        
        # פילטר 2: איכות הניהול (ROE & Profit Margin)
        roe = info.get('returnOnEquity', 0)
        margin = info.get('profitMargins', 0)
        
        # פילטר 3: תמחור וצמיחה (PEG & FCF)
        peg = info.get('pegRatio', 0)
        fcf = info.get('freeCashflow', 0)
        
        if roe < 0.15 or margin < 0.10: return None # מסנן חברות לא רווחיות מספיק
        
        # חישוב ציון משוקלל (Score)
        sentiment = get_sentiment_score(ticker)
        final_score = (roe * 100 * 0.4) + (sentiment * 0.4) + ((1/peg if peg > 0 else 0) * 10)
        
        return {
            "Symbol": ticker,
            "Name": info.get('shortName', ticker),
            "Price": f"${price:.2f}",
            "ROE": f"{roe*100:.1f}%",
            "Margin": f"{margin*100:.1f}%",
            "Sentiment": f"{sentiment}/100",
            "Final Score": round(final_score, 1)
        }
    except: return None

# --- 4. ממשק המשתמש ---
st.title("🛡️ Alpha Screener Pro - מערכת בחירת מניות")
st.write("סורק S&P 500 המשלב פונדמנטלי, טכני וסנטימנט חדשותי למניעת מלכודות ערך.")

if "auth" not in st.session_state: st.session_state["auth"] = False
if not st.session_state["auth"]:
    if st.text_input("קוד גישה למערכת:", type="password") == "3535":
        st.session_state["auth"] = True
        st.rerun()
    st.stop()

# רשימת מניות לסריקה (Big Tech & S&P Leaders)
watch_list = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AVGO", "COST", "NFLX", "ADBE", "CRM", "AMD", "QCOM", "TXN"]

if st.button("🚀 הרץ סריקה מבוססת AI וסנטימנט"):
    results = []
    progress = st.progress(0)
    
    for i, t in enumerate(watch_list):
        res = deep_analyze(t)
        if res: results.append(res)
        progress.progress((i + 1) / len(watch_list))
    
    if results:
        df = pd.DataFrame(results).sort_values(by="Final Score", ascending=False)
        st.subheader("💎 המניות האטרקטיביות ביותר כרגע")
        st.dataframe(df, use_container_width=True)
        
        st.success(f"נמצאו {len(df)} מניות שעומדות בקריטריונים המחמירים.")
    else:
        st.error("השוק כרגע בתנודתיות גבוהה - לא נמצאו מניות בטוחות לקנייה.")

st.sidebar.info("""
**איך המודל עובד?**
1. **טכני:** פוסל מניות במגמת ירידה חדה.
2. **חדשות:** סורק כותרות למניעת אי-ודאות (PayPal Case).
3. **פונדמנטלי:** ROE מעל 15% ושולי רווח מעל 10%.
""")
