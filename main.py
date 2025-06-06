from datetime import datetime
from typing import Any, Dict

import aiohttp
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register


@register("send_message_to_gotify", "malphitee", "监听指定用户消息并转发到 Gotify", "1.0.0")
class GotifyForwarderPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.session = None
        
    async def initialize(self):
        """插件初始化方法"""
        # 创建 HTTP 客户端会话
        self.session = aiohttp.ClientSession()
        
        # 验证配置
        if not self.config.get("gotify_server") or not self.config.get("gotify_token"):
            logger.warning("Gotify 转发插件：未配置 Gotify 服务器地址或令牌，插件将不会工作")
        else:
            logger.info("Gotify 转发插件：初始化成功")
    
    async def terminate(self):
        """插件销毁方法"""
        if self.session:
            await self.session.close()
        logger.info("Gotify 转发插件：已停止")
    
    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        """监听所有消息事件"""
        try:
            # 检查基础配置
            if not self._check_config():
                return
                
            # 获取发送者 ID
            sender_id = event.get_sender_id()
            
            # 检查是否为监听的用户
            if not self._is_monitored_user(sender_id):
                return
            
            # 获取消息内容
            message_content = event.message_str
            if not message_content.strip():
                return  # 忽略空消息
            
            # 应用过滤规则
            if not self._should_forward_message(message_content):
                if self.config.get("enable_logging", True):
                    logger.info(f"Gotify 转发插件：消息被过滤规则拦截 - 用户：{sender_id}")
                return
            
            # 构建转发消息
            forwarded_message = self._build_message(event, message_content)
            
            # 发送到 Gotify
            success = await self._send_to_gotify(forwarded_message)
            
            if success and self.config.get("enable_logging", True):
                logger.info(f"Gotify 转发插件：成功转发消息 - 用户：{sender_id}")
                
        except Exception as e:
            logger.error(f"Gotify 转发插件：处理消息时发生错误：{e}")
    
    def _check_config(self) -> bool:
        """检查配置是否有效"""
        gotify_server = self.config.get("gotify_server", "").strip()
        gotify_token = self.config.get("gotify_token", "").strip()
        monitored_users = self.config.get("monitored_users", [])
        
        if not gotify_server or not gotify_token:
            return False
            
        if not monitored_users:
            return False
            
        return True
    
    def _is_monitored_user(self, sender_id: str) -> bool:
        """检查是否为监听的用户"""
        monitored_users = self.config.get("monitored_users", [])
        return sender_id in [str(user_id) for user_id in monitored_users]
    
    def _should_forward_message(self, message_content: str) -> bool:
        """检查消息是否应该转发（根据过滤规则）"""
        filter_config = self.config.get("filter_keywords", {})
        
        # 如果未启用过滤，则转发所有消息
        if not filter_config.get("enable_filter", False):
            return True
        
        message_lower = message_content.lower()
        
        # 检查排除关键词
        exclude_keywords = filter_config.get("exclude_keywords", [])
        for keyword in exclude_keywords:
            if keyword.lower() in message_lower:
                return False
        
        # 检查包含关键词
        include_keywords = filter_config.get("include_keywords", [])
        if include_keywords:
            # 如果设置了包含关键词，消息必须包含其中至少一个
            for keyword in include_keywords:
                if keyword.lower() in message_lower:
                    return True
            return False  # 没有匹配到任何包含关键词
        
        return True
    
    def _build_message(self, event: AstrMessageEvent, message_content: str) -> Dict[str, Any]:
        """构建要发送的消息"""
        # 获取基本信息
        sender_name = event.get_sender_name()
        sender_id = event.get_sender_id()
        platform = event.get_platform_name()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 获取模板配置
        template_config = self.config.get("message_template", {})
        title_template = template_config.get("title_template", "来自 {sender_name} 的消息")
        message_template = template_config.get("message_template", 
                                             "发送者：{sender_name}\n时间：{timestamp}\n内容：{message_content}")
        
        # 构建变量字典
        variables = {
            "sender_name": sender_name,
            "user_id": sender_id,
            "message_content": message_content,
            "timestamp": timestamp,
            "platform": platform
        }
        
        # 应用模板
        try:
            title = title_template.format(**variables)
            message = message_template.format(**variables)
        except KeyError as e:
            logger.error(f"Gotify 转发插件：模板变量错误：{e}")
            # 使用默认格式
            title = f"来自 {sender_name} 的消息"
            message = f"发送者：{sender_name}\n时间：{timestamp}\n内容：{message_content}"
        
        return {
            "title": title,
            "message": message,
            "priority": self.config.get("gotify_priority", 5)
        }
    
    async def _send_to_gotify(self, message_data: Dict[str, Any]) -> bool:
        """发送消息到 Gotify"""
        try:
            gotify_server = self.config.get("gotify_server").rstrip('/')
            gotify_token = self.config.get("gotify_token")
            
            url = f"{gotify_server}/message"
            params = {"token": gotify_token}
            
            async with self.session.post(url, params=params, json=message_data) as response:
                if response.status == 200:
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Gotify 转发插件：发送失败，状态码：{response.status}，响应：{error_text}")
                    return False
                    
        except aiohttp.ClientError as e:
            logger.error(f"Gotify 转发插件：网络请求失败：{e}")
            return False
        except Exception as e:
            logger.error(f"Gotify 转发插件：发送到 Gotify 时发生未知错误：{e}")
            return False
    
    @filter.command("gotify_test")
    async def test_gotify(self, event: AstrMessageEvent):
        """测试 Gotify 连接的指令"""
        if not self._check_config():
            yield event.plain_result("❌ Gotify 配置不完整，请检查配置")
            return
        
        # 构建测试消息
        test_message = {
            "title": "AstrBot Gotify 插件测试",
            "message": f"测试消息发送成功！\n时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n发送者：{event.get_sender_name()}",
            "priority": 5
        }
        
        success = await self._send_to_gotify(test_message)
        
        if success:
            yield event.plain_result("✅ Gotify 测试消息发送成功！")
        else:
            yield event.plain_result("❌ Gotify 测试消息发送失败，请检查配置和网络连接")
    
    @filter.command("gotify_status") 
    async def check_status(self, event: AstrMessageEvent):
        """查看插件状态的指令"""
        status_lines = []
        status_lines.append("📊 Gotify 转发插件状态")
        status_lines.append("=" * 30)
        
        # 检查配置
        gotify_server = self.config.get("gotify_server", "").strip()
        gotify_token = self.config.get("gotify_token", "").strip()
        monitored_users = self.config.get("monitored_users", [])
        
        status_lines.append(f"🌐 Gotify 服务器：{gotify_server if gotify_server else '未配置'}")
        status_lines.append(f"🔑 Token 状态：{'已配置' if gotify_token else '未配置'}")
        status_lines.append(f"👥 监听用户数量：{len(monitored_users)}")
        
        if monitored_users:
            status_lines.append(f"📝 监听用户列表：{', '.join(map(str, monitored_users))}")
        
        # 过滤设置
        filter_config = self.config.get("filter_keywords", {})
        if filter_config.get("enable_filter", False):
            status_lines.append("🔍 关键词过滤：已启用")
            include_kw = filter_config.get("include_keywords", [])
            exclude_kw = filter_config.get("exclude_keywords", [])
            if include_kw:
                status_lines.append(f"   ✅ 包含关键词：{', '.join(include_kw)}")
            if exclude_kw:
                status_lines.append(f"   ❌ 排除关键词：{', '.join(exclude_kw)}")
        else:
            status_lines.append("🔍 关键词过滤：已禁用")
        
        status_lines.append(f"📊 消息优先级：{self.config.get('gotify_priority', 5)}")
        status_lines.append(f"📝 详细日志：{'已启用' if self.config.get('enable_logging', True) else '已禁用'}")
        
        yield event.plain_result("\n".join(status_lines))
