import openai
import pyodbc
from typing import List, Dict, Any, Optional
import logging
import os
import time
from datetime import datetime
from config import Config
from vector_store import VectorStore
from course_processor import CourseProcessor
from conversation_manager import ConversationManager

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGSystem:
    """RAG課程推薦系統 - 整合檢索增強生成功能"""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.vector_store = None
        self.course_processor = None
        self.openai_client = None
        self.conversation_manager = ConversationManager()  # 新增對話管理器
        self.last_data_file_mtime = None  # 記錄資料檔案的最後修改時間
        self.setup_system()
    
    def setup_system(self):
        """初始化RAG系統"""
        try:
            # 設定OpenAI API
            openai.api_key = self.config.OPENAI_API_KEY
            self.openai_client = openai.OpenAI(api_key=self.config.OPENAI_API_KEY)
            
            # 初始化課程處理器
            self.course_processor = CourseProcessor()
            
            # 初始化向量數據庫
            self.vector_store = VectorStore(self.config)
            
            logger.info("RAG系統初始化完成")
            
        except Exception as e:
            logger.error(f"RAG系統初始化失敗: {e}")
            raise

    def generate_sql_where_clause(self, user_query: str) -> str:
        """
        使用 AI 將自然語言查詢轉換為 SQL WHERE 條件子句（採用思維鏈 CoT 技術）。
        """
        logger.info(f"開始為查詢生成 SQL WHERE 子句 (CoT): {user_query}")

        schema_description = """
        - 課程代碼 (NVARCHAR): 課程的唯一識別碼，格式類似 '114A47'.
        - 大類 (NVARCHAR): 課程的主要分類，例如 '有氧系列', '瑜珈系列', '舞蹈系列'.
        - 課程名稱 (NVARCHAR): 課程的具體名稱.
        - 授課教師 (NVARCHAR): 教師的姓名.
        - 上課週次 (NVARCHAR): 描述上課的星期，例如 '[1][3][5]' 代表週一、三、五.
        - 上課時間 (TIME): 課程開始時間，格式為 'HH:MM'.
        - 課程費用 (INT): 課程的價格.
        """

        system_prompt = f"""
        你是一個頂級的 SQL 專家，專長是將自然語言轉換為 SQL 查詢條件。請遵循「思維鏈」的步驟來分析用戶請求，並以 JSON 格式輸出結果。

        【資料庫欄位綱要】
        {schema_description}

        【執行步驟】
        1.  **思考 (thought)**: 逐步分析用戶的請求，拆解出所有的查詢意圖、實體和限制條件。
        2.  **條件映射 (mapping)**: 將每個意圖分別映射到對應的資料庫欄位和具體的 SQL 條件表達式。
        3.  **SQL生成 (sql)**: 根據映射結果，組合出最終的 SQL `WHERE` 條件子句。如果沒有可用的條件，則此欄位應為空字串 ""。

        【輸出格式】
        嚴格使用以下 JSON 格式輸出，不要有任何額外的文字或解釋：
        ```json
        {{
          "thought": "用戶的思考過程分析...",
          "sql": "最終生成的 WHERE 條件子句..."
        }}
        ```

        【重要規則】
        - `WHERE` 子句中不要包含 `WHERE` 這個詞。
        - 對於文字欄位，優先使用 `LIKE '%keyword%'` 進行模糊匹配，除非用戶意圖非常明確。
        - `上課週次` 欄位的資料格式：'[0]' 表示週日、'[1]' 表示週一、...、'[6]' 表示週六。
          因此：週一→'%[1]%'、週二→'%[2]%'、...、週六→'%[6]%'、週日→'%[0]%'
        - 如果用戶的請求與課程查詢完全無關（例如打招呼），則 `sql` 欄位必須為空字串 ""。

        【範例】
        用戶請求: "我想找 BoBo 老師開的，費用低於 1000 元的瑜珈課"
        ```json
        {{
          "thought": "用戶指定了三個條件：1. 老師是 BoBo。 2. 費用需要低於 1000。 3. 課程大類是瑜珈。",
          "sql": "授課教師 = 'BoBo(男)' AND 課程費用 < 1000 AND 大類 = 'C　瑜珈系列'"
        }}
        ```
        用戶請求: "你好啊"
        ```json
        {{
          "thought": "用戶在打招呼，與課程查詢無關。",
          "sql": ""
        }}
        ```
        """

        try:
            response = self.openai_client.chat.completions.create(
                model=self.config.MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"用戶請求: \"{user_query}\""}
                ],
                temperature=0.0,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            response_text = response.choices[0].message.content.strip()
            logger.info(f"AI (CoT) response: {response_text}")
            
            import json
            try:
                data = json.loads(response_text)
                where_clause = data.get("sql", "")
                
                # 基本的安全檢查
                forbidden_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', ';']
                if any(keyword in where_clause.upper() for keyword in forbidden_keywords):
                    logger.warning(f"檢測到潛在的惡意 SQL 關鍵字，拒絕生成: {where_clause}")
                    return ""
                
                return where_clause
            except json.JSONDecodeError:
                logger.error(f"無法解析 AI 回傳的 JSON: {response_text}")
                return ""

        except Exception as e:
            logger.error(f"呼叫 OpenAI 生成 SQL WHERE 子句失敗: {e}")
            return ""

    def fetch_courses_by_sql(self, sql_query: str) -> List[Dict[str, Any]]:
        """
        使用提供的完整 SQL 查詢來獲取課程資料。
        """
        logger.info(f"執行 SQL 查詢: {sql_query[:200]}...")
        conn_str = (
            f"DRIVER={self.config.DB_DRIVER};"
            f"SERVER={self.config.DB_SERVER};"
            f"DATABASE={self.config.DB_DATABASE};"
            f"UID={self.config.DB_USER};"
            f"PWD={self.config.DB_PASSWORD};"
        )
        courses = []
        try:
            with pyodbc.connect(conn_str, timeout=5) as cnxn:
                cursor = cnxn.cursor()
                cursor.execute(sql_query)
                columns = [column[0] for column in cursor.description]
                rows = cursor.fetchall()
                courses = [dict(zip(columns, row)) for row in rows]
            logger.info(f"查詢成功，獲取了 {len(courses)} 筆課程。")
        except Exception as e:
            logger.error(f"執行 SQL 查詢失敗: {e}")
        return courses

    def query_database_with_ai(self, user_query: str) -> List[Dict[str, Any]]:
        """
        主要流程：將自然語言轉換為 SQL 查詢並從資料庫獲取結果。
        """
        logger.critical("--- EXECUTING LIVE AI-SQL DATABASE QUERY ---")
        where_clause = self.generate_sql_where_clause(user_query)

        if not where_clause:
            logger.info("AI 未能生成有效的 WHERE 子句，返回空結果。")
            return []

        # --- 翻譯層：將 AI 使用的別名翻譯回真實的 SQL 欄位 ---
        translation_map = {
            '大類': 'C.k02',
            '課程名稱': 'B.k03',
            '課程介紹': 'B.k18',
            '教室名稱': 'D.k02',
            '課程代碼': 'A.k34',
            '授課教師': 'E.k02',
            '上課週次': 'A.k07',
            '課程費用': 'A.k13',
            '體驗費用': 'A.k14',
            '開班人數': 'A.k16',
            '滿班人數': 'A.k17',
            # 處理 CASE 和 CONVERT 的特殊情況
            '年齡限制': "(CASE WHEN A.k80 = 0 THEN '無' ELSE '有' END)",
            '上課時間': "(CONVERT(VARCHAR(5), A.k08, 108))"
        }
        
        translated_where_clause = where_clause
        for alias, real_column in translation_map.items():
            translated_where_clause = translated_where_clause.replace(alias, real_column)
        
        logger.info(f"翻譯後的 WHERE 子句: {translated_where_clause}")
        # --------------------------------------------------------

        base_query = """
        SELECT C.k02 as 大類, B.k03 as 課程名稱, B.k18 as 課程介紹, D.k02 as 教室名稱, 
               A.k34 as 課程代碼, isnull(E.k02,'無') as 授課教師, 
               CASE WHEN A.k80 = 0 THEN '無' ELSE '有' END as 年齡限制,
               isnull(A.k07,'無') as 上課週次, CONVERT(VARCHAR(5), A.k08, 108) AS 上課時間,
               A.k13 as 課程費用, A.k14 as 體驗費用, A.k16 as 開班人數, A.k17 as 滿班人數
        FROM wk05 A
        INNER JOIN wk01 B ON A.k04 = B.k00
        INNER JOIN wk00 C ON B.k01 = C.k00
        INNER JOIN wk02 D ON A.k02 = D.k00
        INNER JOIN wk03eee E ON A.k05 = E.k00
        WHERE A.k06 = 1
        """

        final_sql = f"{base_query} AND ({translated_where_clause})"
        
        # 執行查詢
        courses_from_db = self.fetch_courses_by_sql(final_sql)

        # 將資料庫查詢結果轉換為 UI 期望的格式
        transformed_courses = []
        for course in courses_from_db:
            transformed_courses.append({
                'title': course.get('課程名稱'),
                'category': course.get('大類'),
                'description': course.get('課程介紹'),
                'similarity_score': 1.0,  # 因為是精確篩選，所以給定一個假分數
                'metadata': {
                    'meta_授課教師': course.get('授課教師'),
                    'meta_年齡限制': course.get('年齡限制'),
                    'meta_上課時間': course.get('上課時間'),
                    'meta_課程費用': course.get('課程費用'),
                    'meta_體驗費用': course.get('體驗費用')
                }
            })
        
        return transformed_courses

    def generate_clarifying_question(self, user_query: str) -> str:
        """
        當找不到課程時，生成一個澄清問題。
        """
        logger.info(f"為查詢生成澄清問題: {user_query}")
        system_prompt = """
        你是一個友善且專業的AI課程顧問。系統剛剛根據用戶的查詢找不到任何完全匹配的課程。
        你的任務是：
        1.  首先，明確地告知用戶，沒有找到完全符合他們「所有」條件的課程。請務必提到用戶的具體條件（例如「下午」、「王老師」等）。
        2.  接著，立刻無縫地轉為提出有幫助的、引導性的問題，來放寬或修改搜尋條件。

        重要原則:
        1.  語氣要自然、友善。
        2.  第一句話必須是直接的回應，承認找不到「完全符合」的結果。
        3.  第二句話必須是開放性的提問，提供替代方案或詢問其他偏好。
        4.  用繁體中文回答。

        範例:
        - 用戶查詢: "我想上一些下午的瑜伽課程"
        - 你的回應: "抱歉，目前沒有找到完全符合在「下午」開課的瑜珈課程。不過我們有很多在早上或晚上開課的瑜珈選項，請問您對這些時段方便嗎？或者您對特定老師有沒有偏好呢？"
        - 用戶查詢: "我想找王大明老師的課"
        - 你的回應: "我們目前沒有找到「王大明」老師開設的課程。請問老師的名字是否正確？或者，您對其他老師的同類型課程會感興趣嗎？"
        """
        try:
            response = self.openai_client.chat.completions.create(
                model=self.config.MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"用戶查詢: \"{user_query}\""}
                ],
                temperature=0.8,
                max_tokens=300
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"生成澄清問題失敗: {e}")
            return "抱歉，我不太確定該如何幫您縮小範圍，您可以試著提供更具體的課程名稱或類別嗎？"

    def initialize_knowledge_base(self, force_rebuild: bool = False, check_updates: bool = True):
        """初始化知識庫"""
        try:
            # 檢查資料檔案是否更新
            if check_updates and self._should_update_data():
                logger.info("檢測到資料檔案已更新，重新建立知識庫...")
                force_rebuild = True
            
            # 檢查是否已有數據
            stats = self.vector_store.get_collection_stats()
            
            # 如果集合有錯誤或資料為空，強制重建
            if stats.get('total_courses', 0) == 0:
                logger.info("知識庫為空或有錯誤，需要重建...")
                force_rebuild = True
            elif not force_rebuild:
                logger.info(f"知識庫已存在，包含 {stats['total_courses']} 筆課程")
                # 更新檔案修改時間記錄
                self._update_file_mtime()
                return
            
            # 重新建立知識庫
            logger.info("開始建立知識庫...")
            
            # 處理課程數據
            courses_data = self.course_processor.prepare_for_vectorization()
            
            if force_rebuild:
                self.vector_store.reset_collection()
            
            # 添加到向量數據庫
            self.vector_store.add_courses(courses_data)
            
            # 更新檔案修改時間記錄
            self._update_file_mtime()
            
            logger.info("知識庫建立完成")
            
        except Exception as e:
            logger.error(f"初始化知識庫失敗: {e}")
            raise
    
    def retrieve_relevant_courses(self, query: str, k: int = None) -> List[Dict[str, Any]]:
        """檢索相關課程"""
        try:
            k = k or self.config.RETRIEVAL_K
            relevant_courses = self.vector_store.search_similar_courses(query, k)
            
            # 如果返回空結果且可能是集合錯誤，嘗試重建
            if not relevant_courses:
                logger.info("檢索結果為空，檢查是否需要重建知識庫...")
                stats = self.vector_store.get_collection_stats()
                if stats.get('total_courses', 0) == 0:
                    logger.info("知識庫似乎有問題，嘗試重建...")
                    try:
                        self.initialize_knowledge_base(force_rebuild=True, check_updates=False)
                        # 重新嘗試檢索
                        relevant_courses = self.vector_store.search_similar_courses(query, k)
                    except Exception as rebuild_error:
                        logger.error(f"重建知識庫失敗: {rebuild_error}")
                        # 如果重建失敗，返回空結果但不崩潰
            
            # 記錄檢索結果
            logger.info(f"檢索到 {len(relevant_courses)} 個相關課程")
            for course in relevant_courses:
                logger.debug(f"課程: {course['title']}, 相似度: {course['similarity_score']:.3f}")
            
            return relevant_courses
            
        except Exception as e:
            logger.error(f"檢索相關課程失敗: {e}")
            # 如果出現集合不存在的錯誤，嘗試重建
            if "does not exists" in str(e) or "Collection" in str(e):
                logger.info("檢測到集合錯誤，嘗試重建知識庫...")
                try:
                    self.initialize_knowledge_base(force_rebuild=True, check_updates=False)
                    # 重新嘗試檢索
                    return self.vector_store.search_similar_courses(query, k)
                except Exception as rebuild_error:
                    logger.error(f"重建後仍然失敗: {rebuild_error}")
            return []
    
    def generate_course_recommendation(self, query: str, retrieved_courses: List[Dict[str, Any]], 
                                      session_id: str = None) -> str:
        """使用 GPT 生成課程推薦（嚴格避免幻覺；只允許輸出 Top‑K 中的課名）"""
        try:
            import json
            if not retrieved_courses:
                return "抱歉，我找不到符合您需求的課程。請嘗試用不同的關鍵字搜尋。"

            # 允許的課名與老師名清單（用於約束 LLM 輸出）
            allowed_titles = [c.get('title') for c in retrieved_courses if c.get('title')]
            allowed_categories = list({c.get('category') for c in retrieved_courses if c.get('category')})
            allowed_teachers = list({
                c.get('metadata', {}).get('meta_授課教師')
                for c in retrieved_courses if c.get('metadata', {}).get('meta_授課教師')
            })

            # Grounding：將課程轉為精簡、可讀的描述
            grounding_texts = []
            for course in retrieved_courses:
                course_for_text = {
                    '課程名稱': course.get('title'),
                    '大類': course.get('category'),
                    '課程介紹': course.get('description'),
                    **course.get('metadata', {})
                }
                grounding_texts.append(self.course_processor.create_searchable_text(course_for_text))

            # 對話上下文
            context = self.conversation_manager.get_conversation_context(session_id) if session_id else {}

            # 嚴格系統提示：要求回傳 JSON，課名只能從 allowed_titles 挑選，且逐字一致
            system_prompt = f"""
你是嚴謹的課程推薦助手。嚴格遵守：
1) 只能推薦我提供的課程清單中的標題（逐字一致），不得創造新課名或新課程類型；
2) 只能引用以下欄位：課程名稱（必須來自清單）、類別、授課教師、上課時間、費用、介紹；
3) 若找不到合適課程，請提出一個澄清問題，不可輸出任何課名；
4) 用繁體中文，口語但專業，簡明扼要；
5) 僅輸出 JSON（不要任何額外文字）。

澄清問題的限制：
- 只能詢問以下面向：時段（早上/下午/晚上/平日/週末）、指定老師、價格範圍、偏好類別；
- 禁止提及「線上/實體」除非提供的課程資訊中明確出現「線上」字樣；
- 禁止舉例任何未在允許清單中的課名或風格名稱（例如哈達、流瑜珈、陰瑜珈等）除非該名稱就出現在允許清單中；

【允許的課程名稱（只能從此清單中挑選，且需逐字一致）】
{allowed_titles}

【允許的類別（可引用）】
{allowed_categories}

【允許的老師（可引用；可能為空）】
{allowed_teachers}

請輸出以下 JSON 格式：
{{
  "intro": "對用戶需求的簡短回應",
  "recommendations": [
    {{"title": "必須是允許清單中的課名", "reason": "為何匹配"}},
    ... 最多 3 筆
  ],
  "clarify_question": "若無法完全匹配時的一句澄清問題（否則可為空字串）"
}}
"""

            # 構建使用者訊息（包含查詢、對話重點與課程資料）
            parts = [f"用戶查詢: {query}", "相關課程資訊："]
            for i, text in enumerate(grounding_texts, 1):
                parts.append(f"--- 課程 {i} ---\n{text}")
            user_prompt = "\n".join(parts)

            # 低溫度，要求輸出 JSON
            response = self.openai_client.chat.completions.create(
                model=self.config.MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                max_tokens=600,
                response_format={"type": "json_object"}
            )

            raw = response.choices[0].message.content.strip()
            data = json.loads(raw)

            # 後處理：只保留合法課名的推薦
            recs = data.get('recommendations', []) or []
            safe_recs = []
            titles_set = set(allowed_titles)
            for r in recs:
                t = (r or {}).get('title', '')
                if t in titles_set:
                    safe_recs.append(r)

            # 保底策略：若模型未返回合法推薦，但我們有檢索結果，則使用檢索結果前3筆
            if not safe_recs and retrieved_courses:
                for c in retrieved_courses[:3]:
                    safe_recs.append({
                        'title': c.get('title'),
                        'reason': '與您的需求最相關，且確實存在於我們的課程資料中。'
                    })

            # 組裝最終可讀文字（並淨化所有文字避免越權用語）
            lines = []
            intro = data.get('intro') or "以下是根據您需求整理的推薦："
            banned_terms = [
                "線上", "線上課", "實體", "線下", "遠距",
                "哈達", "流瑜伽", "流瑜珈", "陰瑜伽", "陰瑜珈", "阿斯坦加", "艾揚格", "熱瑜珈"
            ]
            for bt in banned_terms:
                if bt in intro:
                    intro = intro.replace(bt, "")
            lines.append(f"🤖 {intro}")

            if safe_recs:
                for idx, r in enumerate(safe_recs[:3], 1):
                    title = r.get('title')
                    reason = r.get('reason') or "這堂課與您的需求高度相符。"
                    for bt in banned_terms:
                        if bt in reason:
                            reason = reason.replace(bt, "")
                    # 取出該課的其他資訊輔助展示（非必須）
                    matched = next((c for c in retrieved_courses if c.get('title') == title), None)
                    extra = []
                    if matched:
                        cat = matched.get('category')
                        teacher = matched.get('metadata', {}).get('meta_授課教師')
                        time_ = matched.get('metadata', {}).get('meta_上課時間')
                        fee = matched.get('metadata', {}).get('meta_課程費用')
                        if cat: extra.append(f"類別：{cat}")
                        if teacher: extra.append(f"老師：{teacher}")
                        if time_: extra.append(f"時間：{time_}")
                        if fee: extra.append(f"費用：{fee}")
                    details = (" • " + "；".join(extra)) if extra else ""
                    lines.append(f"\n⭐ 推薦 {idx}：{title}{details}\n• 理由：{reason}")
            else:
                clarify = data.get('clarify_question') or "您是否接受不同的上課時段（早上/晚上），或有偏好的授課教師與價格範圍？"
                if any(bt in clarify for bt in banned_terms):
                    clarify = "您是否接受不同的上課時段（早上/晚上），或有偏好的授課教師與價格範圍？"
                lines.append("目前沒有找到完全匹配的課程。")
                lines.append(f"👉 {clarify}")

            text = "\n".join(lines).strip()
            logger.info(f"生成推薦完成，長度: {len(text)} 字符")
            return text
            
        except Exception as e:
            logger.error(f"生成課程推薦失敗: {e}")
            return "抱歉，生成推薦時發生錯誤。請稍後再試。"
    
    def get_course_recommendation(self, query: str, k: int = None, session_id: str = None) -> Dict[str, Any]:
        """獲取課程推薦（Top‑K 流程）：檢索 Top‑K → 交給 AI 生成口語化推薦"""
        try:
            logger.info(f"開始處理查詢 (Top-K): {query}")

            # 記錄用戶查詢
            if session_id:
                self.conversation_manager.add_message(session_id, "user_query", query)

            # 1) 檢索 Top‑K 相關課程
            topk = k or self.config.RETRIEVAL_K
            retrieved_courses = self.retrieve_relevant_courses(query, topk)

            # 1.1) 依用語中的時段字樣做二次過濾（例如：早上/下午/晚上）
            def parse_time_ok(t: str, bucket: str) -> bool:
                try:
                    if not t:
                        return False
                    hh, mm = t.split(":")
                    mins = int(hh) * 60 + int(mm)
                    if bucket == 'morning':  # 00:00–11:59
                        return mins < 12 * 60
                    if bucket == 'afternoon':  # 12:00–17:59
                        return 12 * 60 <= mins < 18 * 60
                    if bucket == 'evening':  # 18:00–23:59
                        return mins >= 18 * 60
                    return True
                except:
                    return False

            q = query or ""
            bucket = None
            if '下午' in q:
                bucket = 'afternoon'
            elif any(w in q for w in ['早上', '上午']):
                bucket = 'morning'
            elif '晚上' in q:
                bucket = 'evening'

            filtered_courses = []
            if bucket:
                for c in retrieved_courses:
                    t = c.get('metadata', {}).get('meta_上課時間')
                    if parse_time_ok(t, bucket):
                        filtered_courses.append(c)
                # 若有符合時段的課，採用過濾後的集合
                if filtered_courses:
                    retrieved_courses = filtered_courses

            # 2) 生成推薦（僅基於檢索到的結果）
            recommendation = self.generate_course_recommendation(query, retrieved_courses, session_id)

            # 3) 記錄系統回應與課程
            if session_id:
                self.conversation_manager.add_message(
                    session_id,
                    "system_response",
                    recommendation,
                    courses=retrieved_courses
                )

            return {
                'query': query,
                'retrieved_courses': retrieved_courses,
                'recommendation': recommendation,
                'success': True,
                'session_id': session_id
            }

        except Exception as e:
            logger.error(f"獲取課程推薦失敗 (Top-K): {e}")
            return {
                'query': query,
                'retrieved_courses': [],
                'recommendation': f"系統發生錯誤: {str(e)}",
                'success': False
            }
    
    def get_courses_by_category(self, category: str, limit: int = None) -> List[Dict[str, Any]]:
        """根據類別獲取課程"""
        try:
            courses = self.vector_store.get_courses_by_category(category, limit)
            
            # 如果返回空結果且可能是集合錯誤，嘗試重建
            if not courses:
                stats = self.vector_store.get_collection_stats()
                if stats.get('total_courses', 0) == 0:
                    logger.info("知識庫似乎有問題，嘗試重建...")
                    self.initialize_knowledge_base(force_rebuild=True, check_updates=False)
                    # 重新嘗試獲取
                    courses = self.vector_store.get_courses_by_category(category, limit)
            
            return courses
        except Exception as e:
            logger.error(f"根據類別獲取課程失敗: {e}")
            # 如果出現集合不存在的錯誤，嘗試重建
            if "does not exists" in str(e) or "Collection" in str(e):
                logger.info("檢測到集合錯誤，嘗試重建知識庫...")
                try:
                    self.initialize_knowledge_base(force_rebuild=True, check_updates=False)
                    # 重新嘗試獲取
                    return self.vector_store.get_courses_by_category(category, limit)
                except Exception as rebuild_error:
                    logger.error(f"重建後仍然失敗: {rebuild_error}")
            return []
    
    def get_all_categories(self) -> List[str]:
        """獲取所有課程類別"""
        try:
            return self.course_processor.get_course_categories()
        except Exception as e:
            logger.error(f"獲取課程類別失敗: {e}")
            return []
    
    def get_system_stats(self) -> Dict[str, Any]:
        """獲取系統統計資訊"""
        try:
            vector_stats = self.vector_store.get_collection_stats()
            categories = self.get_all_categories()
            
            # 獲取資料檔案資訊
            data_file_info = self._get_data_file_info()
            
            return {
                'total_courses': vector_stats.get('total_courses', 0),
                'total_categories': len(categories),
                'categories': categories,
                'collection_name': vector_stats.get('collection_name', ''),
                'model_name': self.config.MODEL_NAME,
                'embedding_model': self.config.EMBEDDING_MODEL,
                'data_file_last_modified': data_file_info.get('last_modified', '未知'),
                'data_file_size': data_file_info.get('size', 0),
                'last_update_check': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            logger.error(f"獲取系統統計失敗: {e}")
            return {}
    
    def _should_update_data(self) -> bool:
        """檢查是否需要更新資料"""
        try:
            if not os.path.exists(self.config.COURSE_DATA_PATH):
                logger.warning(f"資料檔案不存在: {self.config.COURSE_DATA_PATH}")
                return False
            
            current_mtime = os.path.getmtime(self.config.COURSE_DATA_PATH)
            
            # 如果是第一次檢查，先檢查知識庫是否有資料
            if self.last_data_file_mtime is None:
                stats = self.vector_store.get_collection_stats()
                if stats.get('total_courses', 0) == 0:
                    # 知識庫為空，需要載入資料
                    logger.info("知識庫為空，需要載入資料")
                    self.last_data_file_mtime = current_mtime
                    return True
                else:
                    # 知識庫有資料，記錄檔案時間
                    self.last_data_file_mtime = current_mtime
                    return False
            
            # 檢查檔案是否已更新
            if current_mtime > self.last_data_file_mtime:
                logger.info(f"檔案已更新，舊時間: {datetime.fromtimestamp(self.last_data_file_mtime)}, "
                           f"新時間: {datetime.fromtimestamp(current_mtime)}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"檢查檔案更新失敗: {e}")
            return False
    
    def _update_file_mtime(self):
        """更新檔案修改時間記錄"""
        try:
            if os.path.exists(self.config.COURSE_DATA_PATH):
                self.last_data_file_mtime = os.path.getmtime(self.config.COURSE_DATA_PATH)
                logger.debug(f"更新檔案修改時間記錄: {datetime.fromtimestamp(self.last_data_file_mtime)}")
        except Exception as e:
            logger.error(f"更新檔案修改時間失敗: {e}")
    
    def _get_data_file_info(self) -> Dict[str, Any]:
        """獲取資料檔案資訊"""
        try:
            if not os.path.exists(self.config.COURSE_DATA_PATH):
                return {'last_modified': '檔案不存在', 'size': 0}
            
            mtime = os.path.getmtime(self.config.COURSE_DATA_PATH)
            size = os.path.getsize(self.config.COURSE_DATA_PATH)
            
            return {
                'last_modified': datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S"),
                'size': f"{size / 1024:.1f} KB"
            }
        except Exception as e:
            logger.error(f"獲取檔案資訊失敗: {e}")
            return {'last_modified': '錯誤', 'size': 0}
    
    def check_and_reload_if_updated(self) -> Dict[str, Any]:
        """檢查並重新載入更新的資料"""
        try:
            if self._should_update_data():
                logger.info("檢測到資料更新，開始重新載入...")
                self.initialize_knowledge_base(force_rebuild=True, check_updates=False)
                return {
                    'updated': True,
                    'message': '資料已成功更新',
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            else:
                return {
                    'updated': False,
                    'message': '資料無更新',
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
        except Exception as e:
            logger.error(f"檢查和重新載入失敗: {e}")
            return {
                'updated': False,
                'message': f'錯誤: {str(e)}',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
    
    def chat_with_user(self, session_id: str, user_message: str) -> Dict[str, Any]:
        """聊天功能 - 處理用戶的聊天消息"""
        try:
            # 記錄用戶原始消息
            self.conversation_manager.add_message(session_id, "user_message", user_message)

            # 結合對話歷史，生成一個更豐富的查詢
            refined_query = self.conversation_manager.get_refined_query(session_id, user_message)
            logger.info(f"原始查詢: '{user_message}', 上下文優化後查詢: '{refined_query}'")

            # 使用優化後的查詢來判斷是否與課程相關
            is_course_query = self._is_course_related_query(refined_query)
            
            if is_course_query:
                # 如果是課程相關查詢，使用 get_course_recommendation 進行處理
                logger.info(f"使用 get_course_recommendation 處理課程問題: {refined_query}")
                
                # 呼叫我們修改過的 RAG 函式
                # 注意: get_course_recommendation 內部已經記錄了 user_query，所以這裡不用重複記錄
                recommendation_result = self.get_course_recommendation(refined_query, session_id=session_id)
                
                ai_response = recommendation_result['recommendation']
                courses = recommendation_result['retrieved_courses']
                
                # 注意：推薦和訊息記錄已在 get_course_recommendation 內部完成，此處無需重複
            else:
                # 如果是一般聊天，使用原有的聊天回應生成邏輯
                context = self.conversation_manager.get_conversation_context(session_id)
                ai_response = self._generate_chat_response(user_message, context)
                courses = []
                
                # 記錄AI回應
                self.conversation_manager.add_message(
                    session_id, "ai_response", ai_response, courses=courses
                )
            
            return {
                'success': True,
                'ai_response': ai_response,
                'courses': courses,
                'is_course_query': is_course_query
            }
            
        except Exception as e:
            logger.error(f"聊天處理失敗: {e}")
            error_response = "抱歉，我遇到了一些問題。請稍後再試。"
            
            # 記錄錯誤回應
            self.conversation_manager.add_message(session_id, "ai_response", error_response)
            
            return {
                'success': False,
                'ai_response': error_response,
                'courses': [],
                'is_course_query': False
            }
    
    def _get_course_recommendation_for_chat(self, user_message: str, session_id: str) -> Dict[str, Any]:
        """專門用於聊天的課程推薦方法"""
        try:
            # 記錄用戶消息為聊天消息
            self.conversation_manager.add_message(session_id, "user_message", user_message)
            
            # 獲取對話上下文並優化查詢
            refined_query = self.conversation_manager.get_refined_query(session_id, user_message)
            
            # 檢索相關課程
            retrieved_courses = self.retrieve_relevant_courses(refined_query)
            
            if not retrieved_courses:
                recommendation = "抱歉，我找不到符合您需求的課程。請嘗試用不同的關鍵字搜尋，例如：'有氧運動'、'瑜珈'、'游泳'、'球類運動'等。"
            else:
                # 生成推薦
                recommendation = self.generate_course_recommendation(user_message, retrieved_courses, session_id)
            
            # 記錄AI回應為聊天回應
            self.conversation_manager.add_message(
                session_id, "ai_response", recommendation, courses=retrieved_courses
            )
            
            return {
                'recommendation': recommendation,
                'retrieved_courses': retrieved_courses,
                'success': len(retrieved_courses) > 0
            }
            
        except Exception as e:
            logger.error(f"聊天課程推薦失敗: {e}")
            return {
                'recommendation': "抱歉，我遇到了一些問題。請稍後再試。",
                'retrieved_courses': [],
                'success': False
            }
    
    def _is_course_related_query(self, message: str) -> bool:
        """判斷消息是否與課程相關（積極模式，較容易觸發檢索）。"""
        if not message:
            return False
        msg = str(message)

        # 1) 類別/課程關鍵字（包含單字「課」與更廣義的類別詞）
        def _split_env_list(value: str) -> list:
            return [x.strip() for x in (value or '').split(',') if x.strip()]

        category_keywords = _split_env_list(self.config.COURSE_TRIGGER_KEYWORDS)
        if any(k in msg for k in category_keywords):
            return True

        # 2) 觸發動詞（學/學習/想學/想上/想報名/想參加）
        intent_verbs = _split_env_list(self.config.COURSE_TRIGGER_VERBS)
        if any(v in msg for v in intent_verbs):
            return True

        # 3) 時段/星期信號 + 類別/課程意圖的組合
        time_signals = _split_env_list(self.config.COURSE_TRIGGER_TIME_SIGNALS)
        week_signals = _split_env_list(self.config.COURSE_TRIGGER_WEEK_SIGNALS)
        if (any(t in msg for t in time_signals) or any(w in msg for w in week_signals)) and \
           any(k in msg for k in ['課', '上課', '課程', '瑜珈', '有氧', '游泳', '健身', '運動']):
            return True

        # 4) 課程代碼信號（英數混合碼）
        try:
            if hasattr(self, 'vector_store') and self.vector_store:
                codes = self.vector_store._extract_course_codes(msg)
                if codes:
                    return True
        except Exception:
            pass

        return False
    
    def _generate_chat_response(self, user_message: str, context: Dict[str, Any]) -> str:
        """生成聊天回應（非課程查詢時）。嚴禁捏造課程/風格/線上實體等資訊。"""
        try:
            # 構建聊天提示（非課程情境下，禁止提及具體課名/老師/風格/線上實體）
            system_prompt = """你是一個友善的AI課程推薦助手，現在是一般聊天情境：
1) 不要提及、舉例或推薦任何具體的課程名稱、老師姓名、課程風格（如哈達/流/陰瑜珈等）或上課型態（線上/實體）。
2) 若對方主動詢問課程，請引導他簡述需求（時段/星期/老師/價格/類別），並說明你將根據「我們場館的現有課程」來推薦；在未檢索前仍不要說任何具體課名。
3) 用繁體中文、自然友善、簡短回應。
4) 如果話題與課程無關，就正常閒聊，但避免產出可能被誤解為我們場館提供的服務/課程資訊。
"""

            # 構建對話歷史
            chat_history = []
            if context.get('messages'):
                recent_messages = context['messages'][-6:]  # 最近6條消息
                for msg in recent_messages:
                    if msg['type'] == 'user_message':
                        chat_history.append(f"用戶: {msg['content']}")
                    elif msg['type'] == 'ai_response':
                        chat_history.append(f"助手: {msg['content']}")
            
            # 構建完整提示
            conversation_context = "\n".join(chat_history) if chat_history else "這是對話的開始。"
            
            user_prompt = f"""
            對話歷史:
            {conversation_context}

            用戶剛剛說: {user_message}

            請根據對話歷史給出適當的回應。如果用戶在詢問課程相關問題，可以引導他們使用更具體的描述來獲得課程推薦。
            """

            # 呼叫GPT
            response = self.openai_client.chat.completions.create(
                model=self.config.MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=300,
                top_p=0.9
            )
            
            text = response.choices[0].message.content.strip()
            # 最後防呆：移除常見禁詞，避免誤導
            banned_terms = [
                "線上", "線上課", "實體", "線下", "遠距",
                "哈達", "流瑜伽", "流瑜珈", "陰瑜伽", "陰瑜珈", "阿斯坦加", "艾揚格", "熱瑜珈"
            ]
            for bt in banned_terms:
                if bt in text:
                    text = text.replace(bt, "")
            return text
            
        except Exception as e:
            logger.error(f"生成聊天回應失敗: {e}")
            return "我好像有點不太明白，可以換個方式說嗎？或者告訴我您想了解什麼樣的課程？"
    
    def handle_user_feedback(self, session_id: str, feedback_content: str, 
                           feedback_type: str = "dissatisfied", 
                           rejected_courses: List[str] = None,
                           reasons: List[str] = None) -> Dict[str, Any]:
        """處理用戶反饋"""
        try:
            # 記錄反饋
            success = self.conversation_manager.add_user_feedback(
                session_id, feedback_type, feedback_content, 
                rejected_courses, reasons
            )
            
            if not success:
                return {
                    'success': False,
                    'message': '記錄反饋失敗',
                    'followup_questions': []
                }
            
            # 記錄反饋消息
            self.conversation_manager.add_message(session_id, "user_feedback", feedback_content)
            
            # 生成追問問題
            followup_questions = self.conversation_manager.generate_followup_questions(
                session_id, feedback_content
            )
            
            return {
                'success': True,
                'message': '感謝您的反饋！',
                'followup_questions': followup_questions,
                'should_ask_followup': len(followup_questions) > 0
            }
            
        except Exception as e:
            logger.error(f"處理用戶反饋失敗: {e}")
            return {
                'success': False,
                'message': f'處理反饋時發生錯誤: {str(e)}',
                'followup_questions': []
            }
    
    def create_conversation_session(self, user_id: str = None) -> str:
        """創建新的對話會話"""
        return self.conversation_manager.create_session(user_id)
    
    def get_conversation_history(self, session_id: str) -> Dict[str, Any]:
        """獲取對話歷史"""
        return self.conversation_manager.get_conversation_context(session_id)
    
    def clear_conversation(self, session_id: str):
        """清空對話歷史"""
        self.conversation_manager.clear_session(session_id)
    
    def process_user_query_for_existing_message(self, session_id: str, user_message: str) -> Dict[str, Any]:
        """處理已存在的用戶消息 - NOW USES RAG"""
        try:
            is_course_query = self._is_course_related_query(user_message)
            
            if is_course_query:
                logger.info(f"使用 get_course_recommendation 處理課程問題: {user_message}")
                
                # 呼叫我們修改過的 RAG 函式
                recommendation_result = self.get_course_recommendation(user_message, session_id=session_id)
                
                ai_response = recommendation_result['recommendation']
                courses = recommendation_result['retrieved_courses']
                
                # 注意：推薦和訊息記錄已在 get_course_recommendation 內部完成
            else:
                context = self.conversation_manager.get_conversation_context(session_id)
                ai_response = self._generate_chat_response(user_message, context)
                courses = []
                # 為非課程相關的回應記錄訊息
                self.conversation_manager.add_message(
                    session_id, "ai_response", ai_response, courses=courses
                )
            
            return {
                'success': True,
                'ai_response': ai_response,
                'courses': courses,
                'is_course_query': is_course_query
            }
            
        except Exception as e:
            logger.error(f"處理用戶查詢失敗: {e}")
            error_response = "抱歉，我遇到了一些問題。請稍後再試。"
            self.conversation_manager.add_message(session_id, "ai_response", error_response)
            return {
                'success': False,
                'ai_response': error_response,
                'courses': [],
                'is_course_query': False
            }
