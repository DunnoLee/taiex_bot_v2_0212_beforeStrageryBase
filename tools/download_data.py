import sys
import os
import csv
import pandas as pd  # <--- 記得要 import pandas
from datetime import datetime, timedelta
import shioaji as sj
from shioaji import constant

# 載入設定
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.settings import Settings

def download_kbars():
    print("📡 連線到 Shioaji API...")
    api = sj.Shioaji(simulation=False) 
    api.login(
        api_key=Settings.SHIOAJI_API_KEY,
        secret_key=Settings.SHIOAJI_SECRET_KEY
    )

    contract_code = Settings.TARGET_CONTRACT 
    contract = api.Contracts.Futures.TMF[contract_code]
    
    if not contract:
        print(f"❌ 找不到合約: {contract_code}")
        return

    print(f"📥 開始下載 {contract_code} 的 1分K 資料...")
    
    # 抓取最近 30 天
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    
    kbars = api.kbars(
        contract, 
        start=start_date, 
        end=datetime.now().strftime("%Y-%m-%d"),
    )
    
    # --- 🔴 修正重點開始 🔴 ---
    # 舊寫法: df = kbars.df (已失效)
    
    # 新寫法: 手動轉成 DataFrame
    df = pd.DataFrame({
        "ts": kbars.ts,
        "Open": kbars.Open,
        "High": kbars.High,
        "Low": kbars.Low,
        "Close": kbars.Close,
        "Volume": kbars.Volume
    })
    
    # 把 ts (timestamp) 轉成可讀的時間格式
    df['ts'] = pd.to_datetime(df['ts'])
    df.set_index('ts', inplace=True)
    df.index.name = 'Time'
    # --- 🔴 修正重點結束 🔴 ---
    
    # 存檔
    os.makedirs("data/history", exist_ok=True)
    file_path = f"data/history/{contract_code}_1min_history.csv"
    
    df.to_csv(file_path)
    
    print(f"✅ 下載完成！已儲存至: {file_path}")
    print(f"📊 共 {len(df)} 筆資料")
    
    # 登出 (好習慣)
    api.logout()

if __name__ == "__main__":
    download_kbars()