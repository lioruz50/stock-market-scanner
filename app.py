import streamlit as st
import yfinance as yf
import pandas as pd

# --- 1. הגדרות דף ותיקון עברית (RTL) ---
st.set_page_config(page_title="Alpha Market Hunter - Buffett Edition", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    html, body, [data-testid="stSidebar"], .main {
        direction: rtl;
        text-align: right;
        font-family: 'Assistant', sans-serif;
    }
    div[data-testid="stTooltipContent"] { direction: rtl; text-align: right; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. משיכת רשימת מניות ---
@st.cache_data(ttl=86400)
def get_all_tickers():
    return ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "AVGO", "COST", "NFLX",
            "ADBE", "CRM", "AMD", "QCOM", "TXN", "INTC", "MU", "AMAT", "LRCX", "TSM",
            "V", "MA", "JPM", "BAC", "WMT", "DIS", "NKE", "ORCL", "UNH", "PFE", "KO", "PEP"]

# --- 3. פונקציית הניתוח של באפט ---
def analyze_buffett_style(ticker, p):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        price = info.get('currentPrice', 0)
        roe = info.get('returnOnEquity', 0)
        net_margin = info.get('profitMargins', 0)
        debt_to_equity = info.get('debtToEquity', 999)
        free_cash_flow = info.get('freeCashflow', 0)
        eps = info.get('trailingEps', 1)
        
        if price == 0: return None

        # חישוב Upside (המרחק מהשווי ההוגן)
        future_eps = eps * ((1 + p['growth']) ** 5)
        fair_value = (future_eps * p['target_pe']) / 1.6 
        upside = ((fair_value / price) - 1) * 100
        
        # --- תנאי הברזל של באפט ---
        # 1. חפיר כלכלי: שולי רווח מעל 15% ו-ROE מעל 15%
        has_moat = net_margin > 0.15 and roe > 0.15
        # 2. שמרנות פיננסית: חוב נמוך מההון העצמי (מתחת ל-100)
        low_debt = debt_to_equity < 100
        # 3. ייצור מזומנים: תזרים מזומנים חופשי חיובי
        cash_king = free_cash_flow > 0
        
        # שקלול ציון (Score)
        score = round((roe * 40) + (net_margin * 20) + (upside * 0.4), 1)
        
        # בדיקה אם המניה עוברת את "פקד באפט"
        is_buffett_approved = has_moat and low_debt and cash_king and upside > 5
        
        # סינון לפי בחירת המשתמש
        passed = True
        if p['buffett_mode'] and not is_buffett_approved:
            passed = False
        elif not p['buffett_mode']:
            if roe < (p['min_roe']/100) or upside < p['min_upside']:
                passed = False

        return {
            "Ticker": ticker,
            "Name": info.get('shortName', ticker),
            "Price": f"${price:.2f}",
            "ROE": f"{roe*100:.1f}%",
            "Margin": f"{net_margin*100:.1f}%",
            "Debt/Equity": f"{debt_to_equity:.1f}",
            "Upside": f"{upside:.1f}%",
            "Score": score,
            "Passed": passed,
            "Buffett": "💎 אישור באפט" if is_buffett_approved else "❌ לא עובר"
        }
    except: return None

# --- 4. ממשק משתמש ---
st.title("🛡️ Alpha Market Hunter - Buffett Edition")

# --- פקד וורן באפט ---
st.sidebar.header("🎯 אסטרטגיה")
buffett_mode = st.sidebar.toggle("💎 הפעל סינון וורן באפט", value=True, 
    help="סינון קשוח לפי: חפיר חזק (ROE ורווחיות > 15%), חוב נמוך ותזרים מזומנים חיובי.")

st.sidebar.divider()

# פקדי שליטה ידניים (פעילים כשהמצב אינו "באפט")
min_roe = st.sidebar.slider("מינימום ROE (%)", 0, 50, 15, format="%d%%")
min_upside = st.sidebar.slider("מינימום Upside (%)", -20, 100, 10, format="%d%%")
target_pe = st.sidebar.number_input("מכפיל יעד", 5, 50, 15)
growth = st.sidebar.slider("צמיחה חזויה", 1, 50, 10, format="%d%%") / 100
limit = st.sidebar.number_input("כמות מניות לסריקה", 10, 100, 40)

params = {
    'buffett_mode': buffett_mode, 'min_roe': min_roe, 
    'min_upside': min_upside, 'target_pe': target_pe, 
    'growth': growth
}

if st.button("🚀 הרץ סריקת ערך"):
    all_res = []
    prog = st.progress(0)
    tickers = get_all_tickers()[:int(limit)]
    
    for i, t in enumerate(tickers):
        res = analyze_buffett_style(t, params)
        if res: all_res.append(res)
        prog.progress((i + 1) / len(tickers))
    
    if all_res:
        df = pd.DataFrame(all_res).sort_values(by="Score", ascending=False)
        
        st.subheader("✅ מניות שעברו את הסינון")
        st.dataframe(df[df['Passed'] == True].drop(columns=['Passed']), use_container_width=True)
        
        st.divider()
        st.subheader("📊 דירוג מלא ואישור באפט")
        st.dataframe(df.drop(columns=['Passed']), use_container_width=True)

        st.success("""
        ### 📖 המתכון של באפט בקוד:
        * **חפיר (Moat):** המניה חייבת להציג ROE ושולי רווח מעל 15%.
        * **שמרנות פיננסית:** חוב נמוך (מתחת ל-100) כדי לשרוד תקופות קשות.
        * **מזומן הוא המלך:** תזרים מזומנים חופשי חיובי (Free Cash Flow).
        * **מחיר בטוח:** פוטנציאל רווח (Upside) חיובי ביחס לשווי ההוגן.
        """)
