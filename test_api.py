#!/usr/bin/env python3
"""
API測試腳本 - 用於診斷和測試API端點
"""

import requests
import json
import sys
from typing import Dict, Any

def test_api_endpoint(base_url: str = "http://localhost:8000"):
    """測試API端點"""
    
    print("🧪 開始API測試...")
    print(f"Base URL: {base_url}")
    print("="*60)
    
    # 1. 測試根端點
    print("\n1. 測試根端點 (GET /)")
    try:
        response = requests.get(f"{base_url}/")
        print(f"狀態碼: {response.status_code}")
        if response.status_code == 200:
            print("✅ 成功")
            print(f"回應: {response.json()}")
        else:
            print("❌ 失敗")
            print(f"錯誤: {response.text}")
    except Exception as e:
        print(f"❌ 連接失敗: {e}")
        print("請確保API服務正在運行")
        return False
    
    # 2. 測試健康檢查
    print("\n2. 測試健康檢查 (GET /health)")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"狀態碼: {response.status_code}")
        if response.status_code == 200:
            health_data = response.json()
            print("✅ 成功")
            print(f"系統狀態: {health_data.get('status', 'unknown')}")
            print(f"系統就緒: {health_data.get('system_ready', False)}")
            
            if not health_data.get('system_ready', False):
                print("⚠️  系統未就緒，可能影響其他端點")
        else:
            print("❌ 失敗")
            print(f"錯誤: {response.text}")
    except Exception as e:
        print(f"❌ 請求失敗: {e}")
    
    # 3. 測試搜索端點（不需要API密鑰）
    print("\n3. 測試搜索端點 (POST /search)")
    search_payload = {
        "query": "游泳課程",
        "k": 3
    }
    
    try:
        response = requests.post(
            f"{base_url}/search",
            json=search_payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"狀態碼: {response.status_code}")
        print(f"請求內容: {json.dumps(search_payload, ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            search_data = response.json()
            print("✅ 成功")
            print(f"找到課程數: {search_data.get('total_found', 0)}")
        elif response.status_code == 422:
            print("❌ 422錯誤 - 請求格式問題")
            print(f"詳細錯誤: {response.text}")
            
            # 嘗試解析錯誤詳情
            try:
                error_detail = response.json()
                print("驗證錯誤詳情:")
                for error in error_detail.get('detail', []):
                    print(f"  - 欄位: {error.get('loc', [])}")
                    print(f"    錯誤: {error.get('msg', '')}")
                    print(f"    類型: {error.get('type', '')}")
            except:
                pass
        else:
            print(f"❌ 失敗 - 狀態碼: {response.status_code}")
            print(f"錯誤: {response.text}")
    except Exception as e:
        print(f"❌ 請求失敗: {e}")
    
    # 4. 測試推薦端點（需要API密鑰）
    print("\n4. 測試推薦端點 (POST /recommend)")
    recommend_payload = {
        "query": "我想要減肥燃脂的課程",
        "k": 3
        # 注意：不包含api_key，會測試錯誤處理
    }
    
    try:
        response = requests.post(
            f"{base_url}/recommend",
            json=recommend_payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"狀態碼: {response.status_code}")
        print(f"請求內容: {json.dumps(recommend_payload, ensure_ascii=False, indent=2)}")
        
        if response.status_code == 200:
            print("✅ 成功")
            recommend_data = response.json()
            print(f"推薦成功: {recommend_data.get('success', False)}")
        elif response.status_code == 400:
            print("⚠️  400錯誤 - API密鑰問題（預期行為）")
            print(f"錯誤信息: {response.json().get('error', response.text)}")
        elif response.status_code == 422:
            print("❌ 422錯誤 - 請求格式問題")
            print(f"詳細錯誤: {response.text}")
            
            # 嘗試解析錯誤詳情
            try:
                error_detail = response.json()
                print("驗證錯誤詳情:")
                for error in error_detail.get('detail', []):
                    print(f"  - 欄位: {error.get('loc', [])}")
                    print(f"    錯誤: {error.get('msg', '')}")
                    print(f"    類型: {error.get('type', '')}")
            except:
                pass
        else:
            print(f"❌ 失敗 - 狀態碼: {response.status_code}")
            print(f"錯誤: {response.text}")
    except Exception as e:
        print(f"❌ 請求失敗: {e}")
    
    # 5. 測試類別端點
    print("\n5. 測試類別端點 (GET /categories)")
    try:
        response = requests.get(f"{base_url}/categories")
        print(f"狀態碼: {response.status_code}")
        
        if response.status_code == 200:
            categories_data = response.json()
            print("✅ 成功")
            print(f"類別數量: {categories_data.get('total', 0)}")
            if categories_data.get('categories'):
                print(f"前幾個類別: {categories_data['categories'][:3]}")
        else:
            print(f"❌ 失敗 - 狀態碼: {response.status_code}")
            print(f"錯誤: {response.text}")
    except Exception as e:
        print(f"❌ 請求失敗: {e}")
    
    print("\n" + "="*60)
    print("🧪 API測試完成")
    
    # 提供修復建議
    print("\n💡 如果遇到422錯誤，請檢查：")
    print("1. 請求的JSON格式是否正確")
    print("2. 必填欄位是否都有提供")
    print("3. 欄位類型是否符合要求")
    print("4. 欄位值是否在允許範圍內")
    print("\n📚 查看完整API文檔: http://localhost:8000/docs")

def test_specific_payload():
    """測試特定的請求負載"""
    print("\n🔍 測試特定請求負載...")
    
    # 測試各種可能的請求格式
    test_cases = [
        {
            "name": "最小有效請求",
            "payload": {"query": "游泳"}
        },
        {
            "name": "完整請求",
            "payload": {"query": "游泳課程", "k": 5}
        },
        {
            "name": "包含API密鑰",
            "payload": {"query": "游泳課程", "k": 5, "api_key": "test-key"}
        },
        {
            "name": "空查詢（應該失敗）",
            "payload": {"query": ""}
        },
        {
            "name": "缺少查詢欄位（應該失敗）",
            "payload": {"k": 5}
        }
    ]
    
    for test_case in test_cases:
        print(f"\n測試案例: {test_case['name']}")
        print(f"負載: {json.dumps(test_case['payload'], ensure_ascii=False)}")
        
        try:
            response = requests.post(
                "http://localhost:8000/search",
                json=test_case['payload'],
                headers={"Content-Type": "application/json"}
            )
            
            print(f"狀態碼: {response.status_code}")
            
            if response.status_code == 422:
                try:
                    error_detail = response.json()
                    print("❌ 驗證錯誤:")
                    for error in error_detail.get('detail', []):
                        print(f"  - {error}")
                except:
                    print(f"❌ 錯誤: {response.text}")
            elif response.status_code == 200:
                print("✅ 成功")
            else:
                print(f"❌ 其他錯誤: {response.text}")
                
        except Exception as e:
            print(f"❌ 請求失敗: {e}")

if __name__ == "__main__":
    base_url = "http://localhost:8000"
    
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    test_api_endpoint(base_url)
    test_specific_payload() 