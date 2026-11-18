from __future__ import annotations

from datetime import timezone
from html import escape
from typing import Optional

from ..config import Config
from ..models import User
from .email_service import TRANSACTIONAL, EmailContent, SesEmailService, first_name_for


class SubscriptionEmailService:
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.email_service = SesEmailService(self.config)

    @property
    def is_configured(self) -> bool:
        return self.email_service.is_configured

    async def send_subscribed_email(self, user: User) -> dict:
        content = self._build_subscribed_email(user)
        return await self.email_service.send_email(user.email, content)

    async def send_unsubscribed_email(self, user: User) -> dict:
        content = self._build_unsubscribed_email(user)
        return await self.email_service.send_email(user.email, content)

    async def send_cancellation_scheduled_email(self, user: User) -> dict:
        content = self._build_cancellation_scheduled_email(user)
        return await self.email_service.send_email(user.email, content)

    def _build_cancellation_scheduled_email(self, user: User) -> EmailContent:
        if user.subscription_cancel_at is None:
            raise ValueError("A scheduled cancellation date is required")
        first_name = self._first_name_for(user)
        end_date = user.subscription_cancel_at.astimezone(timezone.utc).strftime(
            "%B %d, %Y at %H:%M UTC"
        )
        paragraphs = [
            "Your WeberslinkClip cancellation is scheduled. Thanks for giving us a try.",
            "What would have made WeberslinkClip more useful to you? Just hit reply—a quick note "
            "about what was missing or what got in your way would mean a lot.",
            "If a clip didn't turn out as expected or you got stuck somewhere, tell us "
            "what happened. We'd be happy to take a look.",
        ]
        closing = (
            f"P.S. Your subscription won't renew, and you'll keep access to your current plan "
            f"until {end_date}. You can undo the cancellation in Settings before then."
        )
        return EmailContent(
            subject="A quick question about your WeberslinkClip experience",
            reply_to=("hassan@weberslink.org",),
            category=TRANSACTIONAL,
            html=(
                f"<p>Hey {escape(first_name)},</p>"
                + "".join(f"<p>{escape(paragraph)}</p>" for paragraph in paragraphs)
                + "<p>Best,<br>Team WeberslinkClip</p>"
                + f"<p>{escape(closing)}</p>"
            ),
            text=(
                f"Hey {first_name},\n\n"
                + "\n\n".join(paragraphs)
                + f"\n\nBest,\nTeam WeberslinkClip\n\n{closing}"
            ),
        )

    def _build_subscribed_email(self, user: User) -> EmailContent:
        first_name = self._first_name_for(user)
        return EmailContent(
            subject="Thanks for subscribing to WeberslinkClip",
            html=(
                f"<p>Hi {first_name},</p>"
                "<p>Thanks for subscribing to WeberslinkClip.</p>"
                "<p>Your paid plan is now active, and you can jump back in anytime to create more clips.</p>"
                "<p>We’re excited to have you with us.</p>"
                "<p>Team WeberslinkClip</p>"
            ),
            text=(
                f"Hi {first_name},\n\n"
                "Thanks for subscribing to WeberslinkClip.\n\n"
                "Your paid plan is now active, and you can jump back in anytime to create more clips.\n\n"
                "We’re excited to have you with us.\n\n"
                "Team WeberslinkClip"
            ),
        )

    def _build_unsubscribed_email(self, user: User) -> EmailContent:
        first_name = self._first_name_for(user)
        return EmailContent(
            subject="Sorry to see you go from WeberslinkClip",
            html=(
                f"<p>Hi {first_name},</p>"
                "<p>Sorry to see you go, and thanks for trying WeberslinkClip.</p>"
                "<p>Your subscription has been canceled. If you ever want to come back, we’d love to have you.</p>"
                "<p>Team WeberslinkClip</p>"
            ),
            text=(
                f"Hi {first_name},\n\n"
                "Sorry to see you go, and thanks for trying WeberslinkClip.\n\n"
                "Your subscription has been canceled. If you ever want to come back, we’d love to have you.\n\n"
                "Team WeberslinkClip"
            ),
        )

    @staticmethod
    def _first_name_for(user: User) -> str:
        return first_name_for(first_name=user.first_name, full_name=user.name)
