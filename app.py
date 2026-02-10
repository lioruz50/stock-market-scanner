import streamlit as st
import yfinance as yf
import pandas as pd

# --- 1. הגדרות דף ---
st.set_page_config(page_title="Alpha Market Hunter PRO", layout="wide")

# --- 2. משיכת רשימת מניות יציבה ---
@st.cache_data(ttl=86400)
def get_all_tickers():
    return [
        "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AVGO", "COST", "NFLX",
        "ADBE", "CRM", "AMD", "QCOM", "TXN", "INTC", "MU", "AMAT", "LRCX", "TSM",
        "V", "MA", "JPM", "BAC", "WMT", "DIS", "NKE", "ORCL", "UNH", "PFE",
        "XOM", "CVX", "LLY", "ABBV", "MRK", "HD", "PEP", "KO", "TMO", "CSCO"
    ]

# --- 3. פונקציית ניתוח ---
def analyze_stock(ticker, p):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get('currentPrice', 0)
        roe = info.get('returnOnEquity', 0.10)
        debt = info.get('debtToEquity', 50)
        eps = info.get('trailingEps', 1)
        
        if price == 0: return None

        if p['use_ma200']:
            hist = stock.history(period="1y")
            if len(hist) >= 200:
                ma200 = hist['Close'].rolling(200).mean().iloc[-1]
                if price < ma200: return None

        if roe < (p['min_roe']/100) or debt > p['max_debt']:
            return None
            
        # חישוב שווי הוגן
        future_eps = eps * ((1 + p['growth']) ** 5)
        fair_value = (future_eps * p['target_pe']) / 1.6 
        upside = ((fair_value / price) - 1) * 100
        
        if upside < p['min_upside']: return None
        
        return {
            "Ticker": ticker,
            "Name": info.get('shortName', ticker),
            "Price": f"${price:.2f}",
            "ROE": f"{roe*100:.1f}%",
            "Upside": f"{upside:.1f}%",
            "Score": round((roe*50) + (upside*0.5), 1)
        }
    except: return None

# --- 4. ממשק משתמש עם הסברים ---
st.title("🛡️ Alpha Market Hunter - סורק הזדמנויות")

st.sidebar.header("⚙️ פילטרים והסברים")

# הגדרת הפרמטרים עם הסברים מפורטים (Help Tooltips)
min_roe = st.sidebar.slider("מינימום ROE (%)", 0, 50, 10, 
    help="מדד ליעילות הניהול. ROE של 15% ומעלה נחשב מצוין ומעיד שהחברה יודעת לייצר רווח גבוה מההון של בעלי המניות.")

max_debt = st.sidebar.slider("מקסימום חוב/הון", 0, 200, 150, 
    help="מראה כמה החברה ממונפת. ככל שהמספר נמוך יותר, החברה פחות מסוכנת מבחינה פיננסית. מעל 100 נחשב לרמת חוב גבוהה.")

max_peg = st.sidebar.slider("מקסימום PEG", 0.5, 5.0, 2.5, 
    help="היחס בין המכפיל לצמיחה. PEG מתחת ל-1 נחשב למחיר 'מציאה' ביחס לצמיחה החזויה.")

min_upside = st.sidebar.slider("מינימום Upside (%)", -20, 100, 5, 
    help="הפער באחוזים בין מחיר המניה כרגע לבין השווי ההוגן שחישבנו. ככל שהמספר גבוה יותר, המניה נחשבת לזולה יותר ביחס לערכה.")

target_pe = st.sidebar.number_input("מכפיל יעד", 5, 50, 15, 
    help="המכפיל שאתה צופה שהחברה תקבל בעוד 5 שנים. חברות צמיחה (טכנולוגיה) מקבלות בדרך כלל 25+, חברות יציבות מקבלות 15.")

growth = st.sidebar.slider("צמיחה חזויה (%)", 1, 50, 10, 
    help="בכמה אחוזים לדעתך יגדלו רווחי החברה בכל שנה ב-5 השנים הקרובות.") / 100

use_ma200 = st.sidebar.checkbox("פסול מניות במגמת ירידה", value=False, 
    help="פילטר טכני: פוסל מניות שנסחרות מתחת לממוצע מחירן ב-200 הימים האחרונים. עוזר להימנע מ'סכינים נופלות'.")

limit = st.sidebar.number_input("כמות מניות לסריקה", 10, 100, 40)

params = {
    'min_roe': min_roe, 'max_debt': max_debt, 'max_peg': max_peg,
    'min_upside': min_upside, 'target_pe': target_pe, 'growth': growth,
    'use_ma200': use_ma200, 'limit': limit
}

if st.button("🚀 התחל סריקה עמוקה"):
    all_tickers = get_all_tickers()
    selected = all_tickers[:int(limit)]
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
        
        # הסבר על הדירוג
        st.info("""
        **איך לקרוא את התוצאות?**
        * **Score גבוה:** שילוב אופטימלי של ניהול יעיל (ROE גבוה) ומחיר זול (Upside גבוה).
        * **Upside:** פוטנציאל הרווח עד להגעה לשווי ההוגן.
        """)
    else:
        st.error("לא נמצאו תוצאות. נסה להעלות את 'מכפיל יעד' או להוריד 'מינימום ROE' בסרגל הצד.")
