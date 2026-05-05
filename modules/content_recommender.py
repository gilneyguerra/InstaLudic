"""Content recommender: weekly topic suggestions based on lead distribution + benchmark."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from modules.utils import get_logger, load_config, safe

log = get_logger("casa_ludic.content")

OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"

TOPIC_LIBRARY: dict[str, list[str]] = {
    "psicologia": [
        "Sinais de ansiedade infantil que pais precisam reconhecer",
        "Como conversar com seu filho sobre emoções",
        "Quando procurar terapia infantil: 5 sinais",
    ],
    "fonoaudiologia": [
        "Atrasos de fala: o que é normal por idade",
        "Como estimular a linguagem em casa",
        "Gagueira infantil: mitos e verdades",
    ],
    "fisioterapia": [
        "Marcos do desenvolvimento motor por idade",
        "Postura escolar: cuidados em casa",
        "Crianças e atividade física: o que recomenda a OMS",
    ],
    "musicalizacao": [
        "Música e desenvolvimento cerebral infantil",
        "Como a musicalização ajuda crianças autistas",
        "Atividades musicais para fazer em casa",
    ],
    "psicopedagogia": [
        "Dificuldades de aprendizagem: como identificar",
        "Rotina de estudos para crianças do fundamental",
        "Dislexia: sinais e quando buscar avaliação",
    ],
    "terapia_ocupacional": [
        "Integração sensorial: o que é e quando ajuda",
        "Coordenação motora fina: atividades em casa",
        "TO no autismo: ganhos práticos",
    ],
    "indefinido": [
        "Conheça a Casa Ludic: depoimento de famílias",
        "A importância do atendimento multidisciplinar infantil",
    ],
}

FORMAT_TIPS = {
    "reels": "Foco em alcance e descoberta - vídeos curtos com hook forte",
    "carousel": "Conteúdo educativo profundo - constrói autoridade técnica",
    "static": "Provas sociais, depoimentos e CTAs diretos para agendamento",
}


@safe(default=None, log_name="casa_ludic.content")
def suggest_topics(db: Any, path: Path | None = None) -> Path | None:
    """Scheduler job 7: gera sugestoes ponderadas por servicos com mais leads recentes."""
    cfg = load_config().get("content_strategy", {"reels_pct": 60, "carousel_pct": 25, "static_pct": 15})
    by_service = db.kpis().get("by_service", {})
    total = sum(by_service.values()) or 1

    services_ordered = sorted(by_service.items(), key=lambda kv: kv[1], reverse=True) or [("indefinido", 1)]

    suggestions: list[dict[str, Any]] = []
    formats = [
        ("reels", int(cfg.get("reels_pct", 60))),
        ("carousel", int(cfg.get("carousel_pct", 25))),
        ("static", int(cfg.get("static_pct", 15))),
    ]
    for fmt, pct in formats:
        for svc, count in services_ordered[:3]:
            topics = TOPIC_LIBRARY.get(svc, TOPIC_LIBRARY["indefinido"])
            for t in topics[:2]:
                suggestions.append({
                    "format": fmt,
                    "service": svc,
                    "topic": t,
                    "share_target_pct": pct,
                    "leads_share_pct": round(count / total * 100, 1),
                    "tip": FORMAT_TIPS[fmt],
                })

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "strategy": cfg,
        "lead_distribution": by_service,
        "suggestions": suggestions,
    }
    path = Path(path) if path else OUTPUTS_DIR / "content_suggestions.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("Sugestoes de conteudo geradas: %s (%d itens)", path, len(suggestions))
    return path
