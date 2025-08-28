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
        - `上課週次` 欄位，週一對應'%[1]%'，週二對應'%[2]%'，以此類推。
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
        """使用GPT-4.1 mini生成課程推薦，支援對話上下文"""
        try:
            if not retrieved_courses:
                return "抱歉，我找不到符合您需求的課程。請嘗試用不同的關鍵字搜尋。"
            
            # --- RAG Grounding v2：將結構化資料轉換為文字描述，再提供給AI ---
            grounding_texts = []
            for course in retrieved_courses:
                # 使用 course_processor 的方法來創建豐富的文本描述
                # 注意：course_processor.create_searchable_text 需要的格式與我們從DB拿到的可能不同，需要適配
                # 這裡我們手動模擬一個類似的結構
                course_for_text = {
                    '課程名稱': course.get('title'),
                    '大類': course.get('category'),
                    '課程介紹': course.get('description'),
                    **course.get('metadata', {})
                }
                grounding_texts.append(self.course_processor.create_searchable_text(course_for_text))

            # --- 從檢索到的資料中動態建立許可清單 ---
            allowed_categories = list(set([c['category'] for c in retrieved_courses]))
            allowed_teachers = list(set([c['metadata'].get('meta_授課教師') for c in retrieved_courses if c['metadata'].get('meta_授課教師')]))

            grounding_prompt_part = f"""
            【最重要規則】你的所有回覆，包括你提出的問題，都必須嚴格基於我下方提供的「相關課程資訊」。
            絕對禁止提及、詢問或建議任何未在下方明確出現的課程名稱、課程類型、老師姓名或任何課程細節。
            例如，你只能在以下列表中選擇課程類別來提問：{allowed_categories}
            例如，你只能在以下列表中選擇老師來提問：{allowed_teachers}
            你的世界裡只有我給你的這些資料，不要使用任何外部知識。
            """

            # 獲取對話上下文
            context = {}
            if session_id:
                context = self.conversation_manager.get_conversation_context(session_id)
            
            # 構建系統提示
            system_prompt = f"""你是一個專業的課程推薦助手。基於提供的課程資訊和對話歷史，為用戶推薦最適合的課程。

            {grounding_prompt_part}

            其他原則：
            1. 只推薦提供的課程資訊中存在的課程，絕對不能虛構或推薦不存在的課程
            2. 根據用戶需求、對話歷史和課程匹配度進行排序推薦
            3. 考慮用戶的偏好和之前拒絕的課程
            4. 提供具體且實用的推薦理由
            5. 用繁體中文回答
            6. 格式要清晰，包含課程名稱、類別、介紹和推薦理由

            如果沒有找到完全匹配的課程，要誠實說明，並推薦最相近的替代選項。"""

            # 構建用戶查詢上下文
            context_parts = []
            context_parts.append(f"用戶查詢: {query}\n")
            
            # 添加對話歷史和用戶偏好
            if context:
                if context.get("user_preferences"):
                    context_parts.append("用戶偏好:")
                    for pref, value in context["user_preferences"].items():
                        if value:
                            pref_name = pref.replace("_sensitive", "").replace("_", " ")
                            context_parts.append(f"  -特別關注: {pref_name}")
                
                if context.get("rejected_courses"):
                    context_parts.append(f"用戶之前拒絕的課程: {len(context['rejected_courses'])} 個")
                
                if context.get("messages"):
                    recent_messages = context["messages"][-3:]  # 最近3條消息
                    context_parts.append("最近的對話:")
                    for msg in recent_messages:
                        if msg["type"] == "user_feedback":
                            context_parts.append(f"  - 用戶反饋: {msg['content']}")
            
            context_parts.append("\n相關課程資訊:")
            # 使用轉換後的文字描述作為上下文
            for i, text in enumerate(grounding_texts, 1):
                context_parts.append(f"\n--- 課程 {i} ---\n{text}")
            
            user_prompt = "\n".join(context_parts)
            user_prompt += "\n\n請根據以上課程資訊和對話歷史，為用戶提供最適合的課程推薦："
            
            # 呼叫GPT-4.1 mini
            response = self.openai_client.chat.completions.create(
                model=self.config.MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=1500,
                top_p=0.9
            )
            
            recommendation = response.choices[0].message.content.strip()
            logger.info(f"生成推薦完成，長度: {len(recommendation)} 字符")
            
            return recommendation
            
        except Exception as e:
            logger.error(f"生成課程推薦失敗: {e}")
            return "抱歉，生成推薦時發生錯誤。請稍後再試。"
    
    def get_course_recommendation(self, query: str, k: int = None, session_id: str = None) -> Dict[str, Any]:
        """獲取課程推薦（完整流程）- MODIFIED: 使用全量課程進行推薦"""
        try:
            logger.info(f"開始處理查詢 (全量模式): {query}")
            
            # 如果有會話ID，記錄用戶查詢
            if session_id:
                self.conversation_manager.add_message(session_id, "user_query", query)

            # 1. MODIFIED: 獲取所有課程，而不是檢索相關課程
            logger.info("正在加載所有課程資料...")
            # 使用 course_processor 準備好的數據格式
            all_courses = self.course_processor.prepare_for_vectorization()
            
            # 為了與 generate_course_recommendation 的輸入格式保持一致，
            # 我們手動添加一個假的 similarity_score
            courses_for_generation = []
            for course in all_courses:
                course_copy = course.copy()
                course_copy['similarity_score'] = 1.0 # 添加假的相似度分數
                courses_for_generation.append(course_copy)

            logger.info(f"已加載 {len(courses_for_generation)} 門課程送交 AI 進行分析。")

            # --- NEW: Log the data of each course being sent to the AI ---
            logger.info("--- 開始記錄本次推薦使用的所有課程資料 ---")
            for course in courses_for_generation:
                metadata = course.get('metadata', {})
                logger.info(
                    f"  - 課程: {course.get('title', 'N/A')} | "
                    f"代碼: {metadata.get('課程代碼', 'N/A')} | "
                    f"教師: {metadata.get('授課教師', 'N/A')} | "
                    f"費用: {metadata.get('課程費用', 'N/A')}"
                )
            logger.info("--- 課程資料記錄完畢 ---")
            # ---------------------------------------------------------

            if not courses_for_generation:
                return {
                    'query': query,
                    'retrieved_courses': [],
                    'recommendation': "抱歉，課程資料庫目前是空的，我無法提供任何推薦。",
                    'success': False
                }
            
            # 2. 生成推薦 (傳入所有課程)
            # 警告: 這會非常慢且昂貴
            logger.warning("正在將所有課程發送給 AI，這可能會很慢且昂貴。")
            recommendation = self.generate_course_recommendation(query, courses_for_generation, session_id)
            
            # 記錄系統回應
            if session_id:
                self.conversation_manager.add_message(
                    session_id, "system_response", recommendation, 
                    courses=courses_for_generation # 記錄所有課程
                )
            
            return {
                'query': query,
                # 在 retrieved_courses 中返回所有課程，以便調試
                'retrieved_courses': courses_for_generation,
                'recommendation': recommendation,
                'success': True,
                'session_id': session_id
            }
            
        except Exception as e:
            logger.error(f"獲取課程推薦失敗 (全量模式): {e}")
            return {
                'query': query,
                'retrieved_courses': [],
                'recommendation': f"系統發生錯誤 (全量模式): {str(e)}",
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
        """判斷消息是否與課程相關"""
        course_keywords = [
            '課程', '推薦', '學習', '教學', '訓練', '班級', '報名', '上課',
            '減肥', '瑜珈', '游泳', '健身', '運動', '舞蹈', '音樂', '繪畫',
            '語言', '電腦', '程式', '設計', '攝影', '烹飪', '手工', '才藝'
        ]
        
        return any(keyword in message for keyword in course_keywords)
    
    def _generate_chat_response(self, user_message: str, context: Dict[str, Any]) -> str:
        """生成聊天回應"""
        try:
            # 構建聊天提示
            system_prompt = """你是一個友善的AI課程推薦助手。你可以：
1. 推薦和介紹各種課程
2. 回答關於課程的問題  
3. 進行日常聊天
4. 記住對話歷史並保持連貫性

請用繁體中文回應，保持友善和專業的語調。如果用戶沒有明確要求課程推薦，可以進行一般對話，但要適時引導到課程相關話題。"""

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
                temperature=0.8,
                max_tokens=800,
                top_p=0.9
            )
            
            return response.choices[0].message.content.strip()
            
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
