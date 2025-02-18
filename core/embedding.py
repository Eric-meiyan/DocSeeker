from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Union

class EmbeddingService:
    def __init__(self, model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2'):
        """初始化嵌入服务"""
        self.model = SentenceTransformer(model_name)
        
    def encode(self, texts: Union[str, List[str]], batch_size: int = 32) -> np.ndarray:
        """将文本转换为向量"""
        if isinstance(texts, str):
            texts = [texts]
            
        # 使用模型进行编码
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            normalize_embeddings=True
        )
        
        return embeddings 