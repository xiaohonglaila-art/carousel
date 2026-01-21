import streamlit as st
import google.generativeai as genai
import replicate
import os
import json

# --- 页面配置 ---
st.set_page_config(page_title="AI 电商轮播图生成器", page_icon="🛍️", layout="wide")

# --- 侧边栏：配置 API ---
with st.sidebar:
    st.header("🔑 API 配置")
    st.markdown("请先输入你的 API Key 才能开始使用：")
    
    gemini_key = st.text_input("Gemini API Key (必填)", type="password", help="用于理解文案")
    replicate_api_token = st.text_input("Replicate API Token (选填)", type="password", help="用于生成图片 (推荐 Flux 模型)")
    
    st.markdown("---")
    st.markdown("""
    **如何获取 Key?**
    1. [获取 Gemini Key (Google)](https://aistudio.google.com/app/apikey)
    2. [获取 Replicate Token](https://replicate.com/account/api-tokens)
    """)

# --- 核心逻辑函数 ---

def get_gemini_prompts(user_copy, api_key):
    """调用 Gemini 将文案转化为视觉提示词"""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    你是一位专业的电商视觉总监。请根据以下产品文案，设计 3 张不同维度的轮播图视觉方案。
    
    产品文案：
    {user_copy}
    
    请严格按照以下 JSON 格式输出，不要包含 Markdown 标记或多余文字：
    [
        {{
            "title": "场景图",
            "description": "中文的构图描述，用于展示给用户看",
            "image_prompt": "High quality commercial photography, [这里填入基于文案生成的英文详细绘画指令], 8k resolution, highly detailed, photorealistic, professional lighting, no text in background"
        }},
        {{
            "title": "细节图",
            "description": "...",
            "image_prompt": "..."
        }},
        {{
            "title": "模特/使用图",
            "description": "...",
            "image_prompt": "..."
        }}
    ]
    """
    
    try:
        response = model.generate_content(prompt)
        # 清理可能存在的 markdown 符号
        cleaned_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(cleaned_text)
    except Exception as e:
        st.error(f"Gemini 生成出错: {e}")
        return []

def generate_image_replicate(prompt, api_token):
    """调用 Replicate (Flux 模型) 生成图片"""
    os.environ["REPLICATE_API_TOKEN"] = api_token
    try:
        # 使用 Flux-schnell 模型，速度快且便宜
        output = replicate.run(
            "black-forest-labs/flux-schnell",
            input={
                "prompt": prompt,
                "aspect_ratio": "1:1", # 电商通常 1:1 或 3:4
                "output_format": "jpg",
                "output_quality": 80
            }
        )
        # Replicate 返回的是一个列表，取第一张图
        return output[0]
    except Exception as e:
        st.error(f"图片生成出错: {e}")
        return None

# --- 主界面 UI ---

st.title("🛍️ AI 电商轮播图生成器")
st.markdown("输入你的产品文案，AI 自动为你拆解视觉卖点并生成高清大图。")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("1. 输入文案")
    user_copy = st.text_area("产品文案 / 卖点", height=200, placeholder="例如：新款夏季防晒霜，SPF50+，清爽不油腻，含有玻尿酸成分，买一送一。")
    
    generate_btn = st.button("🚀 开始生成", type="primary", use_container_width=True)

if generate_btn:
    if not gemini_key:
        st.warning("请先在左侧填入 Gemini API Key！")
    elif not user_copy:
        st.warning("请输入文案！")
    else:
        # 1. Gemini 生成方案
        with st.status("🤖 Gemini 正在思考视觉方案...", expanded=True) as status:
            plans = get_gemini_prompts(user_copy, gemini_key)
            status.update(label="✅ 视觉方案设计完成！", state="complete", expanded=False)

        # 2. 展示结果
        st.divider()
        st.subheader("2. 生成结果")

        if plans:
            # 遍历生成的 3 个方案
            for plan in plans:
                with st.container():
                    c1, c2 = st.columns([1, 2])
                    
                    with c1:
                        st.info(f"**{plan['title']}**")
                        st.caption(plan['description'])
                        st.text_area("英文 Prompt (可复制)", plan['image_prompt'], height=100)
                    
                    with c2:
                        if replicate_api_token:
                            with st.spinner(f"正在绘制 {plan['title']}..."):
                                image_url = generate_image_replicate(plan['image_prompt'], replicate_api_token)
                                if image_url:
                                    st.image(image_url, use_column_width=True)
                                    st.success("生成成功")
                        else:
                            st.warning("未配置 Replicate Key，跳过绘图步骤。配置后即可自动出图。")
                    
                    st.markdown("---")
