#!/bin/bash

echo "=== 修復 huggingface_hub 兼容性問題 ==="

# 檢查是否在虛擬環境中
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "啟動虛擬環境..."
    source venv/bin/activate
fi

echo "1. 卸載有問題的套件..."
pip uninstall -y sentence-transformers huggingface_hub transformers torch

echo "2. 清理pip快取..."
pip cache purge

echo "3. 安裝兼容的版本..."
pip install torch>=2.0.0
pip install transformers>=4.35.0
pip install "huggingface_hub>=0.20.0,<1.0.0"
pip install sentence-transformers==2.7.0

echo "4. 安裝其他依賴..."
pip install --only-binary=all -r requirements.txt

echo "5. 驗證安裝..."
python3 -c "
try:
    import sentence_transformers
    import huggingface_hub
    print('✅ sentence-transformers 版本:', sentence_transformers.__version__)
    print('✅ huggingface_hub 版本:', huggingface_hub.__version__)
    
    # 測試模型載入
    from sentence_transformers import SentenceTransformer
    print('✅ 正在測試模型載入...')
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    print('✅ 模型載入成功!')
    
except Exception as e:
    print(f'❌ 錯誤: {e}')
    exit(1)
"

echo "✅ 依賴修復完成！" 