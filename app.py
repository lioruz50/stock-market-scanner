import streamlit as st
import yfinance as yf
import pandas as pd

# --- 1. הגדרות דף ותיקון עברית חזותי (CSS) ---
st.set_page_config(page_title="Alpha Market Hunter PRO", layout="wide")

# הזרקת CSS לתיקון כיווניות ויישור טקסט לימין
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    
    html, body, [data-testid="stSidebar"], .main {
        direction: rtl;
        text-align: right;
        font-family: 'Assistant', sans-serif;
    }
    /* תיקון לבועות הסבר (Tooltips) */
    div[data-testid="stTooltipContent"] {
        direction: rtl;
        text-align: right;
    }
    /* יישור כפתורים ותיבות טקסט */
    .stButton>button, .stSelectbox, .stNumberInput {
        direction: rtl;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. משיכת רשימת מניות ---
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

        # חישוב שווי הוגן
        future_eps = eps * ((1 + p['growth']) ** 5)
        fair_value = (future_eps * p['target_pe']) / 1.6 
        upside = ((fair_value / price) - 1) * 100
        
        # חישוב Score (50% ROE, 50% Upside)
        score = round((roe * 50) + (upside * 0.5), 1)
        
        passed = True
        if roe < (p['min_roe']/100) or debt > p['max_debt'] or upside < p['min_upside']:
            passed = False
            
        return {
            "Ticker": ticker,
            "Name": info.get('shortName', ticker),
            "Price": f"${price:.2f}",
            "ROE": f"{roe*100:.1f}%",
            "Upside": f"{upside:.1f}%",
            "Score": score,
            "Passed": passed
        }
    except: return None

# --- 4. ממשק משתמש ---
st.title("🛡️ Alpha Market Hunter - סורק הזדמנויות")

# כפתורי מצבים (Presets)
st.subheader("⚡ בחר סגנון סריקה מהיר")
c1, c2, c3 = st.columns(3)

if 'min_roe' not in st.session_state:
    st.session_state.min_roe, st.session_state.min_upside, st.session_state.max_debt = 12, 10, 120
    st.session_state.target_pe, st.session_state.growth = 15, 10

with c1:
    if st.button("🟢 מצב מקל (חיפוש רחב)"):
        st.session_state.min_roe, st.session_state.min_upside, st.session_state.max_debt = 5, -5, 200
        st.session_state.target_pe, st.session_state.growth = 20, 15
with c2:
    if st.button("🔵 מצב הוגן (מאוזן)"):
        st.session_state.min_roe, st.session_state.min_upside, st.session_state.max_debt = 12, 10, 120
        st.session_state.target_pe, st.session_state.growth = 15, 10
with c3:
    if st.button("🔴 מצב מחמיר (יהלומים בלבד)"):
        st.session_state.min_roe, st.session_state.min_upside, st.session_state.max_debt = 20, 25, 80
        st.session_state.target_pe, st.session_state.growth = 12, 8

st.divider()

# סרגל צד עם הסברים מעודכנים
st.sidebar.header("⚙️ פילטרים והסברים")

min_roe = st.sidebar.slider("מינימום ROE (%)", 0, 50, st.session_state.min_roe, format="%d%%",
    help="מראה כמה רווח החברה מייצרת מההון העצמי שלה. ככל שיותר גבוה - הניהול יעיל יותר.")

max_debt = st.sidebar.slider("מקסימום חוב/הון", 0, 200, st.session_state.max_debt,
    help="רמת המינוף של החברה. מספר נמוך מעיד על חברה יציבה פיננסית.")

min_upside = st.sidebar.slider("מינימום Upside (%)", -20, 100, st.session_state.min_upside, format="%d%%",
    help="הפער בין מחיר השוק לשווי ההוגן. Upside גבוה אומר שהמניה נסחרת בהנחה.")

target_pe = st.sidebar.number_input("מכפיל יעד (P/E)", 5, 50, st.session_state.target_pe,
    help="המכפיל העתידי הצפוי לחברה (למשל: טכנולוגיה 25, תעשייה 15).")

growth = st.sidebar.slider("צמיחה חזויה שנתית", 1, 50, st.session_state.growth, format="%d%%",
    help="קצב הגידול השנתי הצפוי ברווחים ל-5 השנים הקרובות.") / 100

limit = st.sidebar.number_input("כמות מניות לסריקה", 10, 100, 40)

if st.button("🚀 הרץ סריקה עכשיו"):
    all_res = []
    prog = st.progress(0)
    params = {'min_roe': min_roe, 'max_debt': max_debt, 'min_upside': min_upside, 'target_pe': target_pe, 'growth': growth}
    
    for i, t in enumerate(get_all_tickers()[:int(limit)]):
        res = analyze_stock(t, params)
        if res: all_res.append(res)
        prog.progress((i + 1) / int(limit))
    
    if all_res:
        df = pd.DataFrame(all_res).sort_values(by="Score", ascending=False)
        
        st.subheader("✅ הזדמנויות שעברו את הסינון")
        st.dataframe(df[df['Passed'] == True].drop(columns=['Passed']), use_container_width=True)
            
        st.divider()
        st.subheader("📊 דירוג מלא של כל המניות שנסרקו")
        st.dataframe(df.drop(columns=['Passed']), use_container_width=True)

        # הסבר שקוף על השקלול
        st.info(f"""
        ### 🧠 איך חישבנו את התוצאות?
        הציון הסופי (Score) מורכב משילוב של שני גורמים מרכזיים:
        1. **מדד האיכות (50%):** מבוסס על ה-ROE. אנחנו מחפשים חברות עם ניהול יעיל.
        2. **מדד הערך (50%):** מבוסס על ה-Upside. אנחנו מחפשים פער בין המחיר לשווי האמיתי.

        **מה המשמעות?**
        * **מעל 30:** הזדמנות קנייה חזקה.
        * **15-30:** חברה טובה במחיר הוגן.
        * **מתחת ל-15:** המניה יקרה מדי או בסיכון גבוה.
        """)
