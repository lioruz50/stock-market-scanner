import streamlit as st
import yfinance as yf
import pandas as pd

# --- 1. הגדרות דף ותיקון עברית ---
st.set_page_config(page_title="Alpha Market Hunter PRO", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    html, body, [data-testid="stSidebar"], .main {
        direction: rtl; text-align: right; font-family: 'Assistant', sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. משיכת רשימת S&P 500 המלאה ---
@st.cache_data(ttl=86400)
def get_sp500_tickers():
    # משיכת הרשימה המעודכנת ביותר של ה-S&P 500
    table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
    df = table[0]
    return df['Symbol'].tolist()

# --- 3. פונקציית ניתוח (וולידציה מול נתונים עדכניים) ---
def analyze_stock(ticker, p):
    try:
        stock = yf.Ticker(ticker)
        # שימוש ב-fast_info וב-info לקבלת הנתונים המעודכנים ביותר
        info = stock.info
        
        price = info.get('currentPrice', 0)
        if price == 0: return None

        # ולידציה של מדדי האיכות מהדוח האחרון
        roe = info.get('returnOnEquity', 0)
        net_margin = info.get('profitMargins', 0)
        debt_to_equity = info.get('debtToEquity', 0)
        eps = info.get('trailingEps', 1)
        
        # חישוב שווי הוגן לפי מודל באפט (צמיחה עתידית)
        future_eps = eps * ((1 + p['growth']) ** 5)
        fair_value = (future_eps * p['target_pe']) / 1.6 
        upside = ((fair_value / price) - 1) * 100
        
        # תנאי סינון (לפי ההגדרות הנוחות שביקשת)
        passed = True
        if roe < (p['min_roe']/100) or upside < p['min_upside'] or net_margin < 0.08:
            passed = False
        
        # ציון שקלול (Score)
        score = round((roe * 50) + (upside * 0.5), 1)
        
        return {
            "Ticker": ticker,
            "Name": info.get('shortName', ticker),
            "Price": f"${price:.2f}",
            "ROE": f"{roe*100:.1f}%",
            "Margin": f"{net_margin*100:.1f}%",
            "Debt/Eq": f"{debt_to_equity:.1f}",
            "Upside": f"{upside:.1f}%",
            "Score": score,
            "Passed": passed
        }
    except: return None

# --- 4. ממשק משתמש ---
st.title("🛡️ Alpha Market Hunter - S&P 500 Scanner")

st.sidebar.header("⚙️ פילטרים והסברים")
min_roe = st.sidebar.slider("מינימום ROE (%)", 0, 50, 12, format="%d%%", help="יעילות הניהול בייצור רווח מההון")
min_upside = st.sidebar.slider("מינימום Upside (%)", -20, 100, 0, format="%d%%", help="פוטנציאל הרווח ביחס למחיר היום")
target_pe = st.sidebar.number_input("מכפיל יעד (P/E)", 5, 50, 18, help="המכפיל הצפוי בעוד 5 שנים")
growth = st.sidebar.slider("צמיחה חזויה שנתית", 1, 50, 10, format="%d%%") / 100

# כמות מניות לסריקה (מתוך ה-500)
limit = st.sidebar.number_input("כמות מניות לסריקה מה-S&P", 10, 500, 50)

if st.button("🚀 התחל סריקה מקיפה"):
    all_tickers = get_sp500_tickers()
    selected = all_tickers[:int(limit)]
    results = []
    
    progress = st.progress(0)
    status_text = st.empty()
    
    for i, t in enumerate(selected):
        status_text.text(f"מנתח את {t}...")
        res = analyze_stock(t, {'min_roe': min_roe, 'min_upside': min_upside, 'target_pe': target_pe, 'growth': growth})
        if res: results.append(res)
        progress.progress((i + 1) / len(selected))
    
    status_text.empty()
    
    if results:
        df = pd.DataFrame(results).sort_values(by="Score", ascending=False)
        
        # טבלת הזדמנויות
        passed_df = df[df['Passed'] == True].drop(columns=['Passed'])
        st.subheader(f"✅ מניות שעברו את הסינון ({len(passed_df)})")
        st.dataframe(passed_df, use_container_width=True)
        
        # דירוג מלא
        st.divider()
        st.subheader("📊 דירוג מלא של המניות שנסרקו")
        st.dataframe(df.drop(columns=['Passed']), use_container_width=True)
