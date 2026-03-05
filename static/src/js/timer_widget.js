/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, onMounted, onWillUnmount, useRef, xml } from "@odoo/owl";

const WORK_START = 9;
const WORK_END = 19;

function workSec(startMs, endMs) {
  let t = 0;
  for (let i = startMs; i < endMs; i += 60000) {
    const d = new Date(i);
    if (d.getDay() === 0) continue;
    if (d.getHours() < WORK_START || d.getHours() >= WORK_END) continue;
    t += Math.min(60000, endMs - i);
  }
  return t / 1000;
}

function hms(sec) {
  const s = Math.max(0, Math.floor(sec));
  return [Math.floor(s / 3600), Math.floor((s % 3600) / 60), s % 60]
    .map((v) => String(v).padStart(2, "0"))
    .join(":");
}

function hoursHms(h) {
  return hms(Math.round((h || 0) * 3600));
}

function durStr(sec) {
  const s = Math.round(sec);
  return `${Math.floor(s / 3600)}h ${String(Math.floor((s % 3600) / 60)).padStart(2, "0")}m ${String(s % 60).padStart(2, "0")}s`;
}

// ── Timer Display ─────────────────────────────────────────────
class TimerDisplayField extends Component {
  static template = xml`<div t-ref="root"/>`;
  static props = { ...standardFieldProps };

  setup() {
    this.rootRef = useRef("root");
    this._iv = null;
    onMounted(() => {
      this._render();
      this._iv = setInterval(() => this._render(), 1000);
    });
    onWillUnmount(() => {
      if (this._iv) clearInterval(this._iv);
    });
  }

  _render() {
    const el = this.rootRef.el;
    if (!el) return;
    const d = this.props.record.data;
    let html = "";

    if (d.timer_running && d.timer_start) {
      const ms =
        d.timer_start instanceof Date
          ? d.timer_start.getTime()
          : new Date(d.timer_start).getTime();
      const sec =
        workSec(ms, Date.now()) + Math.round((d.timer_accumulated || 0) * 3600);
      html = `<span style="display:inline-flex;align-items:center;border-radius:50px;
                padding:4px 14px;background:#28a745;color:#fff;font-size:15px;
                font-family:monospace;font-weight:600;box-shadow:0 2px 8px rgba(40,167,69,.3);margin-right:8px;">
                <i class="fa fa-circle" style="font-size:9px;margin-right:6px;animation:tat_blink 1s infinite;"></i>
                ${hms(sec)}</span>`;
    } else if (d.timer_paused) {
      html = `<span style="display:inline-flex;align-items:center;border-radius:50px;
                padding:4px 14px;background:#fd7e14;color:#fff;font-size:15px;
                font-family:monospace;font-weight:600;margin-right:8px;">
                <i class="fa fa-pause" style="margin-right:6px;"></i>
                ${hoursHms(d.timer_accumulated)}</span>`;
    } else if (d.total_duration > 0) {
      html = `<span style="display:inline-flex;align-items:center;border-radius:50px;
                padding:4px 14px;background:#dc3545;color:#fff;font-size:15px;
                font-family:monospace;font-weight:600;margin-right:8px;">
                <i class="fa fa-clock-o" style="margin-right:6px;"></i>
                ${hoursHms(d.total_duration)}</span>`;
    }
    el.innerHTML = html;
  }
}

// ── Test Timer Display ────────────────────────────────────────
class TestTimerDisplayField extends Component {
  static template = xml`<div t-ref="root"/>`;
  static props = { ...standardFieldProps };

  setup() {
    this.rootRef = useRef("root");
    this._iv = null;
    onMounted(() => {
      this._render();
      this._iv = setInterval(() => this._render(), 500);
    });
    onWillUnmount(() => {
      if (this._iv) clearInterval(this._iv);
    });
  }

  _render() {
    const el = this.rootRef.el;
    if (!el) return;
    const d = this.props.record.data;
    let html = "";

    if (d.test_timer_running && d.test_timer_start) {
      const ms =
        d.test_timer_start instanceof Date
          ? d.test_timer_start.getTime()
          : new Date(d.test_timer_start).getTime();
      const elapsed_sec = (Date.now() - ms) / 1000;
      const total_sec =
        Math.round((d.test_timer_accumulated || 0) * 3600) + elapsed_sec;
      html = `<span style="display:inline-flex;align-items:center;gap:6px;padding:6px 14px;
                background:#28a745;color:#fff;border-radius:50px;font-weight:600;font-size:13px;
                box-shadow:0 2px 8px rgba(40,167,69,.3);">
                <i class="fa fa-circle" style="font-size:9px;animation:tat_blink 1s infinite;"></i>
                <span style="font-family:monospace;">TEST: ${hms(total_sec)}</span>
              </span>`;
    } else if (d.test_labor_cost >= 0 && d.test_timer_accumulated > 0) {
      const test_hours = d.test_timer_accumulated || 0;
      html = `<span style="display:inline-flex;align-items:center;gap:6px;padding:6px 14px;
                background:#dc3545;color:#fff;border-radius:50px;font-weight:600;font-size:13px;
                box-shadow:0 2px 8px rgba(220,53,69,.3);">
                <i class="fa fa-clock-o"></i>
                <span style="font-family:monospace;">TEST: ${hoursHms(test_hours)}</span>
              </span>`;
    }
    el.innerHTML = html;
  }
}

// ── Sessions Display ──────────────────────────────────────────
class SessionsField extends Component {
  static template = xml`<div t-ref="root"/>`;
  static props = { ...standardFieldProps };

  setup() {
    this.rootRef = useRef("root");
    onMounted(() => this._render());
  }

  _render() {
    const el = this.rootRef.el;
    if (!el) return;

    let sessions = [];
    try {
      sessions = JSON.parse(this.props.record.data.timer_sessions || "[]");
    } catch (e) {}

    if (!sessions.length) {
      el.innerHTML = `<div style="text-align:center;padding:40px;color:#adb5bd;">
                <i class="fa fa-clock-o" style="font-size:36px;display:block;margin-bottom:10px;"></i>
                <span style="font-size:14px;">No sessions yet</span></div>`;
      return;
    }

    const totalSec = sessions.reduce(
      (s, r) => s + Math.round(r.duration * 3600),
      0,
    );
    const th = Math.floor(totalSec / 3600);
    const tm = Math.floor((totalSec % 3600) / 60);

    const rows = sessions
      .map((s, i) => {
        const bg = i % 2 === 0 ? "#fff" : "#f9fafb";
        return `<tr style="background:${bg}">
                <td style="padding:8px 14px;color:#adb5bd;">${i + 1}</td>
                <td style="padding:8px 14px;"><span style="background:#6c757d22;color:#495057;
                    border:1px solid #6c757d44;border-radius:12px;padding:2px 10px;
                    font-size:12px;font-weight:600;">${s.stage || "-"}</span></td>
                <td style="padding:8px 14px;font-size:13px;color:#495057;">
                    ${new Date(s.stopped_at).toLocaleString()}</td>
                <td style="padding:8px 14px;"><span style="background:#dc354520;color:#dc3545;
                    border:1px solid #dc354555;border-radius:20px;padding:3px 12px;
                    font-family:monospace;font-size:13px;font-weight:600;">
                    ${durStr(s.duration * 3600)}</span></td>
              </tr>`;
      })
      .join("");

    el.innerHTML = `<div style="max-width:700px;">
            <table style="width:100%;border-collapse:collapse;border-radius:8px;overflow:hidden;
                box-shadow:0 1px 6px rgba(0,0,0,.08);">
                <thead><tr style="background:#f1f3f5;border-bottom:2px solid #dee2e6;">
                    <th style="padding:9px 14px;text-align:left;font-size:11px;color:#6c757d;font-weight:700;text-transform:uppercase;">#</th>
                    <th style="padding:9px 14px;text-align:left;font-size:11px;color:#6c757d;font-weight:700;text-transform:uppercase;">Stage</th>
                    <th style="padding:9px 14px;text-align:left;font-size:11px;color:#6c757d;font-weight:700;text-transform:uppercase;">Stopped at</th>
                    <th style="padding:9px 14px;text-align:left;font-size:11px;color:#6c757d;font-weight:700;text-transform:uppercase;">Duration</th>
                </tr></thead>
                <tbody>${rows}</tbody>
                <tfoot><tr style="background:#f8f9fa;border-top:2px solid #dee2e6;">
                    <td colspan="3" style="padding:10px 14px;font-weight:700;font-size:13px;color:#495057;">
                        Total (${sessions.length} sessions)</td>
                    <td style="padding:10px 14px;"><span style="background:#28a745;color:#fff;
                        border-radius:20px;padding:3px 14px;font-family:monospace;
                        font-size:13px;font-weight:700;">
                        ${th}h ${String(tm).padStart(2, "00")}m</span></td>
                </tr></tfoot>
            </table></div>`;
  }
}

// ── Test Timer Sessions Display ───────────────────────────────
class TestSessionsField extends Component {
  static template = xml`<div t-ref="root"/>`;
  static props = { ...standardFieldProps };

  setup() {
    this.rootRef = useRef("root");
    onMounted(() => this._render());
  }

  _render() {
    const el = this.rootRef.el;
    if (!el) return;

    let sessions = [];
    try {
      sessions = JSON.parse(this.props.record.data.test_timer_sessions || "[]");
    } catch (e) {}

    if (!sessions.length) {
      el.innerHTML = `<div style="text-align:center;padding:40px;color:#adb5bd;">
                <i class="fa fa-hourglass-start" style="font-size:36px;display:block;margin-bottom:10px;"></i>
                <span style="font-size:14px;">Test jarayoni boshlanmagan</span></div>`;
      return;
    }

    const totalSec = sessions.reduce(
      (s, r) => s + Math.round(r.duration * 3600),
      0,
    );
    const totalCost = sessions.reduce((s, r) => s + (r.cost || 0), 0);
    const th = Math.floor(totalSec / 3600);
    const tm = Math.floor((totalSec % 3600) / 60);

    const rows = sessions
      .map((s, i) => {
        const bg = i % 2 === 0 ? "#fff" : "#f9fafb";
        const wage = s.wage || 0;
        const cost = s.cost || 0;
        return `<tr style="background:${bg}">
                <td style="padding:10px 14px;color:#adb5bd;font-weight:600;">${i + 1}</td>
                <td style="padding:10px 14px;font-size:13px;color:#495057;">
                    ${new Date(s.stopped_at).toLocaleString()}</td>
                <td style="padding:10px 14px;"><span style="background:#dc354520;color:#dc3545;
                    border:1px solid #dc354555;border-radius:20px;padding:4px 12px;
                    font-family:monospace;font-size:13px;font-weight:600;">
                    ${durStr(s.duration * 3600)}</span></td>
                <td style="padding:10px 14px;font-size:12px;color:#6c757d;font-family:monospace;">
                    $${wage.toFixed(2)}/hr</td>
                <td style="padding:10px 14px;"><span style="background:#28a745;color:#fff;
                    border-radius:20px;padding:4px 12px;font-family:monospace;font-size:13px;font-weight:600;">
                    💰 $${cost.toFixed(2)}</span></td>
              </tr>`;
      })
      .join("");

    el.innerHTML = `<div style="max-width:900px;">
            <table style="width:100%;border-collapse:collapse;border-radius:8px;overflow:hidden;
                box-shadow:0 1px 6px rgba(0,0,0,.08);">
                <thead><tr style="background:#dc3545;border-bottom:2px solid #dc3545;">
                    <th style="padding:12px 14px;text-align:left;font-size:11px;color:#fff;font-weight:700;text-transform:uppercase;">#</th>
                    <th style="padding:12px 14px;text-align:left;font-size:11px;color:#fff;font-weight:700;text-transform:uppercase;">Tugallangan vaqt</th>
                    <th style="padding:12px 14px;text-align:left;font-size:11px;color:#fff;font-weight:700;text-transform:uppercase;">Davomiyligi</th>
                    <th style="padding:12px 14px;text-align:left;font-size:11px;color:#fff;font-weight:700;text-transform:uppercase;">CTO Stavka</th>
                    <th style="padding:12px 14px;text-align:left;font-size:11px;color:#fff;font-weight:700;text-transform:uppercase;">Xarajat</th>
                </tr></thead>
                <tbody>${rows}</tbody>
                <tfoot><tr style="background:#f8f9fa;border-top:2px solid #dee2e6;">
                    <td colspan="2" style="padding:12px 14px;font-weight:700;font-size:13px;color:#495057;">
                        Jami (${sessions.length} sessiya)</td>
                    <td style="padding:12px 14px;"><span style="background:#dc3545;color:#fff;
                        border-radius:20px;padding:4px 12px;font-family:monospace;
                        font-size:13px;font-weight:700;">
                        ${th}h ${String(tm).padStart(2, "0")}m</span></td>
                    <td colspan="2" style="padding:12px 14px;"><span style="background:#28a745;color:#fff;
                        border-radius:20px;padding:4px 14px;font-family:monospace;
                        font-size:13px;font-weight:700;">
                        💰 $${totalCost.toFixed(2)}</span></td>
                </tr></tfoot>
            </table></div>`;
  }
}

// ── Registry ──────────────────────────────────────────────────
registry.category("fields").add("timer_display", {
  component: TimerDisplayField,
  supportedTypes: ["boolean"],
});
registry.category("fields").add("timer_sessions_display", {
  component: SessionsField,
  supportedTypes: ["text"],
});
registry.category("fields").add("test_timer_display", {
  component: TestTimerDisplayField,
  supportedTypes: ["boolean"],
});
registry.category("fields").add("test_timer_sessions_display", {
  component: TestSessionsField,
  supportedTypes: ["text"],
});
