# utils/file_utils.py

import pandas as pd
import os

def load_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        print(f"[file_utils.py] ❌ 파일 없음: {path}")
        return pd.DataFrame()
    df = pd.read_csv(path)
    print(f"[file_utils.py] ✅ 파일 로드 완료: {path}, {len(df)} rows")
    return df

def save_csv(df: pd.DataFrame, path: str):
    df.to_csv(path, index=False)
    print(f"[file_utils.py] 💾 파일 저장 완료: {path}, {len(df)} rows")
