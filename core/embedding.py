from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Union
from utils.logger import Logger

class EmbeddingService:
    def __init__(self, model_name: str = 'paraphrase-multilingual-MiniLM-L12-v2'):
        """初始化嵌入服务"""
        self.logger = Logger.get_logger(__name__)
        self.logger.info("初始化嵌入服务，使用模型: %s", model_name)
        self.model = SentenceTransformer(model_name)
        
    def encode(self, texts: Union[str, List[str]], batch_size: int = 32) -> np.ndarray:
        """将文本转换为向量"""
        self.logger.debug("开始文本编码，批大小: %d", batch_size)
        if isinstance(texts, str):
            texts = [texts]
            
        self.logger.debug("待编码文本数量: %d", len(texts))
        # 使用模型进行编码
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            normalize_embeddings=True
        )
        
        self.logger.debug("编码完成，生成向量数量: %d", len(embeddings))
        return embeddings 