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

# --- ⚙️ 設定區 ---
LEMON_SQUEEZY_LINK = "https://petos.lemonsqueezy.com/checkout/buy/da91c266-7236-4a64-aea8-79cdce90706d" 
ACCESS_CODE = "VIP2025"
FREE_LIMIT = 3

# --- 1. 網頁基礎設定 ---
st.set_page_config(
    page_title="PetOS",
    page_icon="🐾",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- CSS 美化 ---
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stButton button { width: 100%; background-color: #FF4B4B; color: white; font-weight: bold; border-radius: 12px; border: none; padding: 0.5rem 1rem; }
        .stButton button:hover { background-color: #FF2B2B; color: white; }
        .usage-counter { text-align: center; font-size: 0.9rem; color: #666; background-color: #f0f2f6; padding: 5px; border-radius: 5px; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 初始化 API & 資料庫 ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
    
    supabase = create_client(supabase_url, supabase_key)
    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"系統設定錯誤: {e}")
    st.stop()

# --- [解決問題 1] 智慧模型防當機 ---
def generate_content_safe(prompt, image):
    # 優先順序：你的帳號有的 2.5 -> 通用 1.5 -> 保底 Pro
    model_list = [
        'gemini-2.5-flash',       
        'gemini-1.5-flash',
        'gemini-1.5-flash-001',
        'gemini-1.5-flash-002',
        'gemini-1.5-pro'          
    ]
    
    last_error = None
    
    for model_name in model_list:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content([prompt, image])
            return response
        except Exception as e:
            print(f"嘗試模型 {model_name} 失敗，切換下一個...")
            last_error = e
            continue
            
    raise last_error

# --- [解決問題 2] Cookie 認人機制 (只用一個 Manager) ---
cookie_manager = stx.CookieManager(key="petos_auth_manager")

# 關鍵：稍微等待讓 Cookie 載入
time.sleep(0.1)
cookies = cookie_manager.get_all()

# A. 取得或生成 User ID
cookie_user_id = cookies.get("petos_user_id")

if not cookie_user_id:
    # 這是新用戶 (或清除了快取)
    new_id = str(uuid.uuid4())
    # 設定 Cookie (長效)
    cookie_manager.set("petos_user_id", new_id, expires_at=datetime.datetime(year=2035, month=1, day=1))
    # 強制等待寫入
    time.sleep(0.5)
    # [關鍵] 重新整理頁面，確保下次讀取到的是剛剛寫入的 ID，而不是又生成新的
    st.rerun()
else:
    # 這是老用戶，直接用
    user_id = cookie_user_id

# B. 取得 VIP 狀態
is_premium = cookies.get("petos_is_premium") == "true"

# --- VIP 側邊欄 ---
with st.sidebar:
    st.header("💎 Premium Access")
    code_input = st.text_input("Enter Access Code", type="password")
    if code_input == ACCESS_CODE:
        cookie_manager.set("petos_is_premium", "true", expires_at=datetime.datetime(year=2035, month=1, day=1))
        st.success("Verified! Refreshing...")
        time.sleep(1)
        st.rerun()

# --- 4. 查詢使用次數 (去資料庫查這個 ID 用了幾次) ---
def get_usage_count(uid):
    try:
        response = supabase.table("logs").select("id", count="exact").eq("user_id", uid).execute()
        return response.count
    except:
        return 0

current_usage = get_usage_count(user_id)
remaining_usage = FREE_LIMIT - current_usage

# --- 5. 主介面 ---
st.markdown("<h1 style='text-align: center;'>🐾 PetOS</h1>", unsafe_allow_html=True)

target_language = st.selectbox(
    "🌍 Choose Language / 選擇語言",
    ["English", "Traditional Chinese (繁體中文)", "Thai (ภาษาไทย)"]
)

uploaded_file = st.file_uploader("", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, use_column_width=True)

    # --- 收費牆判斷 ---
    if not is_premium:
        if remaining_usage > 0:
            st.markdown(f'<div class="usage-counter">⚡ Free tries left: {remaining_usage} / {FREE_LIMIT}</div>', unsafe_allow_html=True)
        else:
            st.error("🚫 Free limit reached! (免費次數已用完)")
            st.markdown(f"""
                <div style="text-align: center; padding: 20px; border: 2px dashed #FF4B4B; border-radius: 10px; margin-top: 10px;">
                    <h3>💎 Upgrade to PetOS Pro</h3>
                    <p>Unlock unlimited photos & premium styles.</p>
                    <a href="{LEMON_SQUEEZY_LINK}" target="_blank">
                        <button style="background-color: #FF4B4B; color: white; border: none; padding: 10px 20px; border-radius: 5px; font-weight: bold; cursor: pointer; font-size: 1rem;">
                            👉 Get Unlimited Access ($9.99)
                        </button>
                    </a>
                    <p style="font-size: 0.8rem; margin-top: 10px; color: #666;">
                        Already paid? Enter code in sidebar ↖️
                    </p>
                </div>
            """, unsafe_allow_html=True)
            st.stop() # 停止執行

    # --- 核心運作區 ---
    if target_language == "English":
        btn_text = "🔮 Read My Pet's Mind!"
        loading = "Connecting to Pet Planet..."
    elif target_language == "Thai (ภาษาไทย)":
        btn_text = "🔮 เริ่มอ่านใจน้อง"
        loading = "AI กำลังเชื่อมต่อ..."
    else:
        btn_text = "🔮 開始讀心"
        loading = "AI 正在連線到寵物星球..."

    if st.button(btn_text):
        try:
            if target_language == "English":
                prompt = "Analyze this photo. Write ONE short, funny, sassy internal monologue. Strict Rules: Max 15 words. No intro. Use Gen Z slang. DO NOT use emojis."
            elif target_language == "Thai (ภาษาไทย)":
                prompt = "Act as a humorous Thai pet psychic. Write ONE short OS in Thai. Strict Rules: Max 20 words. Use Thai teen slang. No intro. DO NOT use emojis."
            else:
                prompt = "請看這張照片。寫一句這隻寵物現在心裡的 OS。嚴格規則：繁體中文，台灣鄉民梗，有點賤賤的。20字以內。不要前言。絕對不要用表情符號。"

            with st.spinner(loading):
                # 1. 呼叫智慧模型
                response = generate_content_safe(prompt, image)
                os_text = response.text
                
                # 2. 合成圖片
                final_image = create_polaroid(image, os_text, target_language)
                
                img_byte_arr = io.BytesIO()
                final_image.save(img_byte_arr, format='JPEG', quality=80)
                img_bytes = img_byte_arr.getvalue()
                
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                file_name = f"{user_id}_{timestamp}.jpg"
                
                # 3. 存到 Supabase
                try:
                    supabase.storage.from_("photos").upload(path=file_name, file=img_bytes, file_options={"content-type": "image/jpeg"})
                    public_url = supabase.storage.from_("photos").get_public_url(file_name)
                except:
                    public_url = "upload_failed"

                try:
                    data = {
                        "user_id": user_id,
                        "image_url": public_url,
                        "ai_text": os_text,
                        "session_id": user_id
                    }
                    supabase.table("logs").insert(data).execute()
                except Exception as e:
                    print(f"DB Error: {e}")

                # 4. 顯示結果
                st.success("Analysis Complete!")
                st.image(final_image, caption="Generated by PetOS", use_column_width=True)
                
                st.download_button(
                    label="📥 Download Image",
                    data=img_bytes,
                    file_name="petos_polaroid.jpg",
                    mime="image/jpeg",
                    use_container_width=True
                )
                
                # [注意] 不要在這裡寫 st.rerun()，會導致圖片消失
                # 我們依靠使用者下次上傳照片時，自動檢查更新後的次數

        except Exception as e:
            st.error(f"系統暫時繁忙，請稍後再試。Error: {e}")

else:
    st.info("👆 Upload a photo to start!")