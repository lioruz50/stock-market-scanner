@st.cache_data
def get_market_tickers():
    try:
        # שימוש ב-User-Agent כדי שויקיפדיה לא תחסום אותנו
        import requests
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        html = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}).text
        df = pd.read_html(html, flavor='bs4')[0] # bs4 הוא מנוע יציב יותר
        return df['Symbol'].tolist()
    except Exception as e:
        st.error(f"שגיאה במשיכת רשימת המניות: {e}")
        # רשימת גיבוי אם ויקיפדיה חסומה
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"]
