"""
邮件通知服务
支持发送 HTML 格式邮件，用于发送投资报告、预警通知等
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """
    邮件发送服务

    支持：
    - HTML 格式邮件
    - 附件（可选）
    - 多收件人
    - 抄送/密送
    """

    _smtp_server: Optional[str] = None
    _smtp_port: Optional[int] = None
    _smtp_username: Optional[str] = None
    _smtp_password: Optional[str] = None
    _from_email: Optional[str] = None
    _initialized = False

    @classmethod
    def initialize(
        cls,
        smtp_server: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        from_email: str,
    ):
        """初始化 SMTP 配置"""
        cls._smtp_server = smtp_server
        cls._smtp_port = smtp_port
        cls._smtp_username = smtp_username
        cls._smtp_password = smtp_password
        cls._from_email = from_email
        cls._initialized = True
        logger.info(f"Email service initialized with SMTP: {smtp_server}:{smtp_port}")

    @classmethod
    def _ensure_initialized(cls):
        """确保服务已初始化，否则从环境变量加载配置"""
        if not cls._initialized:
            smtp_server = getattr(settings, "SMTP_SERVER", None)
            smtp_port = getattr(settings, "SMTP_PORT", 587)
            smtp_username = getattr(settings, "SMTP_USERNAME", None)
            smtp_password = getattr(settings, "SMTP_PASSWORD", None)
            from_email = getattr(settings, "FROM_EMAIL", None)

            if smtp_server and smtp_username and smtp_password and from_email:
                cls.initialize(
                    smtp_server=smtp_server,
                    smtp_port=smtp_port,
                    smtp_username=smtp_username,
                    smtp_password=smtp_password,
                    from_email=from_email,
                )
            else:
                logger.warning("Email service not configured. Set SMTP_* environment variables.")

    @classmethod
    async def send_email(
        cls,
        to_emails: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        cc_emails: Optional[List[str]] = None,
        bcc_emails: Optional[List[str]] = None,
        reply_to: Optional[str] = None,
    ) -> bool:
        """
        发送邮件

        Args:
            to_emails: 收件人列表
            subject: 邮件主题
            html_content: HTML 格式正文
            text_content: 纯文本正文（可选，用于不支持 HTML 的客户端）
            cc_emails: 抄送列表
            bcc_emails: 密送列表
            reply_to: 回复地址

        Returns:
            bool: 发送成功返回 True
        """
        cls._ensure_initialized()

        if not cls._initialized:
            logger.error("Email service not initialized")
            return False

        smtp_server = cls._smtp_server
        smtp_port = cls._smtp_port
        smtp_username = cls._smtp_username
        smtp_password = cls._smtp_password
        from_email = cls._from_email
        if (
            smtp_server is None
            or smtp_port is None
            or smtp_username is None
            or smtp_password is None
            or from_email is None
        ):
            logger.error("Email service config incomplete")
            return False

        try:
            # 创建邮件
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = from_email
            msg["To"] = ", ".join(to_emails)

            if cc_emails:
                msg["Cc"] = ", ".join(cc_emails)

            if reply_to:
                msg["Reply-To"] = reply_to

            # 添加纯文本版本（兼容性）
            if text_content:
                msg.attach(MIMEText(text_content, "plain", "utf-8"))
            else:
                # 从 HTML 提取纯文本（简单处理）
                import re
                plain_text = re.sub(r"<[^>]+>", "", html_content)
                msg.attach(MIMEText(plain_text, "plain", "utf-8"))

            # 添加 HTML 版本
            msg.attach(MIMEText(html_content, "html", "utf-8"))

            # 合并所有收件人
            all_recipients = to_emails + (cc_emails or []) + (bcc_emails or [])

            # 发送邮件
            if smtp_port == 465:
                # SSL 连接
                with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=15) as server:
                    server.login(smtp_username, smtp_password)
                    server.sendmail(from_email, all_recipients, msg.as_string())
            else:
                # STARTTLS 连接
                with smtplib.SMTP(smtp_server, smtp_port, timeout=15) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(smtp_username, smtp_password)
                    server.sendmail(from_email, all_recipients, msg.as_string())

            logger.info(f"Email sent successfully to {len(to_emails)} recipient(s). Subject: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    @classmethod
    async def send_welcome_email(cls, to_email: str, user_name: str) -> bool:
        """发送欢迎邮件"""
        html = f"""
        <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); padding: 30px; border-radius: 12px; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 24px;">欢迎使用 AI 股票顾问</h1>
                <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">让您的投资决策更理智</p>
            </div>

            <div style="padding: 30px 0;">
                <p style="font-size: 16px; color: #333;">尊敬的 {user_name}：</p>
                <p style="font-size: 16px; color: #555; line-height: 1.6;">
                    感谢您注册 AI 股票顾问系统！我们已准备好帮助您：
                </p>
                <ul style="color: #555; line-height: 2;">
                    <li>📊 深度 AI 股票分析</li>
                    <li>🎯 智能投资组合管理</li>
                    <li>📈 实时市场监控</li>
                    <li>🔔 个性化预警通知</li>
                </ul>
                <p style="font-size: 16px; color: #555; line-height: 1.6;">
                    点击以下按钮开始使用：
                </p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://stock.yufeng.fun"
                       style="background: #10b981; color: white; padding: 12px 40px;
                              text-decoration: none; border-radius: 8px; display: inline-block;
                              font-weight: bold; font-size: 16px;">
                        立即体验
                    </a>
                </div>
            </div>

            <div style="border-top: 1px solid #eee; padding-top: 20px; text-align: center; color: #999; font-size: 12px;">
                <p>此邮件由 AI 股票顾问系统自动发送</p>
                <p>&copy; 2026 AI Smart Investment Advisor. All rights reserved.</p>
            </div>
        </body>
        </html>
        """

        return await cls.send_email(
            to_emails=[to_email],
            subject="欢迎使用 AI 股票顾问系统！",
            html_content=html,
        )

    @classmethod
    async def send_price_alert(
        cls,
        to_email: str,
        ticker: str,
        current_price: float,
        target_price: float,
        alert_type: str,  # "ABOVE" or "BELOW"
    ) -> bool:
        """发送价格预警邮件"""
        is_above = alert_type.upper() == "ABOVE"
        emoji = "📈" if is_above else "📉"
        direction = "突破" if is_above else "跌破"
        color = "#10b981" if is_above else "#ef4444"

        html = f"""
        <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: {color}; padding: 20px; border-radius: 12px; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 20px;">{emoji} 价格预警</h1>
            </div>

            <div style="padding: 30px 0;">
                <p style="font-size: 16px; color: #333;">
                    <strong>{ticker}</strong> 已 <strong>{direction}</strong> 目标价位
                </p>

                <div style="background: #f9fafb; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                        <span style="color: #666;">当前价格</span>
                        <span style="font-size: 24px; font-weight: bold; color: #333;">${current_price:.2f}</span>
                    </div>
                    <div style="display: flex; justify-content: space-between;">
                        <span style="color: #666;">目标价格</span>
                        <span style="font-size: 20px; font-weight: bold; color: {color};">${target_price:.2f}</span>
                    </div>
                </div>

                <p style="font-size: 14px; color: #666; text-align: center;">
                    请及时查看您的持仓情况，做出相应决策。
                </p>
            </div>

            <div style="border-top: 1px solid #eee; padding-top: 20px; text-align: center; color: #999; font-size: 12px;">
                <p>您收到此邮件是因为订阅了 {ticker} 的价格预警</p>
                <p>&copy; 2026 AI Smart Investment Advisor</p>
            </div>
        </body>
        </html>
        """

        return await cls.send_email(
            to_emails=[to_email],
            subject=f"【价格预警】{ticker} {direction} ${target_price:.2f}",
            html_content=html,
        )

    @classmethod
    async def send_daily_report(
        cls,
        to_email: str,
        portfolio_summary: dict,
        top_performers: List[dict],
        market_news: List[str],
    ) -> bool:
        """发送每日持仓报告"""
        total_value = portfolio_summary.get("total_value", 0)
        total_pnl = portfolio_summary.get("total_pnl", 0)
        pnl_percent = portfolio_summary.get("pnl_percent", 0)
        pnl_color = "#10b981" if total_pnl >= 0 else "#ef4444"
        pnl_icon = "📈" if total_pnl >= 0 else "📉"

        if top_performers:
            performer_rows = "".join([
                f'<div style="display: flex; justify-content: space-between; padding: 12px;'
                f' border-bottom: 1px solid #eee; align-items: center;">'
                f'<span style="font-weight: bold; color: #333;">{item.get("ticker", "N/A")}</span>'
                f'<span style="color: #10b981; font-weight: bold;">+{item.get("pnl_percent", 0):.2f}%</span>'
                f'</div>'
                for item in top_performers[:3]
            ])
            top_performers_html = f'''
                <div style="margin: 20px 0;">
                    <h2 style="font-size: 16px; color: #333; margin-bottom: 15px;">🏆 表现最佳</h2>
                    {performer_rows}
                </div>'''
        else:
            top_performers_html = ''

        market_news_html = (
            ''.join([f'<li>{news}</li>' for news in market_news[:5]])
            if market_news
            else '<p style="color: #999; text-align: center;">暂无要闻</p>'
        )

        html = f"""
        <html>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #1f2937 0%, #111827 100%); padding: 30px; border-radius: 12px; text-align: center;">
                <h1 style="color: white; margin: 0; font-size: 20px;">📊 每日持仓报告</h1>
                <p style="color: rgba(255,255,255,0.7); margin: 10px 0 0 0; font-size: 12px;">
                    {portfolio_summary.get('date', '今日')}
                </p>
            </div>

            <div style="padding: 30px 0;">
                <!-- 总览卡片 -->
                <div style="background: #f9fafb; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <div style="font-size: 12px; color: #666; margin-bottom: 10px;">总资产</div>
                    <div style="font-size: 32px; font-weight: bold; color: #333; margin-bottom: 15px;">
                        ${total_value:,.2f}
                    </div>
                    <div style="display: flex; justify-content: center; gap: 20px;">
                        <div>
                            <div style="font-size: 12px; color: #666;">盈亏</div>
                            <div style="font-size: 18px; font-weight: bold; color: {pnl_color};">
                                {pnl_icon} ${total_pnl:,.2f}
                            </div>
                        </div>
                        <div>
                            <div style="font-size: 12px; color: #666;">收益率</div>
                            <div style="font-size: 18px; font-weight: bold; color: {pnl_color};">
                                {pnl_icon} {pnl_percent:.2f}%
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 表现最佳持仓 -->
                {top_performers_html}

                <!-- 市场要闻 -->
                <div style="margin: 20px 0;">
                    <h2 style="font-size: 16px; color: #333; margin-bottom: 15px;">📰 市场要闻</h2>
                    <ul style="padding-left: 20px; color: #555; line-height: 1.8;">
                        {market_news_html}
                    </ul>
                </div>
            </div>

            <div style="border-top: 1px solid #eee; padding-top: 20px; text-align: center; color: #999; font-size: 12px;">
                <p>此报告由 AI 股票顾问系统自动生成</p>
                <p>&copy; 2026 AI Smart Investment Advisor</p>
            </div>
        </body>
        </html>
        """

        return await cls.send_email(
            to_emails=[to_email],
            subject=f"📊 每日持仓报告 - ${total_value:,.2f} ({'+' if total_pnl >= 0 else ''}{pnl_percent:.2f}%)",
            html_content=html,
        )


# 全局单例
email_service = EmailService()
