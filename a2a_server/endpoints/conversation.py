"""
会话管理器

维护 A2A contextId 到 Dify conversation_id 的映射，
使用 Dify Plugin Storage (KV) 进行持久化存储。
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ConversationManager:
    """
    会话管理器
    维护 A2A contextId 到 Dify conversation_id 的映射
    
    使用 Dify Plugin Storage (KV) 进行持久化存储
    参考文档：https://docs.dify.ai/develop-plugin/features-and-specs/plugin-types/persistent-storage-kv
    """
    
    KEY_PREFIX = "conv"
    
    def __init__(self, session, app_id: str):
        """
        初始化会话管理器
        
        Args:
            session: Dify Plugin Session，用于访问存储
            app_id: Dify App ID，用于隔离不同 App 的会话
        """
        self.session = session
        self.app_id = app_id
    
    def _build_key(self, context_id: str) -> str:
        """构建存储键 - 格式: conv:{app_id}:{context_id}"""
        return f"{self.KEY_PREFIX}:{self.app_id}:{context_id}"
    
    def get_dify_conversation_id(self, a2a_context_id: str) -> Optional[str]:
        """
        根据 A2A contextId 获取 Dify conversation_id
        
        Args:
            a2a_context_id: A2A 协议的 contextId
            
        Returns:
            Dify conversation_id，如果不存在返回 None
        """
        if not a2a_context_id:
            return None
        
        key = self._build_key(a2a_context_id)
        try:
            # get() 返回 bytes 或 None
            value_bytes = self.session.storage.get(key)
            if value_bytes:
                # 解码 bytes 为字符串
                value = value_bytes.decode('utf-8')
                logger.debug(f"Found conversation mapping: {a2a_context_id} -> {value}")
                return value
            else:
                # 新会话，还没有映射记录
                logger.debug(f"No conversation mapping found for: {a2a_context_id}")
        except Exception as e:
            # 只记录 debug，因为新会话获取失败是正常的
            logger.debug(f"No conversation mapping (new session): {e}")
        
        return None
    
    def save_dify_conversation_id(
        self, 
        a2a_context_id: str, 
        dify_conversation_id: str
    ) -> bool:
        """
        保存 A2A contextId 到 Dify conversation_id 的映射
        
        Args:
            a2a_context_id: A2A 协议的 contextId
            dify_conversation_id: Dify 返回的 conversation_id
            
        Returns:
            是否保存成功
        """
        if not a2a_context_id or not dify_conversation_id:
            return False
        
        key = self._build_key(a2a_context_id)
        try:
            # set() 的值必须是 bytes 格式
            self.session.storage.set(key, dify_conversation_id.encode('utf-8'))
            logger.info(f"Saved conversation mapping: {a2a_context_id} -> {dify_conversation_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to save conversation mapping: {e}")
            return False
    
    def delete_conversation_mapping(self, a2a_context_id: str) -> bool:
        """删除会话映射（可选，用于清理）"""
        if not a2a_context_id:
            return False
        
        key = self._build_key(a2a_context_id)
        try:
            self.session.storage.delete(key)
            logger.info(f"Deleted conversation mapping: {a2a_context_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to delete conversation mapping: {e}")
            return False
