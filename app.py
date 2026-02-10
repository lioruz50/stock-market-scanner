import streamlit as st
import yfinance as yf
import pandas as pd

# --- 1. הגדרות דף ותיקון עברית (CSS) ---
st.set_page_config(page_title="Alpha Market Hunter PRO", layout="wide")

# הזרקת CSS ליישור לימין עבור כל האפליקציה
st.markdown("""
    <style>
    .main, .sidebar-content, div[role="tooltip"] {
        direction: rtl;
        text-align: right;
    }
    div.stButton > button {
        direction: rtl;
    }
    /* תיקון ספציפי לטקסט עזרה שיוצא מהסליידרים */
    .stTooltipIcon {
        order: -1;
        margin-left: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

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

        future_eps = eps * ((1 + p['growth']) ** 5)
        fair_value = (future_eps * p['target_pe']) / 1.6 
        upside = ((fair_value / price) - 1) * 100
        
        score = round((roe * 50) + (upside * 0.5), 1)
        
        passed = True
        if roe < (p['min_roe']/100) or debt > p['max_debt'] or upside < p['min_upside']:
            passed = False
            
        if p['use_ma200']:
            hist = stock.history(period="1y")
            if len(hist) >= 200:
                ma200 = hist['Close'].rolling(200).mean().iloc[-1]
                if price < ma200: passed = False

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

st.subheader("⚡ בחר סגנון סריקה מהיר")
col1, col2, col3 = st.columns(3)

if 'min_roe' not in st.session_state:
    st.session_state.min_roe, st.session_state.min_upside, st.session_state.max_debt = 12, 10, 120
    st.session_state.target_pe, st.session_state.growth = 15, 10

with col1:
    if st.button("🟢 מצב מקל (חיפוש רחב)"):
        st.session_state.min_roe, st.session_state.min_upside, st.session_state.max_debt = 5, -5, 200
        st.session_state.target_pe, st.session_state.growth = 20, 15
with col2:
    if st.button("🔵 מצב הוגן (מאוזן)"):
        st.session_state.min_roe, st.session_state.min_upside, st.session_state.max_debt = 12, 10, 120
        st.session_state.target_pe, st.session_state.growth = 15, 10
with col3:
    if st.button("🔴 מצב מחמיר (יהלומים בלבד)"):
        st.session_state.min_roe, st.session_state.min_upside, st.session_state.max_debt = 20, 25, 80
        st.session_state.target_pe, st.session_state.growth = 12, 8

st.divider()

st.sidebar.header("⚙️ פילטרים והסברים")

min_roe = st.sidebar.slider("מינימום ROE (%)", 0, 50, st.session_state.min_roe, format="%d%%",
    help="מראה כמה רווח החברה מייצרת מההון העצמי שלה. מעל 15% מעיד על ניהול מצוין.")

max_debt = st.sidebar.slider("מקסימום חוב/הון", 0, 200, st.session_state.max_debt,
    help="ככל שהמספר נמוך יותר, החברה פחות מסוכנת וחסינה יותר למשברים פיננסיים.")

min_upside = st.sidebar.slider("מינימום Upside (%)", -20, 100, st.session_state.min_upside, format="%d%%",
    help="הפער בין מחיר השוק לשווי ההוגן. Upside גבוה אומר שהמניה נסחרת בהנחה.")

target_pe = st.sidebar.number_input("מכפיל יעד (P/E)", 5, 50, st.session_state.target_pe,
    help="המכפיל שאתה צופה לחברה בעתיד. חברות טכנולוגיה מקבלות בדרך כלל 25+, יציבות 15.")

growth = st.sidebar.slider("צמיחה חזויה שנתית", 1, 50, st.session_state.growth, format="%d%%",
    help="קצב גידול הרווחים הצפוי. זה המנוע שדוחף את מחיר המניה למעלה.") / 100

use_ma200 = st.sidebar.checkbox("סינון סכינים נופלות (MA200)", value=False,
    help="מוודא שהמניה לא נמצאת במגמת ירידה חדה על ידי בדיקת ממוצע המחיר ב-200 הימים האחרונים.")

limit = st.sidebar.number_input("כמות מניות לסריקה", 10, 100, 40)

params = {'min_roe': min_roe, 'max_debt': max_debt, 'min_upside': min_upside, 'target_pe': target_pe, 'growth': growth, 'use_ma200': use_ma200}

if st.button("🚀 הרץ סריקה"):
    all_scanned = []
    progress = st.progress(0)
    for i, t in enumerate(get_all_tickers()[:int(limit)]):
        res = analyze_stock(t, params)
        if res: all_scanned.append(res)
        progress.progress((i + 1) / int(limit))
    
    if all_scanned:
        df_all = pd.DataFrame(all_scanned).sort_values(by="Score", ascending=False)
        passed_df = df_all[df_all['Passed'] == True].drop(columns=['Passed'])
        
        st.subheader(f"✅ הזדמנויות שעברו את הסינון ({len(passed_df)})")
        st.dataframe(passed_df, use_container_width=True)
            
        st.divider()
        st.subheader("📊 דירוג מלא של כל המניות שנסרקו")
        st.dataframe(df_all.drop(columns=['Passed']), use_container_width=True)

        st.success("""
        ### 🧠 איך חישבנו את התוצאות?
        הציון הסופי (**Score**) מורכב משילוב של שני גורמים מרכזיים:
        1. **מדד האיכות (50%):** מבוסס על ה-**ROE**. אנחנו מחפשים חברות עם ניהול יעיל.
        2. **מדד הערך (50%):** מבוסס על ה-**Upside**. אנחנו מחפשים פער בין המחיר לשווי האמיתי.

        **מה המשמעות?**
        * **מעל 30:** הזדמנות קנייה חזקה.
        * **15-30:** חברה טובה במחיר הוגן.
        * **מתחת ל-15:** המניה יקרה מדי או בסיכון גבוה.
        """)
