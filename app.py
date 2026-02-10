import streamlit as st
import yfinance as yf
import pandas as pd

# --- 1. הגדרות דף ותיקון עברית (RTL) ---
st.set_page_config(page_title="Alpha Market Hunter - Buffett Validator", layout="wide")

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

# --- 3. פונקציית הניתוח המורחבת ---
def analyze_buffett_v2(ticker, p):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # ולידציה בסיסית של מחיר
        price = info.get('currentPrice')
        if not price or price <= 0: return None

        roe = info.get('returnOnEquity', 0)
        net_margin = info.get('profitMargins', 0)
        debt_to_equity = info.get('debtToEquity', 999)
        fcf = info.get('freeCashflow', 0)
        eps = info.get('trailingEps', 1)
        
        # חישוב Upside
        future_eps = eps * ((1 + p['growth']) ** 5)
        fair_value = (future_eps * p['target_pe']) / 1.6 
        upside = ((fair_value / price) - 1) * 100
        
        # --- קריטריונים של באפט (מעודכן) ---
        reasons = []
        if roe < 0.15: reasons.append(f"ROE נמוך ({roe*100:.1f}%)")
        if net_margin < 0.08: reasons.append(f"רווח נקי נמוך ({net_margin*100:.1f}%)")
        if debt_to_equity > 100: reasons.append(f"חוב גבוה ({debt_to_equity:.1f})")
        if fcf <= 0: reasons.append("אין תזרים חופשי")
        if upside < 5: reasons.append(f"יקר מדי ({upside:.1f}% Upside)")

        is_approved = len(reasons) == 0
        failure_reason = " | ".join(reasons) if not is_approved else "✅ עומד בכל התנאים"

        # ציון שקלול
        score = round((roe * 40) + (net_margin * 20) + (upside * 0.4), 1)

        return {
            "Ticker": ticker,
            "Name": info.get('shortName', ticker),
            "Price": f"${price:.2f}",
            "ROE": f"{roe*100:.1f}%",
            "Margin": f"{net_margin*100:.1f}%",
            "Debt/Eq": f"{debt_to_equity:.1f}",
            "Upside": f"{upside:.1f}%",
            "Score": score,
            "Passed": is_approved,
            "Buffett Status": "💎 מאושר" if is_approved else "❌ נפסל",
            "Reason": failure_reason
        }
    except Exception as e:
        return None

# --- 4. ממשק משתמש ---
st.title("🛡️ Alpha Market Hunter - Buffett Edition")

st.sidebar.header("🎯 הגדרות וורן באפט")
buffett_only = st.sidebar.toggle("💎 הצג רק מניות מאושרות", value=False)
growth = st.sidebar.slider("צמיחה חזויה שנתית", 1, 50, 10, format="%d%%") / 100
target_pe = st.sidebar.number_input("מכפיל יעד", 5, 50, 15)
limit = st.sidebar.number_input("כמות מניות לסריקה", 10, 100, 40)

if st.button("🚀 הרץ סריקה עם ולידציה"):
    results = []
    progress = st.progress(0)
    tickers = get_all_tickers()[:int(limit)]
    
    for i, t in enumerate(tickers):
        res = analyze_buffett_v2(t, {'growth': growth, 'target_pe': target_pe})
        if res: results.append(res)
        progress.progress((i + 1) / len(tickers))
    
    if results:
        df = pd.DataFrame(results).sort_values(by="Score", ascending=False)
        
        # טבלת מניות מאושרות
        passed_df = df[df['Passed'] == True].drop(columns=['Passed', 'Reason'])
        st.subheader(f"✅ מניות שעברו את 'מבחן באפט' ({len(passed_df)})")
        if not passed_df.empty:
            st.dataframe(passed_df, use_container_width=True)
        else:
            st.warning("אף מניה לא עברה את הסינון הקשוח של באפט. ראה פירוט בטבלה למטה.")

        # טבלת פירוט ולידציה מלאה
        st.divider()
        st.subheader("🔍 דוח ולידציה: למה הן נפסלו?")
        st.write("בטבלה זו תוכל לראות את כל המניות שנסרקו ואת הסיבה המדויקת לפסילתן לפי הקריטריונים.")
        st.dataframe(df.drop(columns=['Passed']), use_container_width=True)

        st.info("""
        ### 🧪 ולידציה של הנתונים:
        * **אמזון (AMZN):** אם היא נפסלת, זה כנראה בגלל שולי רווח או מחיר יקר ביחס לצמיחה.
        * **ROE:** אם הנתון הוא 0, סימן ש-Yahoo Finance לא סיפק נתון עדכני והמניה נפסלת אוטומטית ליתר ביטחון.
        """)
