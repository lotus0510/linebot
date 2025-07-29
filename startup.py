#!/usr/bin/env python3
"""
Cloud Run 啟動腳本
確保所有服務正確初始化
"""
import os
import sys
import time
import threading
from app import app, start_background_thread

def check_environment():
    """檢查必要的環境變數"""
    required_vars = [
        "LINE_CHANNEL_ACCESS_TOKEN",
        "LINE_CHANNEL_SECRET", 
        "gemini_api",
        "notion_api",
        "notion_id"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ 缺少必要的環境變數: {missing_vars}")
        return False
    
    print("✅ 所有必要的環境變數已設置")
    return True

def test_services():
    """測試外部服務連接"""
    try:
        # 測試 Notion 連接
        from server import NotionSDK
        test_notion_sdk = NotionSDK()
        print("✅ Notion 服務連接正常")
    except Exception as e:
        print(f"⚠️ Notion 服務連接失敗: {e}")
    
    try:
        # 測試 Gemini 連接
        from server import gemini
        test_response = gemini("測試連接")
        print("✅ Gemini 服務連接正常")
    except Exception as e:
        print(f"⚠️ Gemini 服務連接失敗: {e}")

def main():
    """主啟動函數"""
    print("🚀 啟動 LINE Bot 服務...")
    
    # 檢查環境
    if not check_environment():
        sys.exit(1)
    
    # 測試服務
    test_services()
    
    # 確保後台線程已啟動
    print("🔄 確保後台處理線程運行中...")
    
    # 獲取端口
    port = int(os.environ.get('PORT', 8080))
    print(f"📡 服務將在端口 {port} 上運行")
    
    # 啟動應用
    print("✅ 服務啟動完成")
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == "__main__":
    main()