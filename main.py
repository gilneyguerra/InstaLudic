"""Casa Ludic CRM core: launches the 24/7 scheduler with 7 jobs."""
from __future__ import annotations

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from modules.analytics import Analytics
from modules.content_recommender import suggest_topics
from modules.database import Database
from modules.instagram_monitor import InstagramMonitor
from modules.lead_capture import LeadCapture
from modules.lead_qualification import requalify_pending
from modules.outreach import OutreachEngine
from modules.utils import EMOJI, get_logger

log = get_logger("casa_ludic.main")


def build_scheduler(db: Database) -> BlockingScheduler:
    capture = LeadCapture(db)
    ig = InstagramMonitor(db)
    outreach = OutreachEngine(db)
    analytics = Analytics(db)

    sched = BlockingScheduler(timezone="America/Sao_Paulo")

    sched.add_job(ig.sync_metrics, CronTrigger(hour="*/6", minute=0),
                  id="job1_ig_metrics", name="Sync Instagram metrics")
    sched.add_job(ig.capture_pending_comments, CronTrigger(minute="*/30"),
                  args=[capture], id="job2_ig_comments", name="Capture comments -> leads")
    sched.add_job(requalify_pending, CronTrigger(minute=0),
                  args=[db], id="job3_qualify", name="Qualify pending leads")
    sched.add_job(outreach.run_hot_outreach, CronTrigger(hour="9,14,18", minute=0),
                  id="job4_outreach_hot", name="Outreach hot leads")
    sched.add_job(outreach.run_warm_followup, CronTrigger(day_of_week="mon,wed,fri", hour=10, minute=0),
                  id="job5_outreach_warm", name="Outreach warm follow-up")
    sched.add_job(analytics.daily_report, CronTrigger(hour=8, minute=0),
                  id="job6_analytics", name="Daily analytics PDF + HTML")
    sched.add_job(suggest_topics, CronTrigger(day_of_week="mon", hour=9, minute=0),
                  args=[db], id="job7_content", name="Weekly content suggestions")

    return sched


def main() -> None:
    log.info("%s Iniciando Casa Ludic CRM", EMOJI["info"])
    db = Database()
    sched = build_scheduler(db)

    log.info("%s %d jobs agendados", EMOJI["info"], len(sched.get_jobs()))
    for job in sched.get_jobs():
        log.info("  - %s | next_run=%s", job.name, job.next_run_time)
    print(f"{EMOJI['ok']} Scheduler ativo - {len(sched.get_jobs())} jobs (Ctrl+C para encerrar)")

    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Shutdown solicitado")
        sched.shutdown(wait=False)
        db.close()
        print(f"{EMOJI['ok']} Encerrado")


if __name__ == "__main__":
    main()
