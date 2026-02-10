import streamlit as st
import yfinance as yf
import pandas as pd
import time

# --- 1. הגדרות דף ותיקון עברית ---
st.set_page_config(page_title="Alpha Hunter - Global Scanner", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@400;700&display=swap');
    html, body, [data-testid="stSidebar"], .main {
        direction: rtl; text-align: right; font-family: 'Assistant', sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. משיכת רשימת הטיקרים המלאה (S&P 500 + NASDAQ) ---
@st.cache_data(ttl=86400)
def get_global_tickers():
    try:
        # משיכת S&P 500 מוויקיפדיה
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
        # משיכת NASDAQ 100 לגיבוי מהיר
        nasdaq100 = pd.read_html('https://en.wikipedia.org/wiki/Nasdaq-100')[4]['Ticker'].tolist()
        # איחוד והסרת כפילויות
        full_list = list(set(sp500 + nasdaq100))
        return sorted([t.replace('.', '-') for t in full_list])
    except:
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "NFLX", "AVGO", "COST"]

# --- 3. פונקציית הניתוח המדויקת ---
def analyze_stock(ticker, p):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        price = info.get('currentPrice', 0)
        if price == 0: return None

        roe = info.get('returnOnEquity', 0)
        net_margin = info.get('profitMargins', 0)
        eps = info.get('trailingEps', 1)
        
        # מודל השווי ההוגן
        future_eps = eps * ((1 + p['growth']) ** 5)
        fair_value = (future_eps * p['target_pe']) / 1.6 
        upside = ((fair_value / price) - 1) * 100
        
        passed = (roe >= (p['min_roe']/100)) and (upside >= p['min_upside']) and (net_margin >= 0.08)
        
        return {
            "Ticker": ticker,
            "Name": info.get('shortName', ticker),
            "Price": f"${price:.2f}",
            "ROE": f"{roe*100:.1f}%",
            "Margin": f"{net_margin*100:.1f}%",
            "Upside": f"{upside:.1f}%",
            "Score": round((roe * 50) + (upside * 0.5), 1),
            "Passed": passed
        }
    except: return None

# --- 4. ממשק משתמש ---
st.title("🌍 סורק שוק גלובלי - הכל מהכל")
st.write("מערכת זו סורקת כעת את מניות ה-S&P 500 וה-NASDAQ 100 המשולבות.")

st.sidebar.header("⚙️ פילטרים")
min_roe = st.sidebar.slider("מינימום ROE (%)", 0, 50, 12)
min_upside = st.sidebar.slider("מינימום Upside (%)", -20, 100, 0)
target_pe = st.sidebar.number_input("מכפיל יעד", 5, 50, 20)
growth = st.sidebar.slider("צמיחה חזויה", 1, 50, 10) / 100

# שליטה על כמות המניות (כדי שלא יחסמו אותך)
limit = st.sidebar.select_slider("כמות מניות לסריקה", options=[50, 100, 250, 500, "הכל"], value=100)

if st.button("🚀 הרץ סריקה מסיבית"):
    full_list = get_global_tickers()
    
    if limit == "הכל":
        selected = full_list
    else:
        selected = full_list[:int(limit)]
        
    results = []
    progress = st.progress(0)
    status = st.empty()
    
    start_time = time.time()
    
    for i, t in enumerate(selected):
        status.text(f"בודק את {t} ({i+1}/{len(selected)})...")
        res = analyze_stock(t, {'min_roe': min_roe, 'min_upside': min_upside, 'target_pe': target_pe, 'growth': growth})
        if res: results.append(res)
        progress.progress((i + 1) / len(selected))
        
        # הפסקה קצרה כל 50 מניות כדי לא להיחסם
        if i % 50 == 0 and i > 0:
            time.sleep(1)
            
    end_time = time.time()
    status.success(f"הסריקה הושלמה! זמן כולל: {int(end_time - start_time)} שניות")
    
    if results:
        df = pd.DataFrame(results).sort_values(by="Score", ascending=False)
        
        passed_df = df[df['Passed'] == True].drop(columns=['Passed'])
        st.subheader(f"✅ הזדמנויות קנייה שנמצאו ({len(passed_df)})")
        st.dataframe(passed_df, use_container_width=True)
        
        st.divider()
        st.subheader("📊 דירוג השוק המלא")
        st.dataframe(df.drop(columns=['Passed']), use_container_width=True)

        # הסבר השקלול בסוף כפי שביקשת
        st.info("""
        ### 🧠 איך שוקללו התוצאות?
        הציון (**Score**) מבוסס על שקלול של 50% איכות ניהולית (ROE) ו-50% פוטנציאל רווח (Upside).
        * **מעל 30:** חברה מעולה במחיר זול.
        * **15-30:** חברה יציבה במחיר הוגן.
        * **מתחת ל-15:** מניה יקרה מדי או חברה פחות רווחית.
        """)
