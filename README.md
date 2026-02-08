Bili-AIGC-Workstation
面向 B 站 UP 主的工业级全自动 AIGC 封面与选题工作站

本项目由四川艺术学院大数据技术专业学生开发。它集成竞品数据分析、LLM 脚本创作与 Flux 图像生成，旨在通过技术手段提升内容创作效率。

项目亮点 (Key Features)
市场洞察 (Market Insight)：自动采集 B 站 UID 对应的数据，通过散点图动态展示竞争格局，精准锁定高播放选题。

AI 创意引擎 (AI Creative Engine)：基于 Ollama (Qwen2.5-7B) 实现脚本自动生成与视觉提示词提炼。

端侧渲染优化 (On-Device Rendering)：针对主流 RTX 4060 (8GB) 硬件深度优化，采用 Flux.1-dev-GGUF 量化架构，解决 16GB 物理内存下的崩溃问题。

工作流集成 (Workflow Integration)：一键完成从“关键词”到“爆款剧本”再到“电影级封面”的全链路闭环。

硬件环境 (Hardware Environment)
项目针对以下配置进行了极端压力测试并稳定运行：

GPU: NVIDIA GeForce RTX 4060 Laptop (8GB VRAM)。

CPU: AMD Ryzen 7 7435H。

RAM: 16GB (通过虚拟内存与模型量化实现 0 崩溃)。

快速开始 (Quick Start)
1. 环境准备
确保已安装 ComfyUI 并配置好 ComfyUI-GGUF 节点。

2. 模型零件部署
为确保系统正常运行，请将以下文件存入对应路径：

models/unet/: flux1-dev-Q4_K_S.gguf (核心 Unet)

models/clip/: t5xxl_fp8_e4m3fn.safetensors & clip_l.safetensors (文本编码器)

models/vae/: ae.safetensors (VAE)

3. 启动程序
Bash
pip install -r requirements.txt
streamlit run app.py
技术原理 (Technical Architecture)
本系统通过 engine_ai.py 动态重构 ComfyUI 的 API 蓝图，将传统的单体 Checkpoint 加载模式转换为组件化的 Unet Loader (GGUF) 模式，显存占用降低 50% 以上。

开源协议 (License)
本项目采用 MIT License。
