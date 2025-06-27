import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Any, Tuple
import logging
import os
from config import Config

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorStore:
    """向量數據庫管理器 - 使用ChromaDB儲存和檢索課程向量"""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.embedding_model = None
        self.client = None
        self.collection = None
        self.setup_vector_store()
    
    def setup_vector_store(self):
        """初始化向量數據庫和嵌入模型"""
        try:
            # 初始化嵌入模型
            logger.info("載入嵌入模型...")
            self.embedding_model = SentenceTransformer(self.config.EMBEDDING_MODEL)
            
            # 初始化ChromaDB客戶端
            logger.info("初始化ChromaDB...")
            # 創建ChromaDB設定
            chroma_settings = Settings(
                anonymized_telemetry=False,
                allow_reset=True,
                persist_directory=self.config.VECTOR_DB_PATH
            )
            
            # 初始化持久化客戶端
            self.client = chromadb.PersistentClient(
                path=self.config.VECTOR_DB_PATH,
                settings=chroma_settings
            )
            
            # 創建或獲取集合
            self.collection = self.client.get_or_create_collection(
                name=self.config.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
            
            logger.info("向量數據庫初始化完成")
            
        except Exception as e:
            logger.error(f"向量數據庫初始化失敗: {e}")
            raise
    
    def embed_text(self, text: str) -> List[float]:
        """將文本轉換為向量"""
        try:
            embedding = self.embedding_model.encode([text])[0]
            return embedding.tolist()
        except Exception as e:
            logger.error(f"文本嵌入失敗: {e}")
            return []
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """批量將文本轉換為向量"""
        try:
            embeddings = self.embedding_model.encode(texts)
            return [embedding.tolist() for embedding in embeddings]
        except Exception as e:
            logger.error(f"批量文本嵌入失敗: {e}")
            return []
    
    def add_courses(self, courses_data: List[Dict[str, Any]]):
        """將課程數據添加到向量數據庫"""
        try:
            logger.info(f"開始向量化 {len(courses_data)} 筆課程數據...")
            
            # 準備數據
            texts = [course['searchable_text'] for course in courses_data]
            ids = [course['id'] for course in courses_data]
            metadatas = []
            
            for course in courses_data:
                metadata = {
                    'course_id': str(course['course_id']),
                    'title': course['title'],
                    'category': course['category'],
                    'description': course['description'][:500]  # 限制長度避免超出限制
                }
                # 添加其他有用的元數據
                for key, value in course['metadata'].items():
                    if key not in ['課程介紹'] and value is not None:
                        metadata[f"meta_{key}"] = str(value)[:100]  # 限制長度
                
                metadatas.append(metadata)
            
            # 生成嵌入向量
            logger.info("生成嵌入向量...")
            embeddings = self.embed_texts(texts)
            
            # 添加到集合
            logger.info("將數據添加到向量數據庫...")
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"成功添加 {len(courses_data)} 筆課程到向量數據庫")
            
        except Exception as e:
            logger.error(f"添加課程到向量數據庫失敗: {e}")
            raise
    
    def search_similar_courses(self, query: str, k: int = None) -> List[Dict[str, Any]]:
        """搜尋相似的課程 - 使用混合策略（向量檢索 + 關鍵詞匹配）"""
        try:
            k = k or self.config.RETRIEVAL_K
            
            # 先執行向量檢索
            vector_results = self._vector_search(query, k)
            
            # 檢查是否需要關鍵詞回退
            if self._should_use_keyword_fallback(query, vector_results):
                logger.info(f"查詢: '{query}' 向量檢索效果不佳，使用關鍵詞搜索補充")
                keyword_results = self._keyword_search(query, k)
                
                # 合併結果
                all_results = self._merge_results(vector_results, keyword_results, k)
                logger.info(f"查詢: '{query}' 混合搜索找到 {len(all_results)} 個相似課程")
                return all_results
            
            logger.info(f"查詢: '{query}' 向量搜索找到 {len(vector_results)} 個相似課程")
            return vector_results
            
        except Exception as e:
            logger.error(f"搜尋相似課程失敗: {e}")
            return []
    
    def _vector_search(self, query: str, k: int) -> List[Dict[str, Any]]:
        """執行向量檢索"""
        # 將查詢轉換為向量
        query_embedding = self.embed_text(query)
        if not query_embedding:
            return []
        
        # 執行搜尋
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(k * 3, 20),
            include=['metadatas', 'documents', 'distances']
        )
        
        # 格式化結果
        formatted_results = []
        for i in range(len(results['ids'][0])):
            similarity_score = 1 - results['distances'][0][i]
            result = {
                'id': results['ids'][0][i],
                'title': results['metadatas'][0][i].get('title', ''),
                'category': results['metadatas'][0][i].get('category', ''),
                'description': results['metadatas'][0][i].get('description', ''),
                'similarity_score': similarity_score,
                'document': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'search_type': 'vector'
            }
            formatted_results.append(result)
        
        # 記錄相似度分數
        if formatted_results:
            top_scores = [f"{r['similarity_score']:.3f}" for r in formatted_results[:5]]
            logger.info(f"查詢: '{query}' 前5個結果的相似度分數: {top_scores}")
        
        # 過濾並返回結果
        filtered_results = [
            result for result in formatted_results 
            if result['similarity_score'] >= self.config.SIMILARITY_THRESHOLD
        ]
        
        return filtered_results[:k]
    
    def _keyword_search(self, query: str, k: int) -> List[Dict[str, Any]]:
        """執行關鍵詞匹配搜索"""
        try:
            # 提取查詢關鍵詞
            keywords = self._extract_keywords(query)
            if not keywords:
                return []
            
            # 獲取所有課程 - 使用正確的ChromaDB API
            collection_data = self.collection.get()
            
            # 轉換為我們需要的格式
            all_results = {
                'ids': collection_data['ids'] if collection_data['ids'] else [],
                'metadatas': collection_data['metadatas'] if collection_data['metadatas'] else [],
                'documents': collection_data['documents'] if collection_data['documents'] else []
            }
            
            keyword_results = []
            for i in range(len(all_results['ids'])):
                metadata = all_results['metadatas'][i]
                document = all_results['documents'][i]
                
                # 計算關鍵詞匹配分數
                match_score = self._calculate_keyword_match_score(keywords, document, metadata)
                
                if match_score > 0.3:  # 設定最低匹配閾值
                    result = {
                        'id': all_results['ids'][i],
                        'title': metadata.get('title', ''),
                        'category': metadata.get('category', ''),
                        'description': metadata.get('description', ''),
                        'similarity_score': match_score,
                        'document': document,
                        'metadata': metadata,
                        'search_type': 'keyword'
                    }
                    keyword_results.append(result)
            
            # 按匹配分數排序
            keyword_results.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            logger.info(f"關鍵詞搜索找到 {len(keyword_results)} 個匹配課程")
            return keyword_results[:k]
            
        except Exception as e:
            logger.error(f"關鍵詞搜索失敗: {e}")
            return []
    
    def _extract_keywords(self, query: str) -> List[str]:
        """提取查詢關鍵詞"""
        keywords = []
        
        # 關鍵詞映射
        keyword_map = {
            '游泳': ['游泳', '泳', 'SG', '泳訓', '水中運動', '泳池'],
            '兒童': ['兒童', '小孩', '孩子'],
            '幼兒': ['幼兒', '小朋友', '寶寶'],
            '假日': ['假日', '週末', '周末'],
            '五歲': ['五歲', '5歲'],
            '六歲': ['六歲', '6歲'],
            '七歲': ['七歲', '7歲'],
            '瑜珈': ['瑜珈', '瑜伽'],
            '有氧': ['有氧', '燃脂'],
            '舞蹈': ['舞蹈', '跳舞', '韓國', '韓流', 'KPOP', 'K-POP', '流行舞', '韓國流行舞', '街舞', '爵士', '女團'],
            '武術': ['武術', '太極', '防身', '防身術', '自衛', '詠春', '抗暴', '武舞', '短兵', '技擊', '拳術', '武功'],
            '肌力': ['肌力', '重訓'],
            '球類': ['球類', '羽球', '桌球'],
            '養生': ['養生', '保健', '調理', '太極', '氣功']
        }
        
        for main_key, synonyms in keyword_map.items():
            if any(syn in query for syn in synonyms):
                keywords.extend(synonyms)
        
        return list(set(keywords))
    
    def _calculate_keyword_match_score(self, keywords: List[str], document: str, metadata: dict) -> float:
        """計算關鍵詞匹配分數"""
        if not keywords:
            return 0.0
        
        # 合併所有可搜索文本
        searchable_text = f"{document} {metadata.get('title', '')} {metadata.get('category', '')}"
        
        matches = 0
        category_match = False
        
        for keyword in keywords:
            if keyword in searchable_text:
                matches += 1
                # 類別匹配給額外加分
                if keyword in metadata.get('category', ''):
                    category_match = True
        
        # 基礎匹配分數
        base_score = matches / len(keywords)
        
        # 類別匹配加分
        if category_match:
            base_score += 0.2
        
        # 多關鍵詞匹配加分
        if matches >= 2:
            base_score += 0.1
        
        return min(base_score, 1.0)
    
    def _should_use_keyword_fallback(self, query: str, vector_results: List[Dict]) -> bool:
        """判斷是否需要關鍵詞回退"""
        # 1. 如果向量結果太少
        if len(vector_results) < 2:
            return True
        
        # 2. 如果查詢包含明確類別詞但結果不相關
        category_keywords = ['游泳', '瑜珈', '有氧', '舞蹈', '武術', '兒童', '幼兒']
        query_has_category = any(kw in query for kw in category_keywords)
        
        if query_has_category:
            relevant_count = 0
            for result in vector_results:
                for kw in category_keywords:
                    if kw in query and kw in f"{result['title']} {result['category']} {result['description']}":
                        relevant_count += 1
                        break
            
            # 如果相關結果少於50%，使用關鍵詞回退
            if relevant_count / len(vector_results) < 0.5:
                return True
        
        return False
    
    def _merge_results(self, vector_results: List[Dict], keyword_results: List[Dict], k: int) -> List[Dict[str, Any]]:
        """合併向量和關鍵詞搜索結果"""
        # 去重並合併
        seen_ids = set()
        merged = []
        
        # 優先考慮關鍵詞結果（因為它們在這種情況下更準確）
        for result in keyword_results + vector_results:
            if result['id'] not in seen_ids:
                seen_ids.add(result['id'])
                merged.append(result)
                if len(merged) >= k:
                    break
        
        return merged
    
    def get_courses_by_category(self, category: str, limit: int = 10) -> List[Dict[str, Any]]:
        """根據類別獲取課程"""
        try:
            results = self.collection.query(
                query_texts=[f"類別: {category}"],
                n_results=limit,
                where={"category": category},
                include=['metadatas', 'documents']
            )
            
            formatted_results = []
            for i in range(len(results['ids'][0])):
                result = {
                    'id': results['ids'][0][i],
                    'title': results['metadatas'][0][i].get('title', ''),
                    'category': results['metadatas'][0][i].get('category', ''),
                    'description': results['metadatas'][0][i].get('description', ''),
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i]
                }
                formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"根據類別獲取課程失敗: {e}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """獲取集合統計資訊"""
        try:
            count = self.collection.count()
            return {
                'total_courses': count,
                'collection_name': self.config.COLLECTION_NAME
            }
        except Exception as e:
            logger.error(f"獲取集合統計失敗: {e}")
            return {}
    
    def reset_collection(self):
        """重置集合（慎用）"""
        try:
            self.client.delete_collection(self.config.COLLECTION_NAME)
            self.collection = self.client.create_collection(
                name=self.config.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("集合已重置")
        except Exception as e:
            logger.error(f"重置集合失敗: {e}")
            raise 