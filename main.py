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
        sender_name = self._get_sender_display_name(event)
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
    
    def _get_sender_display_name(self, event: AstrMessageEvent) -> str:
        """智能获取发送者显示名称，针对不同平台进行优化"""
        try:
            # 首先尝试获取标准的发送者姓名
            sender_name = event.get_sender_name()
            
            # 如果获取到有效的姓名且不为空，直接返回
            if sender_name and sender_name.strip():
                return sender_name.strip()
            
            # 如果没有获取到姓名，尝试从原始消息对象中提取
            platform = event.get_platform_name().lower()
            sender_id = event.get_sender_id()
            
            # 根据平台特性进行特殊处理
            if platform == "telegram":
                display_name = self._get_telegram_display_name(event)
                if display_name:
                    return display_name
                    
            elif platform in ["qq", "aiocqhttp"]:
                # QQ 平台通常使用昵称或QQ号
                display_name = self._get_qq_display_name(event)
                if display_name:
                    return display_name
                    
            elif platform in ["wechat", "gewechat"]:
                # 微信平台使用微信昵称
                display_name = self._get_wechat_display_name(event)
                if display_name:
                    return display_name
            
            # 如果所有方法都无法获取姓名，使用用户ID作为后备
            return f"用户_{sender_id}" if sender_id else "未知用户"
            
        except Exception as e:
            logger.warning(f"Gotify 转发插件：获取发送者姓名时发生错误：{e}")
            return f"用户_{event.get_sender_id()}" if event.get_sender_id() else "未知用户"
    
    def _get_telegram_display_name(self, event: AstrMessageEvent) -> str:
        """获取 Telegram 用户的显示名称"""
        try:
            # 尝试从原始消息中获取用户信息
            raw_message = event.message_obj.raw_message
            
            if hasattr(raw_message, 'from_user') or isinstance(raw_message, dict):
                # 处理字典格式的原始消息
                if isinstance(raw_message, dict):
                    from_user = raw_message.get('from_user') or raw_message.get('from')
                else:
                    from_user = getattr(raw_message, 'from_user', None)
                
                if from_user:
                    # 尝试获取用户信息
                    if isinstance(from_user, dict):
                        first_name = from_user.get('first_name', '')
                        last_name = from_user.get('last_name', '')
                        username = from_user.get('username', '')
                    else:
                        first_name = getattr(from_user, 'first_name', '')
                        last_name = getattr(from_user, 'last_name', '')
                        username = getattr(from_user, 'username', '')
                    
                    # 构建显示名称
                    display_name = ''
                    if first_name:
                        display_name = first_name
                        if last_name:
                            display_name += f" {last_name}"
                    elif username:
                        display_name = f"@{username}"
                    
                    if display_name.strip():
                        return display_name.strip()
            
            # 如果无法从原始消息获取，尝试其他方法
            sender = event.message_obj.sender
            if hasattr(sender, 'nickname') and sender.nickname:
                return sender.nickname
            
            return None
            
        except Exception as e:
            logger.debug(f"Gotify 转发插件：获取 Telegram 用户信息失败：{e}")
            return None
    
    def _get_qq_display_name(self, event: AstrMessageEvent) -> str:
        """获取 QQ 用户的显示名称"""
        try:
            sender = event.message_obj.sender
            
            # 尝试获取昵称、群名片等
            if hasattr(sender, 'nickname') and sender.nickname:
                return sender.nickname
            elif hasattr(sender, 'card') and sender.card:
                return sender.card
            elif hasattr(sender, 'title') and sender.title:
                return sender.title
                
            # 如果都没有，返回QQ号
            sender_id = event.get_sender_id()
            if sender_id:
                return f"QQ用户_{sender_id}"
                
            return None
            
        except Exception as e:
            logger.debug(f"Gotify 转发插件：获取 QQ 用户信息失败：{e}")
            return None
    
    def _get_wechat_display_name(self, event: AstrMessageEvent) -> str:
        """获取微信用户的显示名称"""
        try:
            sender = event.message_obj.sender
            
            # 尝试获取微信昵称
            if hasattr(sender, 'nickname') and sender.nickname:
                return sender.nickname
            elif hasattr(sender, 'remark') and sender.remark:
                return sender.remark
                
            # 尝试从原始消息获取
            raw_message = event.message_obj.raw_message
            if isinstance(raw_message, dict):
                name = raw_message.get('sender_name') or raw_message.get('nickname')
                if name:
                    return name
                    
            return None
            
        except Exception as e:
            logger.debug(f"Gotify 转发插件：获取微信用户信息失败：{e}")
            return None
    
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

    @filter.command("gotify_debug")
    async def debug_message_info(self, event: AstrMessageEvent):
        """调试指令：查看消息事件的详细信息"""
        try:
            debug_info = []
            debug_info.append("🐞 Gotify 插件调试信息")
            debug_info.append("=" * 30)
            
            # 基本信息
            debug_info.append(f"平台：{event.get_platform_name()}")
            debug_info.append(f"发送者ID：{event.get_sender_id()}")
            debug_info.append(f"标准获取姓名：{repr(event.get_sender_name())}")
            debug_info.append(f"智能获取姓名：{repr(self._get_sender_display_name(event))}")
            
            # 发送者对象信息
            sender = event.message_obj.sender
            debug_info.append("\n📋 发送者对象信息：")
            debug_info.append(f"发送者对象类型：{type(sender)}")
            
            if hasattr(sender, '__dict__'):
                for attr, value in sender.__dict__.items():
                    debug_info.append(f"  {attr}: {repr(value)}")
            else:
                debug_info.append("  发送者对象无 __dict__ 属性")
            
            # 原始消息信息
            raw_message = event.message_obj.raw_message
            debug_info.append("\n📄 原始消息信息：")
            debug_info.append(f"原始消息类型：{type(raw_message)}")
            
            if isinstance(raw_message, dict):
                debug_info.append("原始消息内容（部分）：")
                for key in ['from_user', 'from', 'sender_name', 'nickname', 'user_id', 'chat']:
                    if key in raw_message:
                        debug_info.append(f"  {key}: {repr(raw_message[key])}")
            elif hasattr(raw_message, '__dict__'):
                debug_info.append("原始消息属性（部分）：")
                for attr in ['from_user', 'from', 'sender_name', 'nickname', 'user_id']:
                    if hasattr(raw_message, attr):
                        value = getattr(raw_message, attr)
                        debug_info.append(f"  {attr}: {repr(value)}")
            
            # Telegram 特殊处理
            if event.get_platform_name().lower() == "telegram":
                debug_info.append("\n💬 Telegram 特殊信息：")
                try:
                    if isinstance(raw_message, dict):
                        from_user = raw_message.get('from_user') or raw_message.get('from')
                        if from_user:
                            debug_info.append(f"  from_user/from: {repr(from_user)}")
                            if isinstance(from_user, dict):
                                for key in ['id', 'first_name', 'last_name', 'username', 'language_code']:
                                    if key in from_user:
                                        debug_info.append(f"    {key}: {repr(from_user[key])}")
                except Exception as e:
                    debug_info.append(f"  获取 Telegram 信息时出错: {e}")
            
            result = "\n".join(debug_info)
            
            # 限制输出长度，避免消息过长
            if len(result) > 4000:
                result = result[:4000] + "\n...(信息过长，已截断)"
                
            yield event.plain_result(result)
            
        except Exception as e:
            yield event.plain_result(f"❌ 调试信息获取失败：{e}")
