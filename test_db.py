import streamlit as st
from supabase import create_client, Client

# 1. 嘗試從金庫拿鑰匙
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    
    st.write(f"🔑 找到 URL: `{url[:20]}...`")
    st.write(f"🔑 找到 KEY: `{key[:10]}...`")

    # 2. 嘗試建立連線
    supabase: Client = create_client(url, key)
    
    # 3. 顯示成功訊息
    st.success("✅ Supabase 連線成功！雲端帳房已就緒！")

except Exception as e:
    st.error(f"❌ 連線失敗: {e}")
    st.warning("請檢查 .streamlit/secrets.toml 裡面的內容是否正確")