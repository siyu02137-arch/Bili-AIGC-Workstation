import os, sys, subprocess, datetime
import streamlit as st
import pandas as pd
from data_tool import DataTool
from engine_ai import AIEngine

# 配置
st.set_page_config(page_title="Bilibili AIGC 工作台", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
DATA_DIR = os.path.join(BASE_DIR, "data")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

@st.cache_resource
def load_core():
    try:
        return DataTool(), AIEngine()
    except Exception as e:
        st.error(f"组件初始化失败: {e}")
        return None, None

tool, ai = load_core()

def save_artifact(content: str, prefix: str = "Script") -> str:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.txt"
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath

def page_crawler():
    st.header("🕷️ 数据采集")
    st.markdown("---")
    st.info("输入 UID 抓取数据")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        uid = st.text_input("B站 UID", value="946974")
    with col2:
        st.write("") 
        st.write("") 
        btn = st.button("🚀 开始采集", type="primary", use_container_width=True)

    if btn and uid:
        with st.status("正在启动爬虫...", expanded=True) as status:
            script_path = os.path.join(os.path.dirname(__file__), "crawler.py")
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            
            try:
                status.write("⚡ 连接 API...")
                process = subprocess.run(
                    [sys.executable, script_path, uid],
                    capture_output=True, text=True, encoding='utf-8', errors='replace', env=env
                )
                if process.returncode == 0:
                    status.update(label="✅ 采集成功", state="complete", expanded=False)
                    st.success("数据已保存")
                    # 日志回显
                    log_lines = process.stdout.strip().split('\n')
                    if log_lines:
                        st.code('\n'.join(log_lines[-5:]), language='bash')
                else:
                    status.update(label="❌ 采集失败", state="error")
                    err_msg = process.stderr if process.stderr else process.stdout
                    st.code(err_msg)
            except Exception as e:
                status.update(label="❌ 异常", state="error")
                st.error(str(e))

def page_analysis():
    st.header("📊 市场洞察")
    st.markdown("---")
    
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    if not files:
        st.warning("暂无数据")
        return

    c1, c2 = st.columns(2)
    with c1: base = st.selectbox("我的账号", files)
    with c2: comps = st.multiselect("对标竞品", files)

    if base and comps:
        df_base = tool.load_and_standardize(base)
        if df_base is None:
            st.error("读取失败")
            return
        
        df_base['Type'] = 'Mine'
        all_dfs = [df_base]
        
        for c in comps:
            tmp = tool.load_and_standardize(c)
            if tmp is not None:
                tmp['Type'] = 'Competitor'
                all_dfs.append(tmp)
        
        full_df = pd.concat(all_dfs, ignore_index=True)

        st.subheader("1. 竞争格局")
        y_col = 'coin' if full_df['coin'].sum() > 0 else 'comment'
        st.scatter_chart(full_df, x='view', y=y_col, color='Type', size='view', height=450)

        st.subheader("2. 选题挖掘")
        raw_comps = [d for d in [tool.load_and_standardize(f) for f in comps] if d is not None]
        
        with st.spinner("分析标题..."):
            gaps = tool.find_topic_gaps(df_base, raw_comps)
            keywords = [w[0] for w in gaps] if gaps else ["Python", "DeepSeek", "搞钱", "黑科技"]
            st.success(f"🔥 推荐: {' | '.join(keywords[:6])}")
            
            t1, t2 = st.tabs(["🖐️ 手动", "🧠 AI自动"])
            
            with t1:
                selected = st.multiselect("关键词", keywords)
                if st.button("生成剧本 (手动)"):
                    if selected:
                        prompt = f"我是UP主，请用关键词【{'+'.join(selected)}】写一个B站爆款视频脚本，开头要吸引人，中间干货密集。"
                        res = ai.generate_text(prompt)
                        st.session_state['script'] = res
                        save_artifact(res, "Script_Manual")
                        st.success("剧本已生成")
            
            with t2:
                if st.button("AI 构思"):
                    prompt = f"基于关键词 {','.join(keywords[:5])}，构思3个不同风格（硬核/趣味/商业）的视频选题。"
                    st.session_state['ideas'] = ai.generate_text(prompt)
                
                if 'ideas' in st.session_state:
                    st.info(st.session_state['ideas'])
                    idea = st.text_input("输入思路")
                    if st.button("生成剧本 (AI思路)"):
                        if idea:
                            res = ai.generate_text(f"基于此思路写脚本：{idea}")
                            st.session_state['script'] = res
                            save_artifact(res, "Script_AI")
                            st.success("剧本已生成")

def page_production():
    st.header("🚀 生产车间")
    st.markdown("---")
    col_text, col_img = st.columns([1, 1], gap="large")
    
    with col_text:
        st.subheader("📝 脚本")
        val = st.session_state.get('script', '')
        edited = st.text_area("编辑器", value=val, height=600, label_visibility="collapsed")
        if edited != val: st.session_state['script'] = edited
        
        if st.button("💾 保存"):
            if edited:
                save_artifact(edited, "Script_Edited")
                st.toast("已保存")

    with col_img:
        st.subheader("🎨 封面 (Flux)")
        if st.button("✨ 提取 Prompt"):
            if st.session_state.get('script'):
                with st.spinner("提取中..."):
                    st.session_state['v_prompt'] = ai.generate_visual_prompt(st.session_state['script'])
            else:
                st.error("缺脚本")

        vp = st.text_area("提示词", value=st.session_state.get('v_prompt', ''), height=150)
        
        if st.button("🎨 绘制", type="primary", use_container_width=True):
            if vp:
                with st.status("Flux 渲染中...", expanded=True) as s:
                    s.write("优化提示词...")
                    final = ai.optimize_prompt(vp) if any("\u4e00" <= c <= "\u9fff" for c in vp) else vp
                    s.write("GPU 计算中...")
                    path = ai.generate_image(final, OUTPUT_DIR)
                    if path:
                        st.session_state['img'] = path
                        s.update(label="完成", state="complete", expanded=False)
                    else:
                        s.update(label="失败", state="error")
        
        if st.session_state.get('img'):
            st.image(st.session_state['img'], caption="Result", use_container_width=True)
            st.success("图片已保存")

def page_assets():
    st.header("🗄️ 资产")
    st.markdown("---")
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    if not files:
        st.info("无数据")
        return
        
    sel = st.selectbox("文件", files)
    if sel:
        df = tool.load_and_standardize(sel)
        if df is not None:
            c1, c2, c3 = st.columns(3)
            c1.metric("视频数", len(df))
            c2.metric("平均播放", f"{int(df['view'].mean()):,}")
            rate = (df['coin'].sum() / df['view'].sum() * 100) if df['view'].sum() > 0 else 0
            c3.metric("币粉率", f"{rate:.2f}%")
            st.dataframe(df, use_container_width=True)
        else:
            st.error("读取失败")

def main():
    with st.sidebar:
        st.title("AIGC 工作台")
        nav = st.radio("导航", ["数据采集", "市场洞察", "生产车间", "资产数据"])
        st.divider()
        st.caption(f"Output: {OUTPUT_DIR}")

    if nav == "数据采集": page_crawler()
    elif nav == "市场洞察": page_analysis()
    elif nav == "生产车间": page_production()
    elif nav == "资产数据": page_assets()

if __name__ == "__main__":
    main()