import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import uuid
import datetime
from supabase import create_client
from image_maker import create_polaroid
import extra_streamlit_components as stx
import time

# --- 設定區 ---
LEMON_SQUEEZY_LINK = "https://petos.lemonsqueezy.com/checkout/buy/da91c266-7236-4a64-aea8-79cdce90706d" 
ACCESS_CODE = "VIP2025"
FREE_LIMIT = 3

st.set_page_config(page_title="PetOS", page_icon="🐾", layout="centered", initial_sidebar_state="collapsed")

# --- 初始化 ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(supabase_url, supabase_key)
    genai.configure(api_key=api_key)
except:
    st.error("Secrets 設定錯誤")
    st.stop()

# --- [診斷工具] 查詢可用模型 (放在側邊欄) ---
with st.sidebar:
    st.header("🔧 工程師模式")
    if st.button("🔍 查詢可用模型 (Debug)"):
        try:
            st.write("正在向 Google 查詢...")
            available_models = []
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
            st.success("查詢成功！你的帳號可用模型如下：")
            st.code(available_models)
            st.write("請將上面的列表截圖給工程師。")
        except Exception as e:
            st.error(f"查詢失敗: {e}")

# --- 主程式邏輯 ---
# 為了避免錯誤，我們先用最通用的 flash，等診斷出來再換
def get_gemini_model():
    return genai.GenerativeModel('gemini-1.5-flash')

# Cookie 認人
cookie_manager = stx.CookieManager()
cookies = cookie_manager.get_all()
user_id = cookies.get("petos_user_id")

if not user_id:
    new_id = str(uuid.uuid4())
    cookie_manager.set("petos_user_id", new_id, expires_at=datetime.datetime(year=2030, month=1, day=1))
    user_id = new_id
    time.sleep(0.5)
    st.rerun()

is_premium = cookies.get("petos_is_premium") == "true"

with st.sidebar:
    st.header("💎 Premium Access")
    code_input = st.text_input("Enter Access Code", type="password")
    if code_input == ACCESS_CODE:
        cookie_manager.set("petos_is_premium", "true", expires_at=datetime.datetime(year=2030, month=1, day=1))
        st.success("Verified!")
        time.sleep(1)
        st.rerun()

def get_usage_count(uid):
    try:
        response = supabase.table("logs").select("id", count="exact").eq("user_id", uid).execute()
        return response.count
    except:
        return 0

current_usage = get_usage_count(user_id)
remaining_usage = FREE_LIMIT - current_usage

# UI
st.markdown("<h1 style='text-align: center;'>🐾 PetOS</h1>", unsafe_allow_html=True)
target_language = st.selectbox("🌍 Language", ["English", "Traditional Chinese (繁體中文)", "Thai (ภาษาไทย)"])
uploaded_file = st.file_uploader("", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, use_column_width=True)

    if not is_premium and remaining_usage <= 0:
        st.error("🚫 Free limit reached!")
        st.markdown(f'<a href="{LEMON_SQUEEZY_LINK}" target="_blank">👉 Upgrade Now</a>', unsafe_allow_html=True)
        st.stop()

    if st.button("🔮 Start Analysis"):
        try:
            with st.spinner("AI Thinking..."):
                # 使用上面定義的模型
                model = get_gemini_model()
                
                if target_language == "English":
                    prompt = "Analyze photo. One short funny sassy sentence. No intro. No emojis."
                else:
                    prompt = "看圖寫一句好笑的寵物內心戲。繁體中文。不要表情符號。不要前言。"
                
                response = model.generate_content([prompt, image])
                os_text = response.text
                
                final_image = create_polaroid(image, os_text, target_language)
                
                # 轉 bytes
                img_byte_arr = io.BytesIO()
                final_image.save(img_byte_arr, format='JPEG', quality=80)
                img_bytes = img_byte_arr.getvalue()
                
                # 上傳
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                file_name = f"{user_id}_{timestamp}.jpg"
                try:
                    supabase.storage.from_("photos").upload(file_name, img_bytes, {"content-type": "image/jpeg"})
                    url = supabase.storage.from_("photos").get_public_url(file_name)
                except:
                    url = "failed"
                
                # 紀錄
                supabase.table("logs").insert({
                    "user_id": user_id, "image_url": url, "ai_text": os_text, "session_id": user_id
                }).execute()

                st.success("Done!")
                st.image(final_image, use_column_width=True)
                
        except Exception as e:
            st.error(f"Error: {e}")
            st.info("請使用左上角側邊欄的『查詢可用模型』，並截圖給工程師。")