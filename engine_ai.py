import requests, time, os, random, re

DIRECTOR_PROMPT = """
你是一位 B站/YouTube 顶级封面设计师。任务是【提炼视觉爆点】。
1. 寻找钩子：剧本里最反直觉、最硬核的概念。
2. 视觉隐喻：将抽象概念具象化（如：代码流从键盘炸裂）。
3. 电影级质感：Cinematic lighting, 8k resolution, photorealistic.
【禁令】❌ 严禁生成任何文字。❌ 严禁出现模糊主体。
【输出】直接输出英文 Prompt，逗号分隔。
"""

class AIEngine:
    def __init__(self, model="qwen2.5:7b"):
        self.ollama_url = "http://localhost:11434/api/generate"
        self.comfy_url = "http://127.0.0.1:8188"
        self.model = model

    def _clean(self, text):
        return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

    def generate_text(self, prompt, system_prompt=None):
        full = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        payload = {
            "model": self.model,
            "prompt": full,
            "stream": False,
            "options": {
                "num_ctx": 4096, "temperature": 0.8, "repeat_penalty": 1.3, 
                "stop": ["<|endoftext|>", "<|im_end|>", "Thank you"]
            }
        }
        try:
            res = requests.post(self.ollama_url, json=payload, timeout=600)
            if res.status_code == 200:
                return self._clean(res.json().get('response', ""))
            return f"Error: {res.status_code}"
        except Exception as e: return str(e)

    def generate_visual_prompt(self, script):
        prompt = f"任务：为以下剧本设计一张B站封面底图（只要英文Prompt，不要文字）。\n剧本：{script[:1500]}"
        return self.generate_text(prompt, system_prompt=DIRECTOR_PROMPT)

    def optimize_prompt(self, text):
        return self.generate_text(f"Translate to high-quality Flux prompt: {text}", system_prompt=DIRECTOR_PROMPT)

    def get_all_models(self):
        try:
            r = requests.get(f"{self.comfy_url}/object_info/CheckpointLoaderSimple", timeout=2)
            if r.status_code == 200:
                return r.json()['CheckpointLoaderSimple']['input']['required']['ckpt_name'][0]
        except: pass
        return []

    def _find_file(self, folder, extension, keywords):
        """辅助函数：在指定文件夹找符合关键词的文件"""
        # ComfyUI 的根目录通常在上一级或同级，这里假设在项目同级的 ComfyUI 文件夹
        # 你可以根据实际路径调整此处的 search_path
        search_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ComfyUI", "models", folder)
        if not os.path.exists(search_path):
            return None
        for f in os.listdir(search_path):
            if f.endswith(extension) and any(k.lower() in f.lower() for k in keywords):
                return f
        return None

    def generate_image(self, prompt, save_dir):
        # 1. 自动搜索模型零件
        unet = self._find_file("unet", ".gguf", ["flux", "q4"])
        clip_t5 = self._find_file("clip", ".safetensors", ["t5xxl"])
        clip_l = self._find_file("clip", ".safetensors", ["clip_l"])
        vae = self._find_file("vae", ".safetensors", ["ae", "flux"])

        # 检查零件是否齐全，不全就报错
        if not all([unet, clip_t5, clip_l, vae]):
            error_msg = f"❌ 缺少模型文件！请检查：Unet({unet}), T5({clip_t5}), CLIP_L({clip_l}), VAE({vae})"
            print(error_msg)
            return None

        seed = random.randint(1, 10**14)
        print(f"🚀 自动加载成功！正在生成封面...")
        print(f"📦 Unet: {unet} | Seed: {seed}")

        # 2. 动态构建蓝图
        workflow = {
            "10": {"inputs": {"unet_name": unet}, "class_type": "UnetLoaderGGUF"},
            "11": {
                "inputs": {"clip_name1": clip_t5, "clip_name2": clip_l, "type": "flux"},
                "class_type": "DualCLIPLoader"
            },
            "12": {"inputs": {"vae_name": vae}, "class_type": "VAELoader"},
            "3": {
                "inputs": {
                    "seed": seed, "steps": 25, "cfg": 1.0, # 步数已设为 25 以保证画质
                    "sampler_name": "euler", "scheduler": "simple", "denoise": 1, 
                    "model": ["10", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]
                },
                "class_type": "KSampler"
            },
            "5": {"inputs": {"width": 1280, "height": 720, "batch_size": 1}, "class_type": "EmptyLatentImage"},
            "6": {"inputs": {"text": prompt, "clip": ["11", 0]}, "class_type": "CLIPTextEncode"},
            "7": {"inputs": {"text": "blurry, low quality", "clip": ["11", 0]}, "class_type": "CLIPTextEncode"},
            "8": {"inputs": {"samples": ["3", 0], "vae": ["12", 0]}, "class_type": "VAEDecode"},
            "9": {"inputs": {"filename_prefix": "Bili_Cover", "images": ["8", 0]}, "class_type": "SaveImage"}
        }

        # 3. 发送请求给 ComfyUI
        try:
            r = requests.post(f"{self.comfy_url}/prompt", json={"prompt": workflow}, timeout=10)
            if r.status_code != 200: return None
            pid = r.json()['prompt_id']
            
            start = time.time()
            while time.time() - start < 600: # 增加到 10 分钟超时，防止 4060 渲染大图慢
                time.sleep(2)
                try:
                    h = requests.get(f"{self.comfy_url}/history/{pid}").json()
                    if pid in h:
                        fname = h[pid]['outputs']['9']['images'][0]['filename']
                        res = requests.get(f"{self.comfy_url}/view", params={"filename": fname, "type": "output"})
                        path = os.path.join(save_dir, fname)
                        with open(path, 'wb') as f: f.write(res.content)
                        return path
                except: continue
        except Exception as e:
            print(f"连接失败: {e}")
        return None