import streamlit as st
import yfinance as yf
import pandas as pd
import time

# --- 1. הגדרות דף ---
st.set_page_config(page_title="Fundamental Scanner", layout="wide")

# --- 2. רשימת מניות S&P 500 (מדגם רחב ומייצג) ---
# הערה: בסביבת ענן, מומלץ להתחיל עם רשימה של 50-100 כדי למנוע חסימה מ-Yahoo
TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "BRK-B", "JPM", "V",
    "UNH", "MA", "PG", "HD", "COST", "AVGO", "ADBE", "CRM", "NFLX", "AMD",
    "BAC", "ADI", "TXN", "MU", "INTC", "PYPL", "INTU", "QCOM", "AMAT", "ISRG"
]

# --- 3. פונקציית משיכה וחישוב ---
@st.cache_data(ttl=3600)
def scan_stock(symbol, g_rate, p_margin, target_pe):
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        if not info or 'currentPrice' not in info:
            return None
        
        price = info.get('currentPrice', 0.0)
        rev = info.get('totalRevenue', 0.0) / 1_000_000
        mc = info.get('marketCap', 0.0) / 1_000_000
        
        # נוסחת המודל (5 שנים קדימה)
        future_rev = rev * ((1 + g_rate) ** 5)
        future_profit = future_rev * p_margin
        shares = mc / price
        
        future_price = (future_profit * target_pe) / shares
        cagr = ((future_price / price) ** (1/5) - 1) * 100
        
        return {
            "Ticker": symbol,
            "Company": info.get('longName', symbol),
            "Price": f"${price:.2f}",
            "Future Price (5Y)": f"${future_price:.2f}",
            "Expected CAGR": round(cagr, 2)
        }
    except:
        return None

# --- 4. ממשק המשתמש ---
st.title("🔍 סורק מניות פונדמנטלי - S&P 500")
st.write("כלי זה סורק רשימת מניות ומדרג אותן לפי פוטנציאל תשואה (CAGR) על בסיס המודל שלך.")

# סרגל צד להגדרת קריטריונים לסריקה
st.sidebar.header("🎯 קריטריונים לסריקה")
st.sidebar.write("הגדר את 'הנחות היסוד' שיחולו על כל המניות בסריקה:")
s_growth = st.sidebar.slider("צמיחה שנתית ממוצעת (%)", 5, 30, 14) / 100 # דיפולט אקסל
s_margin = st.sidebar.slider("שולי רווח נקי (%)", 5, 50, 35) / 100 # דיפולט אקסל
s_pe = st.sidebar.number_input("מכפיל יעד שמרני (P/E)", value=20.0)

# אבטחה בסיסית
if "auth" not in st.session_state:
    st.session_state["auth"] = False

if not st.session_state["auth"]:
    pwd = st.text_input("הזן סיסמה לכניסה:", type="password")
    if pwd == "3535":
        st.session_state["auth"] = True
        st.rerun()
    st.stop()

# --- 5. הרצת הסורק ---
if st.button("🚀 הרץ סריקה על מניות נבחרות"):
    results = []
    progress_text = "סורק נתונים... אנא המתן"
    my_bar = st.progress(0, text=progress_text)
    
    for index, ticker in enumerate(TICKERS):
        res = scan_stock(ticker, s_growth, s_margin, s_pe)
        if res:
            results.append(res)
        # עדכון מד התקדמות
        my_bar.progress((index + 1) / len(TICKERS))
    
    my_bar.empty()
    
    if results:
        df = pd.DataFrame(results)
        # מיון לפי התשואה הגבוהה ביותר
        df_sorted = df.sort_values(by="Expected CAGR", ascending=False)
        
        st.subheader("🏆 5 המניות המבטיחות ביותר (Top Picks)")
        st.table(df_sorted.head(5))
        
        st.write("---")
        st.subheader("📊 כל תוצאות הסריקה")
        st.dataframe(df_sorted, use_container_width=True)
    else:
        st.error("לא הצלחנו למשוך נתונים. נסה שוב בעוד כמה דקות.")

st.info("💡 טיפ: הסורק משתמש במכפיל יעד אחיד לכל המניות. מומלץ לבחון כל מניה בנפרד לאחר הסינון הראשוני.")
