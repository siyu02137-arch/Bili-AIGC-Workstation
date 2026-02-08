import os, re, sqlite3
import pandas as pd
from collections import Counter
from typing import List, Tuple

class DataTool:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(self.base_dir, 'data')
        self.db_path = os.path.join(self.data_dir, 'app_database.db')
        
        self.stop_words = {
            '视频', '一个', '如何', '真的', '没有', '这个', '什么', '我们', '你们', '他们',
            '就是', '因为', '所以', '但是', '如果', '可能', '觉得', '其实', '然后', '虽然',
            '万粉丝', '千万粉丝', '极客湾', '影视飓风'
        }

    def load_and_standardize(self, filename: str) -> pd.DataFrame:
        filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(filepath): return None
            
        try:
            try:
                df = pd.read_csv(filepath, encoding='utf-8-sig')
            except UnicodeDecodeError:
                df = pd.read_csv(filepath, encoding='gbk')
        except: return None

        df.columns = [str(c).strip() for c in df.columns]

        # 统一中英文列名
        col_map = {
            '播放量': 'view', 'view': 'view',
            '硬币': 'coin', 'coin': 'coin',
            '点赞': 'like', 'like': 'like',
            '评论数': 'comment', 'comment': 'comment',
            '标题': 'title', 'title': 'title',
            '弹幕': 'danmaku', 'danmaku': 'danmaku',
            '时长': 'duration', 'duration': 'duration',
            '发布时间': 'pubdate', 'pubdate': 'pubdate',
            'BVID': 'bvid', 'bvid': 'bvid'
        }
        
        df = df.rename(columns=col_map)
        
        required_cols = ['view', 'coin', 'like', 'comment', 'title']
        for col in required_cols:
            if col not in df.columns: df[col] = 0

        for col in ['view', 'coin', 'like', 'comment']:
            df[col] = df[col].apply(self._clean_number)
            
        return df

    def _clean_number(self, val):
        try:
            s = str(val).strip()
            if '万' in s:
                return float(re.findall(r'\d+\.?\d*', s)[0]) * 10000
            res = re.sub(r'[^\d.]', '', s)
            return float(res) if res else 0.0
        except:
            return 0.0

    def find_topic_gaps(self, my_df: pd.DataFrame, comp_dfs: List[pd.DataFrame]) -> List[Tuple[str, int]]:
        if not comp_dfs: return []
        
        all_titles = " ".join(pd.concat(comp_dfs)['title'].astype(str))
        # 提取中英文数字，长度2-20
        raw_keywords = re.findall(r'[a-zA-Z0-9\u4e00-\u9fa5]{2,20}', all_titles)
        
        clean_words = []
        for w in raw_keywords:
            if (w not in self.stop_words 
                and not w.isdigit()
                and len(w) > 1 
                and not w.endswith(('的', '了', '吗', '呢', '呀', '吧'))
                and not w.startswith(('在', '和', '与', '给', '被'))):
                clean_words.append(w)
        
        return Counter(clean_words).most_common(20)