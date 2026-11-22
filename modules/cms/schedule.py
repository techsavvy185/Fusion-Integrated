TASK_ROUTES = {
    "cms.send_pre_breach_reminders": {"queue": "notifications"},
    "cms.escalate_breached_complaints": {"queue": "default"},
    "cms.dispatch_notifications": {"queue": "notifications"},
}

BEAT_SCHEDULE = {
    "cms.send-pre-breach-reminders": {
        "task": "cms.send_pre_breach_reminders",
        "schedule": 300.0,
        "options": {"expires": 290},
    },
    "cms.escalate-breached-complaints": {
        "task": "cms.escalate_breached_complaints",
        "schedule": 300.0,
        "options": {"expires": 290},
    },
    "cms.dispatch-notifications": {
        "task": "cms.dispatch_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
}
