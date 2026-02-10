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

# --- 4. ממשק משתמש משופר ---
st.title("🛡️ Alpha Market Hunter - סורק הזדמנויות")

st.sidebar.header("⚙️ פילטרים והגדרות חיפוש")

# הוספת יחידות (format) והסברים מונגשים
min_roe = st.sidebar.slider(
    "מינימום תשואה על ההון (ROE)", 
    min_value=0, max_value=50, value=10, format="%d%%",
    help="מראה כמה רווח החברה מייצרת על כל שקל של בעלי המניות. 15% ומעלה נחשב לניהול איכותי מאוד."
)

max_debt = st.sidebar.slider(
    "מקסימום יחס חוב/הון", 
    min_value=0, max_value=200, value=150,
    help="מעל 100 אומר שלחברה יש יותר חובות מהון עצמי. ככל שהמספר נמוך יותר, החברה יציבה וחסינה יותר למשברים."
)

max_peg = st.sidebar.slider(
    "מקסימום יחס PEG", 
    min_value=0.5, max_value=5.0, value=2.5, step=0.1,
    help="היחס בין המחיר לצמיחה. מספר נמוך מ-1 אומר שאתם קונים את הצמיחה העתידית ב'הנחה'."
)

min_upside = st.sidebar.slider(
    "מינימום פוטנציאל רווח (Upside)", 
    min_value=-20, max_value=100, value=5, format="%d%%",
    help="הפער באחוזים בין מחיר השוק לבין מה שהמניה באמת שווה לדעתנו. ככל שזה גבוה יותר, ההזדמנות גדולה יותר."
)

target_pe = st.sidebar.number_input(
    "מכפיל יעד (P/E)", 
    min_value=5, max_value=50, value=15,
    help="באיזה מכפיל רווח המניה תיסחר בעוד 5 שנים? חברות טכנולוגיה (כמו Nvidia) מקבלות בדרך כלל 25-30, וחברות יציבות (כמו קוקה קולה) 15-20."
)

growth = st.sidebar.slider(
    "צמיחת רווח שנתית חזויה", 
    min_value=1, max_value=50, value=10, format="%d%%",
    help="הקצב שבו הרווחים של החברה יגדלו בכל שנה ב-5 השנים הקרובות. זה המנוע העיקרי לעליית מחיר המניה."
) / 100

use_ma200 = st.sidebar.checkbox(
    "סינון מניות במגמת ירידה (MA200)", 
    value=False, 
    help="מגן עליכם מפני 'סכינים נופלות'. מסנן מניות שהמחיר שלהן נמצא מתחת לממוצע של חצי השנה האחרונה."
)

limit = st.sidebar.number_input("כמות מניות לסריקה", 10, 100, 40)

params = {
    'min_roe': min_roe, 'max_debt': max_debt, 'max_peg': max_peg,
    'min_upside': min_upside, 'target_pe': target_pe, 'growth': growth,
    'use_ma200': use_ma200, 'limit': limit
}

# --- 5. הרצה והצגת תוצאות ---
if st.button("🚀 התחל סריקת עומק"):
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
        st.subheader(f"✅ נמצאו {len(df)} הזדמנויות קנייה")
        st.dataframe(df, use_container_width=True)
        
        st.info("""
        💡 **טיפ לאנליסט:** מניה עם Score גבוה ו-Upside מעל 20% נחשבת להזדמנות קנייה משמעותית, בתנאי שהצמיחה שהזנתם מציאותית.
        """)
    else:
        st.error("הקריטריונים מחמירים מדי ולא נמצאו התאמות. נסו להוריד את 'מינימום ROE' או להעלות את 'מכפיל היעד'.")
