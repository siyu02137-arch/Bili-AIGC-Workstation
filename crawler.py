import sys, os, time, asyncio, random, traceback
import pandas as pd
from bilibili_api import user, video, sync

# 强制 UTF-8，防止 windows 乱码
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

def print_err(msg):
    print(f"{msg}", file=sys.stderr)

async def run_crawler(uid: int):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    save_dir = os.path.join(base_dir, "data")
    
    print(f"🔄 [系统] 初始化爬虫, UID: {uid}")
    
    # 获取用户信息
    try:
        u = user.User(uid=uid)
        info = await u.get_user_info()
        name = info.get('name', str(uid))
        print(f"✅ [连接成功] UP主: {name}")
    except Exception as e:
        print_err(f"❌ [连接失败] API 异常: {str(e)}")
        sys.exit(1)

    # 获取列表
    print("📥 [系统] 拉取视频列表...")
    try:
        time.sleep(random.uniform(0.5, 1.5))
        res = await u.get_videos(pn=1, ps=30)
        v_list = res.get('list', {}).get('vlist', [])
        
        if not v_list:
            print_err("⚠️ [警告] 列表为空")
            sys.exit(1)
    except Exception as e:
        print_err(f"❌ [获取列表失败] {str(e)}")
        traceback.print_exc() 
        sys.exit(1)

    # 遍历解析
    print(f"🔍 [系统] 发现 {len(v_list)} 个视频，开始解析...")
    data = []

    for i, v in enumerate(v_list):
        try:
            bvid = v['bvid']
            title = v['title']
            
            v_obj = video.Video(bvid=bvid)
            info = await v_obj.get_info()
            stat = info['stat']
            
            data.append({
                'title': title,
                'view': stat.get('view', 0),
                'coin': stat.get('coin', 0),
                'like': stat.get('like', 0),
                'comment': stat.get('reply', 0),
                'danmaku': stat.get('danmaku', 0),
                'favorite': stat.get('favorite', 0),
                'share': stat.get('share', 0),
                'duration': info.get('duration', 0),
                'pubdate': pd.to_datetime(info['pubdate'], unit='s'),
                'bvid': bvid
            })
            
            print(f"   [{i+1}/{len(v_list)}] ✔️ {title[:15]}...")
            time.sleep(random.uniform(1.0, 2.0))
            
        except Exception as e:
            print(f"   [{i+1}] ⚠️ 跳过: {e}")

    # 保存
    if data:
        if not os.path.exists(save_dir): os.makedirs(save_dir)
        file_path = os.path.join(save_dir, f"{name}_videos.csv")
        try:
            df = pd.DataFrame(data)
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            print("="*30)
            print(f"🎉 完成！共 {len(df)} 条。\n📂 路径: {file_path}")
            print("="*30)
        except Exception as e:
            print_err(f"❌ 保存失败: {e}")
            sys.exit(1)
    else:
        print_err("❌ 无有效数据")
        sys.exit(1)

if __name__ == "__main__":
    target_uid = 946974
    if len(sys.argv) > 1:
        try: target_uid = int(sys.argv[1])
        except: pass
    
    try:
        sync(run_crawler(target_uid))
    except Exception as e:
        print_err(f"❌ 程序崩溃: {e}")
        traceback.print_exc()
        sys.exit(1)