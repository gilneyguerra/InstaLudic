"""Instagram monitoring via instagrapi, with mock fallback when login fails."""
from __future__ import annotations

import os
import random
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

from modules.utils import get_logger, load_config, safe

load_dotenv()
log = get_logger("casa_ludic.instagram")

SESSION_PATH = Path(__file__).resolve().parent.parent / "outputs" / "ig_session.json"


class InstagramMonitor:
    def __init__(self, db: Any) -> None:
        self.db = db
        cfg = load_config()
        self.handle = cfg.get("clinic", {}).get("instagram_handle", "casaludic")
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        user = os.getenv("IG_USER")
        password = os.getenv("IG_PASS")
        if not user or not password:
            log.warning("Credenciais Instagram ausentes - usara mock")
            return None
        try:
            from instagrapi import Client  # local import: heavy/optional
            client = Client()
            if SESSION_PATH.exists():
                try:
                    client.load_settings(str(SESSION_PATH))
                except Exception as exc:  # noqa: BLE001
                    log.warning("Sessao IG invalida, refazendo login: %s", exc)
            client.login(user, password)
            client.dump_settings(str(SESSION_PATH))
            self._client = client
            log.info("Login Instagram OK")
            return client
        except Exception as exc:  # noqa: BLE001
            log.error("Login Instagram falhou: %s", exc)
            return None

    def _mock_metrics(self) -> dict[str, Any]:
        return {
            "followers": random.randint(4600, 4800),
            "posts": random.randint(800, 820),
            "engagement": round(random.uniform(2.5, 4.5), 2),
        }

    @safe(default=False, log_name="casa_ludic.instagram")
    def sync_metrics(self) -> bool:
        client = self._get_client()
        if not client:
            data = self._mock_metrics()
            return self.db.save_instagram_metrics(
                data["followers"], data["posts"], data["engagement"], source="mock"
            )

        try:
            user_id = client.user_id_from_username(self.handle)
            info = client.user_info(user_id)
            followers = info.follower_count
            posts = info.media_count
            medias = client.user_medias(user_id, amount=10)
            if medias:
                interactions = sum((m.like_count or 0) + (m.comment_count or 0) for m in medias)
                engagement = round(interactions / max(len(medias), 1) / max(followers, 1) * 100, 2)
            else:
                engagement = 0.0
            return self.db.save_instagram_metrics(followers, posts, engagement, source="real")
        except Exception as exc:  # noqa: BLE001
            log.error("Coleta IG falhou (%s) - fallback mock", exc)
            data = self._mock_metrics()
            return self.db.save_instagram_metrics(
                data["followers"], data["posts"], data["engagement"], source="mock_fallback"
            )

    @safe(default=[], log_name="casa_ludic.instagram")
    def fetch_recent_comments(self, limit: int = 20) -> list[dict[str, Any]]:
        client = self._get_client()
        if not client:
            log.info("IG indisponivel - sem comentarios reais para capturar")
            return []
        try:
            user_id = client.user_id_from_username(self.handle)
            medias = client.user_medias(user_id, amount=5)
            comments: list[dict[str, Any]] = []
            for media in medias:
                for c in client.media_comments(media.id, amount=limit):
                    comments.append({
                        "text": c.text,
                        "username": c.user.username if c.user else "ig_user",
                        "media_id": str(media.id),
                    })
            log.info("Coletados %d comentarios IG", len(comments))
            return comments
        except Exception as exc:  # noqa: BLE001
            log.error("Falha ao coletar comentarios IG: %s", exc)
            return []

    @safe(default=0, log_name="casa_ludic.instagram")
    def capture_pending_comments(self, lead_capture: Any) -> int:
        comments = self.fetch_recent_comments()
        captured = 0
        for c in comments:
            if lead_capture.process_instagram_comment(c):
                captured += 1
        log.info("Captura de comentarios IG: %d novos leads", captured)
        return captured

    @safe(default=None, log_name="casa_ludic.instagram")
    def latest(self) -> Optional[dict[str, Any]]:
        return self.db.latest_instagram_metrics()
