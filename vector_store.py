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
            # 檢查集合是否存在
            if not self._check_collection_exists():
                logger.error("集合不存在，需要重新初始化")
                return []
            
            k = k or self.config.RETRIEVAL_K
            # 抽取使用者對『上課週次（星期幾）』與『時段（早/午/晚）』的偏好
            weekday_filter = self._extract_weekday_filter(query)
            time_bucket = self._extract_time_bucket(query)
            
            # 0) 若查詢中包含課程代碼，優先以代碼精準匹配
            course_codes = self._extract_course_codes(query)
            if course_codes:
                logger.info(f"偵測到課程代碼查詢: {course_codes}")
                code_results = self._search_by_course_code(course_codes, k)
                if weekday_filter:
                    code_results = self._filter_by_weekday(code_results, weekday_filter)
                if time_bucket:
                    code_results = self._filter_by_time(code_results, time_bucket)
                if code_results:
                    logger.info(f"課程代碼匹配找到 {len(code_results)} 筆結果")
                    return code_results[:k]
            
            # 先執行向量檢索（保留未過濾版本供匱乏時回退）
            vector_results_raw = self._vector_search(query, k)
            vector_results = vector_results_raw
            if weekday_filter:
                vector_results = self._filter_by_weekday(vector_results, weekday_filter)
            if time_bucket:
                vector_results = self._filter_by_time(vector_results, time_bucket)
            
            # 檢查是否需要關鍵詞回退
            if self._should_use_keyword_fallback(query, vector_results):
                logger.info(f"查詢: '{query}' 向量檢索效果不佳，使用關鍵詞搜索補充")
                keyword_results_raw = self._keyword_search(query, k)
                keyword_results = keyword_results_raw
                if weekday_filter:
                    keyword_results = self._filter_by_weekday(keyword_results, weekday_filter)
                if time_bucket:
                    keyword_results = self._filter_by_time(keyword_results, time_bucket)
                
                # 合併結果
                all_results = self._merge_results(vector_results, keyword_results, k)
                logger.info(f"查詢: '{query}' 混合搜索找到 {len(all_results)} 個相似課程")
                
                # 如果混合搜索仍然沒有結果，至少返回向量搜索的結果
                if not all_results:
                    # 優先回退到未過濾的向量結果，再不行回退未過濾的關鍵詞結果
                    if vector_results:
                        logger.info(f"混合搜索無結果，返回已過濾的向量結果: {len(vector_results)} 個課程")
                        return vector_results
                    if vector_results_raw:
                        logger.info(f"混合搜索無結果，返回未過濾的向量結果: {len(vector_results_raw)} 個課程")
                        return vector_results_raw[:k]
                    if keyword_results:
                        logger.info(f"混合搜索無結果，返回已過濾的關鍵詞結果: {len(keyword_results)} 個課程")
                        return keyword_results
                    if keyword_results_raw:
                        logger.info(f"混合搜索無結果，返回未過濾的關鍵詞結果: {len(keyword_results_raw)} 個課程")
                        return keyword_results_raw[:k]
                
                return all_results
            
            logger.info(f"查詢: '{query}' 向量搜索找到 {len(vector_results)} 個相似課程")
            return vector_results
            
        except Exception as e:
            logger.error(f"搜尋相似課程失敗: {e}")
            return []

    def _extract_time_bucket(self, query: str) -> str:
        """從查詢中抽取時段偏好：morning/afternoon/evening 或空字串"""
        if not query:
            return ""
        q = str(query)
        if any(w in q for w in ["下午", "午后", "午後", "中午"]):
            return 'afternoon'
        if any(w in q for w in ["早上", "上午", "清晨"]):
            return 'morning'
        if "晚上" in q or "夜間" in q:
            return 'evening'
        return ""

    def _filter_by_time(self, results: List[Dict[str, Any]], bucket: str) -> List[Dict[str, Any]]:
        """以『上課時間』欄位過濾結果。格式 HH:MM；
        morning: <12:00, afternoon: 12:00–17:59, evening: >=18:00
        """
        if not results or not bucket:
            return results
        filtered = []
        for r in results:
            t = (r.get('metadata') or {}).get('meta_上課時間')
            try:
                if not t or ":" not in t:
                    continue
                hh, mm = t.split(":")
                mins = int(hh) * 60 + int(mm)
                ok = False
                if bucket == 'morning':
                    ok = mins < 12 * 60
                elif bucket == 'afternoon':
                    ok = 12 * 60 <= mins < 18 * 60
                elif bucket == 'evening':
                    ok = mins >= 18 * 60
                if ok:
                    filtered.append(r)
            except:
                continue
        return filtered

    def _extract_weekday_filter(self, query: str) -> List[int]:
        """從查詢中抽取星期過濾（1=週一 ... 7=週日；稍後會映射為資料格式 [0=日, 6=六]）。
        支援：星期/週/周/禮拜、一到日、中文字數字與阿拉伯數字、平日/週末。
        """
        import re
        if not query:
            return []
        q = query.strip()
        days = set()

        # 關鍵詞對應
        mapping = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '日': 7, '天': 7
        }
        # 週一/星期一/禮拜一 等
        for zh, num in mapping.items():
            if re.search(rf"(週|周|星期|禮拜){zh}", q):
                days.add(num)

        # 直接出現阿拉伯數字 1-7 並與週關鍵詞相鄰（避免把課程代碼當成星期）
        for m in re.finditer(r"(週|周|星期|禮拜)\s*([1-7])", q):
            days.add(int(m.group(2)))

        # 平日 / 週末
        if any(t in q for t in ["平日", "工作日"]):
            days.update([1, 2, 3, 4, 5])
        if any(t in q for t in ["週末", "周末", "假日"]):
            days.update([6, 7])

        # 形如「一三五、246」的簡寫（需與週關鍵詞同句較安全）
        if re.search(r"(週|周|星期|禮拜)", q):
            # 中文數字連寫
            for group in re.findall(r"[一二三四五六日天]{2,}", q):
                for ch in group:
                    if ch in mapping:
                        days.add(mapping[ch])
            # 阿拉伯數字連寫
            for group in re.findall(r"[1-7]{2,}", q):
                for ch in group:
                    days.add(int(ch))

        return sorted(days)

    def _filter_by_weekday(self, results: List[Dict[str, Any]], days: List[int]) -> List[Dict[str, Any]]:
        """以『上課週次』欄位過濾結果。
        資料格式為 [0]=週日, [1]=週一, ... [6]=週六（例如 "[1][3][5]" 或 "無"）。
        傳入的 days 採 1..7（7 表示週日），此處會轉成 0..6 token 比對。
        """
        if not results or not days:
            return results
        filtered = []
        # 映射：1..6 -> 1..6；7(週日) -> 0
        token_ids = [(d % 7) for d in days]
        day_tokens = [f"[{d}]" for d in token_ids]
        for r in results:
            wd = (r.get('metadata') or {}).get('meta_上課週次')
            if not wd or wd == '無':
                continue
            if any(tok in str(wd) for tok in day_tokens):
                filtered.append(r)
        return filtered

    def _extract_course_codes(self, query: str) -> List[str]:
        """從查詢中抽取可能的課程代碼（英數混合），避免把純文字當作代碼"""
        import re
        if not query:
            return []
        # 代碼規則：包含至少1個數字與1個字母，長度>=3（例：114A47、A12、ABC123）
        tokens = re.findall(r"[A-Za-z0-9-]+", query)
        codes = []
        for t in tokens:
            if len(t) >= 3 and re.search(r"[A-Za-z]", t) and re.search(r"\d", t):
                codes.append(t.upper())
        # 去重
        return list(dict.fromkeys(codes))

    def _search_by_course_code(self, codes: List[str], k: int) -> List[Dict[str, Any]]:
        """以課程代碼（精準或包含）搜尋課程，回傳高分結果"""
        try:
            data = self.collection.get()
            ids = data.get('ids') or []
            metadatas = data.get('metadatas') or []
            documents = data.get('documents') or []
            if not ids:
                return []

            results = []
            upper_codes = {c.upper() for c in codes}
            for i in range(len(ids)):
                md = metadatas[i] or {}
                doc = documents[i] if i < len(documents) else ''
                title = md.get('title', '')
                category = md.get('category', '')
                desc = md.get('description', '')
                code = (md.get('meta_課程代碼') or '').upper()
                score = 0.0
                if code:
                    if code in upper_codes:
                        score = 1.0  # 精準命中
                    elif any(c in code for c in upper_codes):
                        score = 0.95  # 包含命中
                if score > 0:
                    results.append({
                        'id': ids[i],
                        'title': title,
                        'category': category,
                        'description': desc,
                        'similarity_score': score,
                        'document': doc,
                        'metadata': md,
                        'search_type': 'code'
                    })

            # 排序與截取
            results.sort(key=lambda x: x['similarity_score'], reverse=True)
            return results[:k]
        except Exception as e:
            logger.error(f"課程代碼搜尋失敗: {e}")
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
        
        # 關鍵詞映射 - 基於AI課程.json完整分析
        keyword_map = {
            '游泳': ['游泳', '泳', 'SG', '泳訓', '水中運動', '泳池', '自由式', '蛙式', '仰式', '蝶式', '銀髮族', '基礎班'],
            '瑜珈': ['瑜珈', '瑜伽', 'Yoga', 'yoga', '正位', '修復', '陰瑜珈', '流瑜珈', '哈達', '瑜珈提斯', '核心瑜珈'],
            '有氧': ['有氧', '燃脂', '減肥', '瘦身', '塑身', '雕塑', '身形', '體態', '產後', '恢復', '修復', '緊實', '線條', '活力', '爆汗'],
            '舞蹈': ['舞蹈', '跳舞'],
            '韓流舞蹈': ['韓國', '韓流', 'KPOP', 'K-POP', 'kpop', '流行舞', '韓國流行舞', '韓流舞', '女團'],
            '街舞': ['街舞', 'Street', 'street', 'Hip Hop', 'hip hop'],
            '爵士舞': ['爵士', 'Jazz', 'jazz', 'Sexy', 'sexy', 'Free Jazz', '流行爵士', '艷舞'],
            '芭蕾': ['芭蕾', 'Ballet', 'ballet', '空中芭蕾'],
            '拉丁舞': ['拉丁', '倫巴', '恰恰', '森巴', '鬥牛', '牛仔'],
            '肚皮舞': ['肚皮舞', 'BELLYDANCE', 'belly dance', 'Belly Dance', 'S曲線', '異域', '性感', '窈窕', '摩登瘦身肚皮舞', '基礎肚皮舞', '融合風'],
            '武術': ['武術', '太極', '防身', '防身術', '自衛', '詠春', '抗暴', '武舞', '短兵', '技擊', '拳術', '武功', '八段錦', '氣功', '易筋經', '24式', '42式'],
            '拳擊': ['拳擊', '拳', '拳擊有氧', '拳擊體能', '踢拳', '踢拳擊', '輕量拳擊', 'boxing', 'Boxing', 'Thump Boxing', '拳擊間歇', '拳擊訓練', '核心拳擊'],
            '肌力': ['肌力', '重訓', '訓練', '強化', '鍛鍊', '肌肉', '核心', 'TRX', '壺鈴', '懸吊', '功能性', '徒手'],
            '飛輪': ['飛輪', '騎行', '騎車', '單車', '瘋飛輪', '享瘦樂騎'],
            '空中瑜珈': ['空中瑜珈', '空瑜', '吊床', '低空', '空中芭蕾', '空中舞蹈'],
            '潛水': ['潛水', '人魚', '救生', '自由潛水', '水肺潛水', '魚人共舞'],
            'Zumba': ['Zumba', 'zumba', '尊巴', 'Amazing Zumba', 'Strong'],
            '皮拉提斯': ['皮拉提斯', 'Pilates', 'pilates', '精雕細琢'],
            '球類': ['球類', '羽球', '桌球', '網球', '籃球', '壁球'],
            '兒童': ['兒童', '小孩', '孩子', 'Children', 'children', '小一', '小二', '小三', '國一', '國二', '國三'],
            '幼兒': ['幼兒', '小朋友', '寶寶', '3歲', '4歲', '5歲', '6歲'],
            '假日': ['假日', '週末', '周末'],
            '年齡': ['五歲', '5歲', '六歲', '6歲', '七歲', '7歲', '8歲', '9歲'],
            '養生': ['養生', '保健', '調理', '太極', '氣功', '銀髮族'],
            '體能': ['體能', '體力', '耐力', '健身', '運動', '活動', '循環'],
            '伸展': ['伸展', '拉筋', '柔軟度', '靈活', '放鬆', 'Stretch', 'stretch', '修復'],
            '包班': ['包班', '團體', '客製化', '公司', '企業']
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
        category_keywords = [
            '游泳', '瑜珈', '有氧', '舞蹈', '韓流舞蹈', '街舞', '爵士舞', '芭蕾', '拉丁舞', 
            '肚皮舞', '武術', '拳擊', '肌力', '飛輪', '空中瑜珈', '潛水', 'Zumba', '皮拉提斯',
            '球類', '兒童', '幼兒', '減肥', '瘦身', '塑身', '雕塑', '身形', '體態', '產後', 
            '燃脂', '訓練', '重訓', '健身', '運動', 'TRX', '壺鈴', '太極', '氣功', '包班'
        ]
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
    
    def _check_collection_exists(self) -> bool:
        """檢查集合是否存在且可用"""
        try:
            # 嘗試檢查集合數量
            self.collection.count()
            return True
        except Exception as e:
            logger.warning(f"集合檢查失敗: {e}")
            try:
                # 嘗試重新取得集合
                self.collection = self.client.get_collection(self.config.COLLECTION_NAME)
                self.collection.count()
                return True
            except Exception as e2:
                logger.error(f"無法取得集合: {e2}")
                return False
    
    def get_courses_by_category(self, category: str, limit: int = None) -> List[Dict[str, Any]]:
        """根據類別獲取課程"""
        try:
            # 檢查集合是否存在
            if not self._check_collection_exists():
                logger.error("集合不存在，無法獲取課程")
                return []
            
            # 如果沒有指定限制，獲取所有課程
            if limit is None:
                # 先獲取該類別的總數
                total_count = self.collection.count()
                limit = total_count if total_count > 0 else 1000  # 設定一個安全的大數字
            
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
            # 檢查集合是否存在
            if not self._check_collection_exists():
                logger.warning("集合不存在，返回0")
                return {
                    'total_courses': 0,
                    'collection_name': self.config.COLLECTION_NAME
                }
            
            count = self.collection.count()
            return {
                'total_courses': count,
                'collection_name': self.config.COLLECTION_NAME
            }
        except Exception as e:
            logger.error(f"獲取集合統計失敗: {e}")
            # 如果集合不存在或有錯誤，返回0
            return {
                'total_courses': 0,
                'collection_name': self.config.COLLECTION_NAME
            }
    
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
    
    def close_connection(self):
        """關閉資料庫連接（Windows 檔案鎖定問題修復）"""
        try:
            # 嘗試各種方式關閉 ChromaDB 連接
            if self.client:
                try:
                    # 嘗試關閉持久化客戶端
                    if hasattr(self.client, '_client') and self.client._client:
                        self.client._client.reset()
                except:
                    pass
                
                try:
                    # 嘗試關閉客戶端
                    if hasattr(self.client, 'reset'):
                        self.client.reset()
                except:
                    pass
                
                try:
                    # 嘗試直接關閉
                    if hasattr(self.client, 'close'):
                        self.client.close()
                except:
                    pass
            
            # 清理引用
            self.collection = None
            self.client = None
            
            # 強制垃圾回收
            import gc
            gc.collect()
            
            # 等待一下讓系統釋放檔案
            import time
            time.sleep(0.5)
            
            logger.info("已關閉向量數據庫連接")
        except Exception as e:
            logger.warning(f"關閉連接時出現警告: {e}")
    
    def __del__(self):
        """析構函數 - 確保連接關閉"""
        try:
            self.close_connection()
        except:
            pass 
