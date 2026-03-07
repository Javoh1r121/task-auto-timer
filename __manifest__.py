# -*- coding: utf-8 -*-
{
    "name": "Task Auto Timer + CRM Integration",
    "version": "19.0.3.0.0",
    "category": "Project",
    "summary": "Auto stage-based timers, CTO test tracking, time reports & CRM-to-Project in one click",
    "description": """
Task Auto Timer automatically tracks time spent on project tasks based on stage transitions.
A dedicated CTO Test Timer records testing time and labor cost separately.
Full reporting, CRM integration, and all settings configurable without code.
    """,
    "author": "Javahir Odoo developer ",
    "website": "https://www.sferaacademy.uz/",
    "license": "LGPL-3",
    "price": 0,
    "currency": "USD",
    "depends": ["project", "crm"],
    "data": [
        "security/ir.model.access.csv",
        "views/settings_views.xml",
        "views/project_task_views.xml",
        "views/report_views.xml",
        "views/menu_views.xml",
        "views/crm_lead_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "task_auto_timer/static/src/css/timer.css",
            "task_auto_timer/static/src/js/timer_widget.js",
        ],
    },
    "images": ["static/description/banner.png"],
    "installable": True,
    "auto_install": False,
    "application": False,
}
