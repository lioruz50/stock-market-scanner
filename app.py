import streamlit as st
import yfinance as yf
import pandas as pd

# --- 1. הגדרות דף ותיקון עברית ---
st.set_page_config(page_title="Alpha Market Hunter", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    html, body, [data-testid="stSidebar"], .main {
        direction: rtl; text-align: right; font-family: 'Assistant', sans-serif;
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

# --- 3. פונקציית ניתוח ---
def analyze_stock(ticker, p):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get('currentPrice', 0)
        if price == 0: return None

        roe = info.get('returnOnEquity', 0)
        net_margin = info.get('profitMargins', 0)
        debt_to_equity = info.get('debtToEquity', 999)
        eps = info.get('trailingEps', 1)
        
        # חישוב שווי הוגן
        future_eps = eps * ((1 + p['growth']) ** 5)
        fair_value = (future_eps * p['target_pe']) / 1.6 
        upside = ((fair_value / price) - 1) * 100
        
        # בדיקת סיבות פסילה
        reasons = []
        if roe < (p['min_roe']/100): reasons.append(f"ROE נמוך ({roe*100:.1f}%)")
        if net_margin < 0.08: reasons.append(f"רווח נמוך ({net_margin*100:.1f}%)")
        if debt_to_equity > 120: reasons.append(f"חוב גבוה ({debt_to_equity:.1f})")
        if upside < p['min_upside']: reasons.append(f"יקר מדי ({upside:.1f}% Upside)")

        passed = len(reasons) == 0
        
        return {
            "Ticker": ticker,
            "Name": info.get('shortName', ticker),
            "Price": f"${price:.2f}",
            "ROE": f"{roe*100:.1f}%",
            "Margin": f"{net_margin*100:.1f}%",
            "Upside": f"{upside:.1f}%",
            "Score": round((roe * 50) + (upside * 0.5), 1),
            "Passed": passed,
            "Reason": "✅ מאושר" if passed else " | ".join(reasons)
        }
    except: return None

# --- 4. ממשק משתמש ---
st.title("🛡️ Alpha Market Hunter - סורק הזדמנויות")

st.sidebar.header("⚙️ הגדרות סריקה")
min_roe = st.sidebar.slider("מינימום ROE (%)", 0, 50, 12, format="%d%%", help="יעילות הניהול")
min_upside = st.sidebar.slider("מינימום פוטנציאל (Upside)", -20, 100, 0, format="%d%%", help="הנחה ביחס למחיר")
target_pe = st.sidebar.number_input("מכפיל יעד", 5, 50, 20, help="מכפיל עתידי צפוי")
growth = st.sidebar.slider("צמיחה חזויה", 1, 50, 10, format="%d%%") / 100
limit = st.sidebar.number_input("כמות מניות", 10, 100, 40)

if st.button("🚀 הרץ סריקה"):
    results = []
    progress = st.progress(0)
    tickers = get_all_tickers()[:int(limit)]
    
    for i, t in enumerate(tickers):
        res = analyze_stock(t, {'min_roe': min_roe, 'min_upside': min_upside, 'target_pe': target_pe, 'growth': growth})
        if res: results.append(res)
        progress.progress((i + 1) / len(tickers))
    
    if results:
        df = pd.DataFrame(results).sort_values(by="Score", ascending=False)
        
        # הצגת תוצאות שעברו
        passed_df = df[df['Passed'] == True].drop(columns=['Passed', 'Reason'])
        st.subheader(f"✅ מניות שעברו את הסינון ({len(passed_df)})")
        st.dataframe(passed_df, use_container_width=True)
        
        # דירוג מלא עם סיבות
        st.divider()
        st.subheader("📊 דוח מלא וסיבות פסילה")
        st.dataframe(df.drop(columns=['Passed']), use_container_width=True)
