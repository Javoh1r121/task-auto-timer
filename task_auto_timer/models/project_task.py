# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime, timedelta

import pytz

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


def _get_param(env, key, default):
    val = env["ir.config_parameter"].sudo().get_param(key)
    return val if val else default


def _work_start(env):
    return int(_get_param(env, "task_auto_timer.work_start", 9))

def _work_end(env):
    return int(_get_param(env, "task_auto_timer.work_end", 19))

def _work_days(env):
    raw = _get_param(env, "task_auto_timer.work_days", "0,1,2,3,4,5")
    try:
        return {int(d.strip()) for d in raw.split(",") if d.strip()}
    except Exception:
        return {0, 1, 2, 3, 4, 5}

def _stage(env, key, default):
    return (_get_param(env, f"task_auto_timer.{key}", default) or default).lower().strip()

def _cto_job(env):
    return _get_param(env, "task_auto_timer.cto_job_title", "CTO") or "CTO"
