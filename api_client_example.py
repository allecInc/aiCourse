import requests
import json
from typing import Dict, Any, List
import time

class CourseRecommendationAPIClient:
    """課程推薦API客戶端"""
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        
        # 設定請求頭
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def health_check(self) -> Dict[str, Any]:
        """檢查API服務健康狀態"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status": "error"}
    
    def get_recommendations(self, query: str, k: int = 5) -> Dict[str, Any]:
        """獲取課程推薦"""
        try:
            payload = {
                "query": query,
                "k": k
            }
            
            if self.api_key:
                payload["api_key"] = self.api_key
            
            response = self.session.post(
                f"{self.base_url}/recommend",
                json=payload
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "success": False}
    
    def search_courses(self, query: str, k: int = 10) -> Dict[str, Any]:
        """搜索課程（僅向量檢索）"""
        try:
            payload = {
                "query": query,
                "k": k
            }
            
            response = self.session.post(
                f"{self.base_url}/search",
                json=payload
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def get_categories(self) -> Dict[str, Any]:
        """獲取所有課程類別"""
        try:
            response = self.session.get(f"{self.base_url}/categories")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def get_courses_by_category(self, category: str, limit: int = 10) -> Dict[str, Any]:
        """根據類別獲取課程"""
        try:
            response = self.session.get(
                f"{self.base_url}/categories/{category}/courses",
                params={"limit": limit}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def get_system_stats(self) -> Dict[str, Any]:
        """獲取系統統計信息"""
        try:
            response = self.session.get(f"{self.base_url}/stats")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def rebuild_knowledge_base(self) -> Dict[str, Any]:
        """重建知識庫"""
        try:
            response = self.session.post(f"{self.base_url}/rebuild-knowledge-base")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

def print_separator(title: str):
    """列印分隔線和標題"""
    print("\n" + "="*60)
    print(f" {title} ")
    print("="*60)

def pretty_print_json(data: Dict[str, Any]):
    """美化列印JSON數據"""
    print(json.dumps(data, ensure_ascii=False, indent=2))

def main():
    """主函數 - API使用範例"""
    
    # 初始化客戶端
    # 注意：請將您的OpenAI API密鑰替換到這裡
    API_KEY = "your-openai-api-key-here"  # 替換為您的實際API密鑰
    
    client = CourseRecommendationAPIClient(
        base_url="http://localhost:8000",
        api_key=API_KEY
    )
    
    print("🤖 課程推薦API使用範例")
    
    # 1. 健康檢查
    print_separator("1. 健康檢查")
    health = client.health_check()
    pretty_print_json(health)
    
    if not health.get("system_ready", False):
        print("❌ 系統未就緒，請檢查API服務狀態")
        return
    
    # 2. 獲取系統統計
    print_separator("2. 系統統計")
    stats = client.get_system_stats()
    pretty_print_json(stats)
    
    # 3. 獲取所有類別
    print_separator("3. 獲取課程類別")
    categories = client.get_categories()
    pretty_print_json(categories)
    
    # 4. 課程搜索範例
    print_separator("4. 課程搜索")
    search_queries = [
        "游泳課程",
        "瑜珈放鬆",
        "減肥燃脂"
    ]
    
    for query in search_queries:
        print(f"\n搜索查詢: '{query}'")
        search_result = client.search_courses(query, k=3)
        if "error" not in search_result:
            print(f"找到 {search_result['total_found']} 個課程")
            for i, course in enumerate(search_result['courses'], 1):
                print(f"  {i}. {course['title']} ({course['category']}) - 相似度: {course['similarity_score']:.3f}")
        else:
            print(f"搜索失敗: {search_result['error']}")
    
    # 5. 課程推薦範例
    print_separator("5. 智能課程推薦")
    recommendation_queries = [
        "我想要減肥燃脂的課程",
        "適合初學者的瑜珈課程",
        "能夠增強體力的運動課程"
    ]
    
    for query in recommendation_queries:
        print(f"\n推薦查詢: '{query}'")
        
        if API_KEY == "your-openai-api-key-here":
            print("⚠️  請設定您的OpenAI API密鑰以使用推薦功能")
            continue
            
        recommendation = client.get_recommendations(query, k=3)
        
        if recommendation.get("success", False):
            print("✅ 推薦成功!")
            print(f"回應時間: {recommendation['response_time']:.2f}秒")
            print(f"\n🤖 AI推薦:")
            print(recommendation['recommendation'])
            
            print(f"\n📚 找到 {recommendation['total_found']} 個相關課程:")
            for i, course in enumerate(recommendation['retrieved_courses'], 1):
                print(f"  {i}. {course['title']} ({course['category']})")
        else:
            print(f"❌ 推薦失敗: {recommendation.get('error', '未知錯誤')}")
    
    # 6. 根據類別獲取課程
    print_separator("6. 根據類別瀏覽課程")
    if categories.get("categories"):
        # 選擇第一個類別作為範例
        sample_category = categories["categories"][0]
        print(f"瀏覽類別: '{sample_category}'")
        
        category_courses = client.get_courses_by_category(sample_category, limit=5)
        if "error" not in category_courses:
            print(f"找到 {category_courses['total_found']} 個 {sample_category} 課程")
            for i, course in enumerate(category_courses['courses'], 1):
                print(f"  {i}. {course['title']}")
                print(f"     描述: {course['description'][:100]}...")
        else:
            print(f"獲取課程失敗: {category_courses['error']}")
    
    print_separator("API範例測試完成！")
    print("💡 提示:")
    print("- 請確保API服務在 http://localhost:8000 運行")
    print("- 設定您的OpenAI API密鑰以使用完整推薦功能")
    print("- 訪問 http://localhost:8000/docs 查看完整API文檔")

if __name__ == "__main__":
    main() 