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

        # חישוב שווי הוגן ו-Upside
        future_eps = eps * ((1 + p['growth']) ** 5)
        fair_value = (future_eps * p['target_pe']) / 1.6 
        upside = ((fair_value / price) - 1) * 100
        
        # ציון איכות כללי (Score) - מורכב מ-ROE ופוטנציאל רווח
        score = round((roe * 50) + (upside * 0.5), 1)
        
        # האם המניה עוברת את הסינון (לצורך הצגת "הזדמנויות")
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

# --- 4. ממשק משתמש עם כפתורי מצבים ---
st.title("🛡️ Alpha Market Hunter - סורק הזדמנויות")

# כפתורי מצבים אוטומטיים
st.subheader("⚡ בחר סגנון סריקה מהיר")
col1, col2, col3 = st.columns(3)

# אתחול ערכים כברירת מחדל
if 'preset' not in st.session_state:
    st.session_state.preset = "הוגן"

with col1:
    if st.button("🟢 סריקה מקלה (הזדמנויות רבות)"):
        st.session_state.min_roe, st.session_state.min_upside, st.session_state.max_debt = 5, -5, 200
        st.session_state.target_pe, st.session_state.growth = 20, 15
        st.session_state.preset = "מקל"

with col2:
    if st.button("🔵 סריקה הוגנת (מאוזנת)"):
        st.session_state.min_roe, st.session_state.min_upside, st.session_state.max_debt = 12, 10, 120
        st.session_state.target_pe, st.session_state.growth = 15, 10
        st.session_state.preset = "הוגן"

with col3:
    if st.button("🔴 סריקה מחמירה (איכות מקסימלית)"):
        st.session_state.min_roe, st.session_state.min_upside, st.session_state.max_debt = 20, 25, 80
        st.session_state.target_pe, st.session_state.growth = 12, 8
        st.session_state.preset = "מחמיר"

st.divider()

# סרגל צד - מקבל ערכים מהכפתורים או ידנית
st.sidebar.header(f"⚙️ הגדרות (מצב: {st.session_state.get('preset', 'הוגן')})")

min_roe = st.sidebar.slider("מינימום ROE (%)", 0, 50, st.session_state.get('min_roe', 12), format="%d%%")
max_debt = st.sidebar.slider("מקסימום חוב/הון", 0, 200, st.session_state.get('max_debt', 120))
min_upside = st.sidebar.slider("מינימום Upside (%)", -20, 100, st.session_state.get('min_upside', 10), format="%d%%")
target_pe = st.sidebar.number_input("מכפיל יעד (P/E)", 5, 50, st.session_state.get('target_pe', 15))
growth = st.sidebar.slider("צמיחה שנתית חזויה", 1, 50, st.session_state.get('growth', 10), format="%d%%") / 100
use_ma200 = st.sidebar.checkbox("סינון מגמת ירידה (MA200)", value=False)
limit = st.sidebar.number_input("כמות מניות לסריקה", 10, 100, 40)

params = {
    'min_roe': min_roe, 'max_debt': max_debt, 'min_upside': min_upside,
    'target_pe': target_pe, 'growth': growth, 'use_ma200': use_ma200
}

# --- 5. הרצה והצגת תוצאות ---
if st.button("🚀 הרץ סריקה על השוק"):
    all_tickers = get_all_tickers()
    selected = all_tickers[:int(limit)]
    all_scanned_results = []
    
    progress = st.progress(0)
    status_text = st.empty()
    
    for i, t in enumerate(selected):
        status_text.text(f"מנתח את {t}...")
        res = analyze_stock(t, params)
        if res: all_scanned_results.append(res)
        progress.progress((i + 1) / len(selected))
    
    status_text.empty()
    
    if all_scanned_results:
        df_all = pd.DataFrame(all_scanned_results).sort_values(by="Score", ascending=False)
        
        # 1. טבלת הזדמנויות (אלו שעברו את הסינון)
        passed_df = df_all[df_all['Passed'] == True].drop(columns=['Passed'])
        st.subheader(f"✅ הזדמנויות קנייה שנמצאו ({len(passed_df)})")
        if not passed_df.empty:
            st.dataframe(passed_df, use_container_width=True)
        else:
            st.warning("לא נמצאו מניות שעומדות בסינון המחמיר. ראה את הדירוג המלא למטה.")
            
        # 2. טבלת דירוג כללי של כל מה שנסרק
        st.divider()
        st.subheader("📊 דירוג מלא של כל המניות שנסרקו")
        st.write("כאן ניתן לראות את כל המניות וציוני האיכות שלהן, גם אם הן נפסלו בגלל פרמטר אחד.")
        st.dataframe(df_all.drop(columns=['Passed']), use_container_width=True)
    else:
        st.error("לא התקבלו נתונים. וודא חיבור לאינטרנט ונסה שנית.")
