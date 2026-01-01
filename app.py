import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import uuid
import datetime
from supabase import create_client

# 匯入繪圖工具
from image_maker import create_polaroid

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
        .stButton button {
            width: 100%;
            background-color: #FF4B4B;
            color: white;
            font-weight: bold;
            border-radius: 12px;
            padding: 0.5rem 1rem;
            border: none;
        }
        .stButton button:hover {
            background-color: #FF2B2B;
            color: white;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. 初始化設定 (API & 資料庫) ---
try:
    # 取得 Google API Key
    api_key = st.secrets["GOOGLE_API_KEY"]
    
    # 取得 Supabase 設定
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
    
    # 建立 Supabase 連線
    supabase = create_client(supabase_url, supabase_key)
    
except:
    st.error("系統設定有誤，請檢查 Secrets")
    st.stop()

# --- 3. 用戶追蹤 (Session ID) ---
if 'user_id' not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

user_id = st.session_state.user_id

# --- 4. 主介面 ---
st.markdown("<h1 style='text-align: center;'>🐾 PetOS</h1>", unsafe_allow_html=True)

target_language = st.selectbox(
    "🌍 Choose Language / 選擇語言",
    ["English", "Traditional Chinese (繁體中文)", "Thai (ภาษาไทย)"]
)

uploaded_file = st.file_uploader("", type=["jpg", "jpeg", "png"])

# --- 5. 核心運作區 ---
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, use_column_width=True)

    # 按鈕文字
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
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')

            # --- Prompt (全面禁止 Emoji) ---
            if target_language == "English":
                prompt = """
                Analyze this photo. Write ONE short, funny, sassy internal monologue. 
                
                STRICT RULES: 
                1. Max 15 words. 
                2. No intro. 
                3. Use Gen Z slang.
                4. DO NOT use emojis. (No smiley faces, no symbols)
                """
            elif target_language == "Thai (ภาษาไทย)":
                prompt = """
                Act as a humorous Thai pet psychic. Write ONE short OS in Thai. 
                
                STRICT RULES: 
                1. Max 20 words. 
                2. Use Thai teen slang. 
                3. No intro.
                4. DO NOT use emojis. (ห้ามใช้อิโมจิเด็ดขาด)
                """
            else:
                prompt = """
                請看這張照片。寫一句這隻寵物現在心裡的 OS。
                
                嚴格規則：
                1. 繁體中文，台灣鄉民梗，有點賤賤的。
                2. 不超過 20 個字。
                3. 不要前言。
                4. 【絕對不要】使用任何 Emoji 或表情符號 (例如 🤣, 🔥, 👀)。
                """

            with st.spinner(loading):
                # A. AI 生成文字
                response = model.generate_content([prompt, image])
                os_text = response.text
                
                # B. 圖片合成
                final_image = create_polaroid(image, os_text, target_language)
                
                # C. 上傳與存檔
                # 1. 轉成 bytes
                img_byte_arr = io.BytesIO()
                final_image.save(img_byte_arr, format='JPEG', quality=80)
                img_bytes = img_byte_arr.getvalue()
                
                # 2. 檔名
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                file_name = f"{user_id}_{timestamp}.jpg"
                
                # 3. 上傳到 Supabase Storage
                try:
                    supabase.storage.from_("photos").upload(
                        path=file_name,
                        file=img_bytes,
                        file_options={"content-type": "image/jpeg"}
                    )
                    # 取得公開連結
                    public_url = supabase.storage.from_("photos").get_public_url(file_name)
                except Exception as e:
                    print(f"Upload Error: {e}")
                    public_url = "upload_failed"

                # 4. 寫入資料庫
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

                # --- 顯示結果 ---
                st.success("Analysis Complete!")
                st.image(final_image, caption="Generated by PetOS", use_column_width=True)
                
                st.download_button(
                    label="📥 Download Image (下載美圖)",
                    data=img_bytes,
                    file_name="petos_polaroid.jpg",
                    mime="image/jpeg",
                    use_container_width=True
                )

        except Exception as e:
            st.error(f"Error: {e}")

else:
    st.info("👆 Upload a photo to start!")