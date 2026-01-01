from PIL import Image, ImageDraw, ImageFont, ImageOps
import textwrap

def create_polaroid(user_image, text, language="English"):
    """
    製作 IG 黃金比例 (4:5) 的拍立得美圖
    """
    
    # --- 1. 定義畫布 (IG 最佳尺寸 1080x1350) ---
    CANVAS_WIDTH = 1080
    CANVAS_HEIGHT = 1350
    
    # 定義邊框與留白
    SIDE_PADDING = 60      # 左右留白
    TOP_PADDING = 60       # 上方留白
    BOTTOM_AREA = 380      # 下方寫字區高度 (留白多一點才有文青感)
    
    # 計算照片應該要多大
    target_img_width = CANVAS_WIDTH - (SIDE_PADDING * 2)
    target_img_height = CANVAS_HEIGHT - TOP_PADDING - BOTTOM_AREA
    
    # --- 2. 智慧裁切 (Smart Crop) ---
    # 使用 ImageOps.fit 自動把照片「填滿」框框並置中裁切
    # 這樣不管用戶傳橫的直的，都不會變形，而且版面最整齊
    resized_img = ImageOps.fit(
        user_image, 
        (target_img_width, target_img_height),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.5) # (0.5, 0.5) 代表裁切正中間
    )
    
    # --- 3. 建立畫布 ---
    canvas = Image.new('RGB', (CANVAS_WIDTH, CANVAS_HEIGHT), '#FDFDFD') # 用微微的米白色，不要死白
    
    # 貼上照片
    canvas.paste(resized_img, (SIDE_PADDING, TOP_PADDING))
    
    # --- 4. 準備寫字 ---
    draw = ImageDraw.Draw(canvas)
    
    # 載入字型 (根據語言微調大小)
    if "Thai" in language:
        font_path = "assets/font_th.ttf"
        font_size = 65 
        line_spacing = 30
        wrap_width = 30
    else:
        font_path = "assets/font_tc.ttf" # 中文/英文
        font_size = 58
        line_spacing = 25
        wrap_width = 22 # 英文/中文一行約 22 字，控制在 2-3 行
        
    try:
        font = ImageFont.truetype(font_path, font_size)
        # 小 Logo 字型
        logo_font = ImageFont.truetype(font_path, 28)
    except:
        font = ImageFont.load_default()
        logo_font = ImageFont.load_default()
        print("⚠️ 找不到字型")

    text_color = "#222222" # 深黑灰，比純黑柔和
    
    # --- 5. 文字排版 (絕對置中) ---
    wrapper = textwrap.TextWrapper(width=wrap_width) 
    word_list = wrapper.wrap(text=text) 
    wrapped_text = '\n'.join(word_list)