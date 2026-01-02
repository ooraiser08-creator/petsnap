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

# ==========================================
# 1. 系統配置與常數 (Configuration)
# ==========================================
st.set_page_config(
    page_title="PetOS",
    page_icon="🐾",
    layout="centered",
    initial_sidebar_state="collapsed"
)

LEMON_SQUEEZY_LINK = "https://petos.lemonsqueezy.com/checkout/buy/da91c266-7236-4a64-aea8-79cdce90706d" 
ACCESS_CODE = "VIP2025"
FREE_LIMIT = 3

# CSS 美化
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stButton button { width: 100%; background-color: #FF4B4B; color: white; font-weight: bold; border-radius: 12px; padding: 0.5rem 1rem; border: none; }
        .stButton button:hover { background-color: #FF2B2B; color: white; }
        .usage-counter { text-align: center; font-size: 0.9rem; color: #666; background-color: #f0f2f6; padding: 5px; border-radius: 5px; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 初始化服務 (Services Initialization)
# ==========================================
@st.cache_resource
def init_services():
    try:
        # Supabase
        supa = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
        # Google AI
        genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
        return supa
    except Exception as e:
        st.error(f"系統連線失敗: {e}")
        st.stop()

supabase = init_services()

# 智慧模型切換函式
def generate_content_safe(prompt, image):
    model_list = [
        'gemini-1.5-flash',       # 首選
        'gemini-1.5-flash-001',   # 備選
        'gemini-1.5-flash-002',   
        'gemini-2.5-flash',       # 你帳號有的
        'gemini-1.5-pro'          # 保底
    ]
    
    for model_name in model_list:
        try:
            model = genai.GenerativeModel(model_name)
            return model.generate_content([prompt, image])
        except:
            continue # 失敗就默默試下一個
            
    raise Exception("所有模型皆忙碌中，請稍後再試。")

# ==========================================
# 3. 用戶身分驗證 (Authentication Logic)
# ==========================================
# 這裡使用單一 CookieManager，並加上 key 防止重複
cookie_manager = stx.CookieManager(key="petos_auth")

# 讀取所有 Cookie
cookies = cookie_manager.get_all()

# 等待 Cookie 載入 (解決重新整理歸零的關鍵)
if not cookies:
    time.sleep(0.1)
    cookies = cookie_manager.get_all()

# --- 邏輯 A: 取得 User ID ---
user_id = cookies.get("petos_user_id")

if not user_id:
    # 這是全新用戶，生成新 ID 並寫入
    new_id = str(uuid.uuid4())
    cookie_manager.set("petos_user_id", new_id, expires_at=datetime.datetime(year=2035, month=1, day=1))
    # 強制暫停一下，確保寫入完成
    time.sleep(0.5)
    # 設定 Session 避免立刻重整導致迴圈
    st.session_state['user_id'] = new_id
else:
    # 老用戶
    st.session_state['user_id'] = user_id

# 確保 user_id 變數可用
current_user_id = st.session_state.get('user_id', user_id)

# --- 邏輯 B: 取得 VIP 狀態 ---
is_premium = cookies.get("petos_is_premium") == "true"

# ==========================================
# 4. 側邊欄與次數查詢 (Sidebar & Quota)
# ==========================================
with st.sidebar:
    st.header("💎 Premium Access")
    code_input = st.text_input("Enter Access Code", type="password")
    if code_input:
        if code_input == ACCESS_CODE:
            cookie_manager.set("petos_is_premium", "true", expires_at=datetime.datetime(year=2035, month=1, day=1))
            st.success("Verified! Please refresh.")
            time.sleep(1)
        else:
            st.error("Invalid Code")

# 查詢使用次數
def get_usage_count(uid):
    try:
        # 如果是新用戶(uid為None)直接回傳0
        if not uid: return 0
        response = supabase.table("logs").select("id", count="exact").eq("user_id", uid).execute()
        return response.count
    except:
        return 0

usage_count = get_usage_count(current_user_id)
remaining = FREE_LIMIT - usage_count

# ==========================================
# 5. 主畫面 UI (Main Interface)
# ==========================================
st.markdown("<h1 style='text-align: center;'>🐾 PetOS</h1>", unsafe_allow_html=True)

target_language = st.selectbox(
    "🌍 Choose Language / 選擇語言",
    ["English", "Traditional Chinese (繁體中文)", "Thai (ภาษาไทย)"]
)

uploaded_file = st.file_uploader("", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, use_column_width=True)

    # --- 收費牆攔截 ---
    if not is_premium:
        if remaining > 0:
            st.markdown(f'<div class="usage-counter">⚡ Free tries left: {remaining} / {FREE_LIMIT}</div>', unsafe_allow_html=True)
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
                </div>
            """, unsafe_allow_html=True)
            st.stop() # 這裡直接停止，不渲染按鈕

    # --- 生成按鈕 ---
    if target_language == "English":
        btn_text = "🔮 Read My Pet's Mind!"
    elif target_language == "Thai (ภาษาไทย)":
        btn_text = "🔮 เริ่มอ่านใจน้อง"
    else:
        btn_text = "🔮 開始讀心"

    if st.button(btn_text):
        try:
            with st.spinner("AI Thinking..."):
                # 1. 準備 Prompt
                if target_language == "English":
                    prompt = "Analyze this photo. Write ONE short, funny, sassy internal monologue. Strict Rules: Max 15 words. No intro. Use Gen Z slang. DO NOT use emojis."
                elif target_language == "Thai (ภาษาไทย)":
                    prompt = "Act as a humorous Thai pet psychic. Write ONE short OS in Thai. Strict Rules: Max 20 words. Use Thai teen slang. No intro. DO NOT use emojis."
                else:
                    prompt = "請看這張照片。寫一句這隻寵物現在心裡的 OS。嚴格規則：繁體中文，台灣鄉民梗，有點賤賤的。20字以內。不要前言。絕對不要用表情符號。"

                # 2. 呼叫 AI (自動切換模型)
                ai_response = generate_content_safe(prompt, image)
                os_text = ai_response.text

                # 3. 合成圖片
                final_image = create_polaroid(image, os_text, target_language)
                
                # 4. 轉換格式
                img_byte_arr = io.BytesIO()
                final_image.save(img_byte_arr, format='JPEG', quality=80)
                img_bytes = img_byte_arr.getvalue()
                
                # 5. 上傳雲端 & 寫入資料庫
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                file_name = f"{current_user_id}_{timestamp}.jpg"
                
                try:
                    supabase.storage.from_("photos").upload(path=file_name, file=img_bytes, file_options={"content-type": "image/jpeg"})
                    public_url = supabase.storage.from_("photos").get_public_url(file_name)
                except:
                    public_url = "upload_failed"

                supabase.table("logs").insert({
                    "user_id": current_user_id,
                    "image_url": public_url,
                    "ai_text": os_text,
                    "session_id": current_user_id
                }).execute()

                # 6. 成功顯示
                st.success("Success!")
                st.image(final_image, caption="Generated by PetOS", use_column_width=True)
                st.download_button(label="📥 Download Image", data=img_bytes, file_name="petos_polaroid.jpg", mime="image/jpeg", use_container_width=True)

        except Exception as e:
            st.error(f"Error: {e}")

else:
    st.info("👆 Upload a photo to start!")