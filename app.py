import streamlit as st
import google.generativeai as genai
import replicate
import os
import json
import time  # 导入时间库用于防限流

# --- 页面配置 ---
st.set_page_config(page_title="AI 电商轮播图生成器", page_icon="🛍️", layout="wide")

# --- 侧边栏：配置 API ---
with st.sidebar:
    st.header("🔑 API 配置")
    gemini_key = st.text_input("Gemini API Key (必填)", type="password")
    replicate_api_token = st.text_input("Replicate API Token (选填)", type="password")
    st.markdown("---")
    st.info("💡 如果图片报错 429，说明请求太快。本版本已加入自动延迟。")

# --- 核心逻辑函数 ---

def get_gemini_prompts(user_copy, api_key):
    genai.configure(api_key=api_key)
    # 自动尝试最新模型名
    model = genai.GenerativeModel('gemini-1.5-flash-8b')
    
    prompt = f"""
    你是一位专业的电商视觉总监。请根据以下产品文案，设计 3 张不同维度的轮播图视觉方案。
    产品文案：{user_copy}
    请严格按照以下 JSON 格式输出，不要包含 Markdown 标记：
    [
        {{
            "title": "场景图",
            "description": "构图描述",
            "image_prompt": "High quality commercial photography, [英文绘图指令], 8k, professional lighting"
        }},
        {{ "title": "细节图", "description": "...", "image_prompt": "..." }},
        {{ "title": "品牌/模特图", "description": "...", "image_prompt": "..." }}
    ]
    """
    try:
        response = model.generate_content(prompt)
        cleaned_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(cleaned_text)
    except Exception as e:
        st.error(f"Gemini 报错: {e}")
        return []

def generate_image_replicate(prompt, api_token):
    os.environ["REPLICATE_API_TOKEN"] = api_token
    try:
        # 使用快速且便宜的 flux-schnell
        output = replicate.run(
            "black-forest-labs/flux-schnell",
            input={"prompt": prompt, "aspect_ratio": "1:1", "output_format": "jpg"}
        )
        return output[0]
    except Exception as e:
        st.error(f"绘图报错: {e}")
        return None

# --- 主界面 ---
st.title("🛍️ AI 电商轮播图生成器")
user_copy = st.text_area("输入产品文案", placeholder="例如：极简智能手表...")
generate_btn = st.button("🚀 开始生成方案并绘图", type="primary")

# --- 核心修改部分：替换原来的 if generate_btn ---
if generate_btn:
    if not gemini_key:
        st.warning("请填写 Gemini API Key")
    else:
        with st.status("🤖 正在设计视觉方案...", expanded=True):
            plans = get_gemini_prompts(user_copy, gemini_key)
        
        if plans:
            st.subheader("生成结果")
            for index, plan in enumerate(plans):
                # 创建一个容器
                with st.container(border=True):
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        st.markdown(f"### 第 {index+1} 张：{plan['title']}")
                        st.write(plan['description'])
                    
                    with col2:
                        if replicate_api_token:
                            # 💡 关键改动：如果是第2、3张，先强制等待，避开限制
                            if index > 0:
                                st.caption("⏱️ 正在排队避开限流，请稍候...")
                                time.sleep(5) # 免费版建议等待 5 秒更稳
                            
                            with st.spinner("正在生成图片..."):
                                img_url = generate_image_replicate(plan['image_prompt'], replicate_api_token)
                                if img_url:
                                    st.image(img_url)
                        else:
                            st.warning("未配置 Replicate Token，仅显示方案。")
