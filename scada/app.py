
"""
Generic ICS SCADA Server — Historian, Trends, and Reporting.

Sits above the HMIs in the architecture. Discovers all PLCs/sensors,
continuously logs readings to a historian database, and provides
trend charts, daily reports, and event logging.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
from datetime import datetime, date
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, url_for

from .device_client import DeviceClient, DeviceState
from .historian import (
    get_db_stats,
    get_daily_summaries,
    get_events,
    get_trend_data,
    generate_daily_summary,
    log_event,
    log_readings_batch,
    prune_old_readings,
)
from .metadata import DataType
from .models import (
    AlarmConfig,
    audit,
    get_alarm_config,
    get_all_alarm_configs,
    get_audit_log,
    set_alarm_config,
)

logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("SCADA_SECRET", "scada-default-key")

# Global state
client: DeviceClient = None
_poll_thread: threading.Thread = None
_running = False

POLL_INTERVAL = float(os.environ.get("SCADA_POLL_INTERVAL", "2.0"))
RESCAN_INTERVAL = int(os.environ.get("SCADA_RESCAN_INTERVAL", "120"))
HISTORIAN_RETENTION_HOURS = int(os.environ.get("SCADA_RETENTION_HOURS", "48"))
SCENARIOS_DIR = Path("/app/scenarios")


# --- Template filters ---

@app.template_filter("ts")
def format_timestamp(ts):
    if ts is None:
        return "—"
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


@app.template_filter("val")
def format_value(val):
    if val is None:
        return "—"
    if isinstance(val, bool):
        return "ON" if val else "OFF"
    if isinstance(val, float):
        return f"{val:.2f}"
    return str(val)


# --- Alarm status helper ---

def get_alarm_status(tag: str, value) -> str:
    if value is None:
        return "stale"
    if not isinstance(value, (int, float)):
        return "normal"
    config = get_alarm_config(tag)
    if config is None or not config.enabled:
        return "normal"
    if config.high_high is not None and value >= config.high_high:
        return "hihi"
    if config.high is not None and value >= config.high:
        return "high"
    if config.low_low is not None and value <= config.low_low:
        return "lolo"
    if config.low is not None and value <= config.low:
        return "low"
    return "normal"


# --- Diagram config (loaded from scenario file, optional) ---

_diagram_config: dict = {}  # Maps PLC tag → {template, name}


def _load_diagram_config():
    """Load diagram config from scenario file."""
    global _diagram_config
    import yaml

    config_file = os.environ.get("SCADA_DIAGRAM_CONFIG", "").strip()
    if not config_file:
        logger.info("No SCADA_DIAGRAM_CONFIG set — using fallback diagram view")
        return

    path = SCENARIOS_DIR / config_file
    if not path.exists():
        logger.warning("Diagram config not found: %s", path)
        return

    try:
        with path.open() as f:
            _diagram_config = yaml.safe_load(f) or {}
    except Exception as e:
        logger.error("Failed to parse %s: %s", path, e)
        return

    logger.info("Loaded diagram config: %s (template: %s)",
                _diagram_config.get("name", "unknown"),
                _diagram_config.get("template", "none"))


# --- Routes ---

@app.route("/")
def plant_diagram():
    """Main page — single full-plant P&ID diagram with all sensors."""
    # Auto-discover all sensor tags for live JS updates
    tags = []
    if client:
        for tag, device in sorted(client.devices.items()):
            if not device.is_plc:
                tags.append(tag)

    # Check if a diagram template exists for this scenario
    template_name = _diagram_config.get("template", "")
    if template_name:
        template_path = f"diagrams/{template_name}"
    else:
        template_path = "diagram_fallback.html"

    plant_name = _diagram_config.get("name", "Plant Overview")

    return render_template(template_path,
                           area={"name": plant_name},
                           area_key="plant",
                           tags=tags)


@app.route("/overview")
def overview():
    """Grid view showing auto-discovered process areas with live values."""
    groups = client.get_sensors_by_subnet() if client else {}

    areas = []
    for plc_tag, sensors in sorted(groups.items()):
        sensor_data = {}
        for s in sensors:
            sensor_data[s.tag] = {
                "value": s.value,
                "units": s.metadata.units,
                "online": s.online,
                "status": get_alarm_status(s.tag, s.value),
                "description": s.metadata.description,
            }

        subnet = "unknown"
        if sensors:
            subnet = sensors[0].ip.rsplit(".", 1)[0] + ".0/24"

        areas.append({
            "plc_tag": plc_tag,
            "name": plc_tag,
            "subnet": subnet,
            "sensor_data": sensor_data,
            "device_count": len(sensors),
        })

    return render_template("diagram_index.html", areas=areas)


@app.route("/trends")
def trends():
    sensors = []
    if client:
        for tag, device in sorted(client.devices.items()):
            if device.is_plc:
                continue
            sensors.append({
                "tag": tag,
                "description": device.metadata.description,
                "units": device.metadata.units,
                "value": device.value,
            })
    return render_template("trends.html", sensors=sensors)


@app.route("/reports")
def reports():
    date_str = request.args.get("date", date.today().isoformat())
    summaries = get_daily_summaries(date_str)
    return render_template("reports.html", summaries=summaries, selected_date=date_str)


@app.route("/reports/generate", methods=["POST"])
def generate_report():
    date_str = request.form.get("date", date.today().isoformat())
    count = generate_daily_summary(date_str)
    log_event("REPORT_GENERATED", message=f"Daily summary for {date_str}: {count} tags")
    return redirect(url_for("reports", date=date_str))



@app.route("/plc-logic")
def plc_logic_page():
    """Upload and view runtime logic YAML for discovered PLCs."""
    plcs = []
    if client:
        for plc in client.get_plcs():
            health = client.get_plc_logic_health(plc.tag)
            current_logic = client.get_plc_logic(plc.tag)
            plcs.append({
                "tag": plc.tag,
                "ip": plc.ip,
                "description": plc.metadata.description,
                "online": plc.online,
                "logic_api_ok": bool(health.get("ok")),
                "logic_api_error": health.get("error", ""),
                "rules_loaded": health.get("rules_loaded", "—"),
                "logic": current_logic or "",
            })
    return render_template("plc_logic.html", plcs=plcs)


@app.route("/plc-logic/upload", methods=["POST"])
def plc_logic_upload():
    """Upload a YAML logic file to a PLC's /logic endpoint."""
    plc_tag = request.form.get("plc_tag", "").strip()
    file = request.files.get("logic_file")

    if not client or not plc_tag or not file or not file.filename:
        log_event("PLC_LOGIC_UPLOAD_FAILED", tag=plc_tag or None,
                  message="Missing PLC or logic file")
        return redirect(url_for("plc_logic_page"))

    content = file.read()
    if len(content) > 256 * 1024:
        log_event("PLC_LOGIC_UPLOAD_FAILED", tag=plc_tag,
                  message=f"Logic file too large: {file.filename}")
        audit("PLC_LOGIC_UPLOAD_FAILED", tag=plc_tag,
              details=f"Rejected oversized logic file {file.filename}")
        return redirect(url_for("plc_logic_page"))

    ok, message = client.upload_plc_logic(plc_tag, content)
    if ok:
        log_event("PLC_LOGIC_UPLOAD", tag=plc_tag,
                  message=f"Uploaded PLC logic file {file.filename}")
        audit("PLC_LOGIC_UPLOAD", tag=plc_tag,
              details=f"Uploaded {file.filename}: {message[:200]}")
    else:
        log_event("PLC_LOGIC_UPLOAD_FAILED", tag=plc_tag,
                  message=f"Failed to upload {file.filename}: {message}")
        audit("PLC_LOGIC_UPLOAD_FAILED", tag=plc_tag,
              details=f"Failed to upload {file.filename}: {message[:200]}")

    return redirect(url_for("plc_logic_page"))

@app.route("/events")
def events_page():
    event_list = get_events(limit=200)
    return render_template("events.html", events=event_list)


@app.route("/control")
def control():
    """Sensor control panel — set manual values, toggle auto/manual mode."""
    sensors = []
    if client:
        for tag, device in sorted(client.devices.items()):
            if device.is_plc:
                continue
            mode = client.read_sensor_mode(tag)
            sensors.append({
                "tag": tag,
                "description": device.metadata.description,
                "units": device.metadata.units,
                "value": device.value,
                "online": device.online,
                "data_type": device.metadata.data_type.name,
                "mode": "MANUAL" if mode == 1 else "AUTO",
            })
    return render_template("control.html", sensors=sensors)


@app.route("/control/set-mode", methods=["POST"])
def control_set_mode():
    tag = request.form.get("tag")
    mode = request.form.get("mode", "auto")
    if tag and client:
        manual = mode == "manual"
        client.write_sensor_mode(tag, manual)
        log_event("SENSOR_MODE", tag=tag,
                  message=f"Set {tag} to {'MANUAL' if manual else 'AUTO'} mode")
        audit("SENSOR_MODE", tag=tag,
              details=f"Mode changed to {'MANUAL' if manual else 'AUTO'}")
    return redirect(url_for("control"))


@app.route("/control/set-value", methods=["POST"])
def control_set_value():
    tag = request.form.get("tag")
    value_str = request.form.get("value", "").strip()
    if tag and value_str and client:
        device = client.devices.get(tag)
        if device:
            # Parse value based on data type
            from .metadata import DataType
            dt = device.metadata.data_type
            try:
                if dt == DataType.BOOL:
                    value = value_str.lower() in ("true", "1", "on", "yes")
                elif dt == DataType.FLOAT32:
                    value = float(value_str)
                elif dt in (DataType.INT16, DataType.UINT16):
                    value = int(float(value_str))
                else:
                    value = float(value_str)

                # Set manual mode first, then write value
                client.write_sensor_mode(tag, True)
                client.write_sensor_value(tag, value)
                log_event("SENSOR_OVERRIDE", tag=tag, value=float(value_str) if dt != DataType.BOOL else (1.0 if value else 0.0),
                          message=f"Manual override: {tag} = {value}")
                audit("SENSOR_OVERRIDE", tag=tag,
                      details=f"Set {tag} = {value} (manual mode)")
            except ValueError:
                pass
    return redirect(url_for("control"))


@app.route("/control/set-auto-all", methods=["POST"])
def control_set_auto_all():
    """Return all sensors to auto/simulation mode."""
    if client:
        count = 0
        for tag, device in client.devices.items():
            if device.is_plc:
                continue
            if client.write_sensor_mode(tag, False):
                count += 1
        log_event("SENSOR_MODE", message=f"Returned {count} sensors to AUTO mode")
        audit("SENSOR_MODE_ALL", details=f"All {count} sensors returned to AUTO")
    return redirect(url_for("control"))


@app.route("/settings/upload-defaults", methods=["POST"])
def upload_alarm_defaults():
    """Upload a YAML file to replace alarm defaults."""
    import yaml
    file = request.files.get("defaults_file")
    if not file or not file.filename:
        return redirect(url_for("settings"))

    try:
        content = file.read().decode("utf-8")
        doc = yaml.safe_load(content) or {}
    except Exception as e:
        log_event("UPLOAD_FAILED", message=f"Failed to parse uploaded file: {e}")
        return redirect(url_for("settings"))

    sensors = doc.get("sensors", {})
    loaded = 0
    for tag, thresholds in sensors.items():
        new_config = AlarmConfig(
            tag=tag,
            high_high=thresholds.get("high_high"),
            high=thresholds.get("high"),
            low=thresholds.get("low"),
            low_low=thresholds.get("low_low"),
            deadband=float(thresholds.get("deadband", 1.0)),
            enabled=thresholds.get("enabled", True),
        )
        set_alarm_config(new_config)
        loaded += 1

    audit("ALARM_UPLOAD", details=f"Uploaded alarm defaults: {loaded} configs from {file.filename}")
    log_event("ALARM_UPLOAD", message=f"Loaded {loaded} alarm config(s) from uploaded file")
    return redirect(url_for("settings"))


@app.route("/settings")
def settings():
    configs = get_all_alarm_configs()
    devices = client.devices if client else {}
    sensors = []
    for tag, device in sorted(devices.items()):
        if device.is_plc:
            continue
        config = configs.get(tag)
        sensors.append({
            "tag": tag,
            "description": device.metadata.description,
            "units": device.metadata.units,
            "config": config,
        })
    return render_template("settings.html", sensors=sensors)


@app.route("/settings/update", methods=["POST"])
def update_setting():
    tag = request.form.get("tag")
    if not tag:
        return redirect(url_for("settings"))

    old_config = get_alarm_config(tag)
    old_str = _config_to_str(old_config) if old_config else "none"

    def _parse_float(key):
        val = request.form.get(key, "").strip()
        if val == "" or val.lower() == "none":
            return None
        return float(val)

    new_config = AlarmConfig(
        tag=tag,
        high_high=_parse_float("high_high"),
        high=_parse_float("high"),
        low=_parse_float("low"),
        low_low=_parse_float("low_low"),
        deadband=float(request.form.get("deadband", "1.0")),
        enabled="enabled" in request.form,
    )
    set_alarm_config(new_config)

    new_str = _config_to_str(new_config)
    audit("ALARM_CONFIG_CHANGE", tag=tag,
          details=f"Alarm settings updated for {tag}",
          old_value=old_str, new_value=new_str)

    # Push this change to all HMIs
    _push_config_to_hmis({tag: {
        "high_high": new_config.high_high,
        "high": new_config.high,
        "low": new_config.low,
        "low_low": new_config.low_low,
        "deadband": new_config.deadband,
        "enabled": new_config.enabled,
    }})

    return redirect(url_for("settings"))


@app.route("/settings/push-all", methods=["POST"])
def push_all_settings():
    """Push all current alarm configs to every HMI."""
    configs = get_all_alarm_configs()
    payload = {
        tag: {
            "high_high": c.high_high,
            "high": c.high,
            "low": c.low,
            "low_low": c.low_low,
            "deadband": c.deadband,
            "enabled": c.enabled,
        }
        for tag, c in configs.items()
    }
    results = _push_config_to_hmis(payload)
    audit("PUSH_ALL", details=f"Pushed {len(configs)} config(s) to HMIs: {results}")
    return redirect(url_for("settings"))


@app.route("/audit")
def audit_page():
    log = get_audit_log(limit=200)
    return render_template("audit.html", log=log)


@app.route("/rediscover", methods=["POST"])
def rediscover():
    before = len(client.devices)
    client.discover()
    after = len(client.devices)
    new_count = after - before
    if new_count > 0:
        log_event("DISCOVERY", message=f"Found {new_count} new device(s) ({after} total)")
        logger.info("Rediscovery found %d new device(s) (%d total)", new_count, after)
    return redirect(url_for("plant_diagram"))


# --- JSON APIs ---

@app.route("/api/sensors")
def api_sensors():
    if not client:
        return jsonify({})
    data = {}
    for tag, device in client.devices.items():
        if device.is_plc:
            continue
        data[tag] = {
            "value": device.value,
            "units": device.metadata.units,
            "online": device.online,
            "status": get_alarm_status(tag, device.value),
            "last_read": device.last_read,
        }
    return jsonify(data)


@app.route("/api/trend/<tag>")
def api_trend(tag):
    duration = request.args.get("duration", "3600", type=int)
    data = get_trend_data(tag, duration_s=duration)
    return jsonify(data)


@app.route("/api/stats")
def api_stats():
    return jsonify(get_db_stats())


@app.route("/api/thresholds/<tag>")
def api_thresholds(tag):
    """Return alarm thresholds for a sensor — used to draw lines on trend charts."""
    config = get_alarm_config(tag)
    if config is None:
        return jsonify({})
    return jsonify({
        "high_high": config.high_high,
        "high": config.high,
        "low": config.low,
        "low_low": config.low_low,
        "enabled": config.enabled,
    })


@app.route("/api/control/set-mode", methods=["POST"])
def api_control_set_mode():
    data = request.get_json()
    tag = data.get("tag")
    manual = data.get("manual", False)
    if tag and client:
        ok = client.write_sensor_mode(tag, manual)
        if ok:
            log_event("SENSOR_MODE", tag=tag,
                      message=f"{'MANUAL' if manual else 'AUTO'} mode")
        return jsonify({"ok": ok})
    return jsonify({"ok": False}), 400


@app.route("/api/control/set-value", methods=["POST"])
def api_control_set_value():
    data = request.get_json()
    tag = data.get("tag")
    value = data.get("value")
    if tag and value is not None and client:
        device = client.devices.get(tag)
        if device:
            from .metadata import DataType
            dt = device.metadata.data_type
            try:
                if dt == DataType.BOOL:
                    val = bool(value)
                elif dt == DataType.FLOAT32:
                    val = float(value)
                else:
                    val = int(float(value))
                client.write_sensor_mode(tag, True)
                ok = client.write_sensor_value(tag, val)
                if ok:
                    log_event("SENSOR_OVERRIDE", tag=tag, value=float(value),
                              message=f"Override: {tag} = {val}")
                return jsonify({"ok": ok})
            except (ValueError, TypeError):
                pass
    return jsonify({"ok": False}), 400


def _load_alarm_defaults():
    """Load default alarm thresholds from local file (fallback for first boot)."""
    import yaml
    defaults_file = os.environ.get("SCADA_ALARM_DEFAULTS", "").strip()
    if not defaults_file:
        return

    path = SCENARIOS_DIR / defaults_file
    if not path.exists():
        return

    try:
        with path.open() as f:
            doc = yaml.safe_load(f) or {}
    except Exception as e:
        logger.error("Failed to parse %s: %s", path, e)
        return

    sensors = doc.get("sensors", {})
    loaded = 0
    for tag, thresholds in sensors.items():
        existing = get_alarm_config(tag)
        if existing is not None:
            continue
        config = AlarmConfig(
            tag=tag,
            high_high=thresholds.get("high_high"),
            high=thresholds.get("high"),
            low=thresholds.get("low"),
            low_low=thresholds.get("low_low"),
            deadband=float(thresholds.get("deadband", 1.0)),
            enabled=True,
        )
        set_alarm_config(config)
        loaded += 1

    if loaded > 0:
        logger.info("Loaded %d default alarm config(s) from %s", loaded, path)


def _get_hmi_urls() -> list:
    """Parse SCADA_HMI_URLS env var into a list of URLs."""
    urls_str = os.environ.get("SCADA_HMI_URLS", "").strip()
    if not urls_str:
        return []
    return [u.strip().rstrip("/") for u in urls_str.split(",") if u.strip()]


def _push_config_to_hmis(configs: dict) -> dict:
    """Push alarm config changes to all HMIs. Returns {url: status}."""
    import urllib.request

    urls = _get_hmi_urls()
    if not urls:
        logger.debug("No SCADA_HMI_URLS configured — skipping push")
        return {}

    payload = json.dumps(configs).encode("utf-8")
    results = {}

    for base_url in urls:
        url = f"{base_url}/api/alarm_configs/update"
        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read().decode())
                results[base_url] = f"OK ({result.get('updated', 0)} updated)"
                logger.info("Pushed configs to %s: %s", base_url, result)
        except Exception as e:
            results[base_url] = f"FAILED: {e}"
            logger.warning("Failed to push configs to %s: %s", base_url, e)

    return results


def _push_all_configs_to_hmis():
    """Push all current alarm configs to all HMIs. Called periodically."""
    configs = get_all_alarm_configs()
    if not configs:
        return
    payload = {
        tag: {
            "high_high": c.high_high,
            "high": c.high,
            "low": c.low,
            "low_low": c.low_low,
            "deadband": c.deadband,
            "enabled": c.enabled,
        }
        for tag, c in configs.items()
    }
    _push_config_to_hmis(payload)


def _config_to_str(config: AlarmConfig) -> str:
    return (f"HH={config.high_high} H={config.high} "
            f"L={config.low} LL={config.low_low} "
            f"DB={config.deadband} EN={config.enabled}")


PUSH_INTERVAL = int(os.environ.get("SCADA_PUSH_INTERVAL", "60"))


# --- Background tasks ---

def _poll_loop():
    global _running
    last_rescan = time.time()
    last_prune = time.time()
    last_summary = time.time()

    while _running:
        try:
            # Poll all devices
            client.poll_all()

            # Log readings to historian
            now = time.time()
            batch = []
            for tag, device in client.devices.items():
                if device.is_plc or device.value is None:
                    continue
                batch.append((tag, device.value, now))
            if batch:
                log_readings_batch(batch)

            # Periodic re-discovery
            if now - last_rescan > RESCAN_INTERVAL:
                before = len(client.devices)
                client.discover()
                after = len(client.devices)
                if after > before:
                    logger.info("Rescan found %d new device(s)", after - before)
                    log_event("DISCOVERY", message=f"Rescan found {after - before} new device(s)")
                last_rescan = now

            # Periodic data pruning (every hour)
            if now - last_prune > 3600:
                deleted = prune_old_readings(HISTORIAN_RETENTION_HOURS)
                if deleted > 0:
                    logger.info("Pruned %d old readings (retention: %dh)", deleted, HISTORIAN_RETENTION_HOURS)
                last_prune = now

            # Daily summary generation (every 30 min)
            if now - last_summary > 1800:
                generate_daily_summary()
                last_summary = now

        except Exception as e:
            logger.exception("Poll loop error: %s", e)

        time.sleep(POLL_INTERVAL)


# --- Startup ---

def main():
    global client, _poll_thread, _running

    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
    )
    logging.getLogger("pymodbus").setLevel(logging.CRITICAL)
    logging.getLogger("pymodbus.logging").setLevel(logging.CRITICAL)

    targets_str = os.environ.get("SCADA_TARGETS", "").strip()
    subnets_str = os.environ.get("SCADA_SUBNETS", "").strip()

    targets = [t.strip() for t in targets_str.split(",") if t.strip()] if targets_str else []
    subnets = [s.strip() for s in subnets_str.split(",") if s.strip()] if subnets_str else []

    if not targets and not subnets:
        logger.warning(
            "No targets configured (SCADA_TARGETS and SCADA_SUBNETS are both unset). "
            "SCADA will start but no devices will be discovered. "
            "Set SCADA_TARGETS or SCADA_SUBNETS to connect to devices."
        )

    client = DeviceClient(targets=targets, subnets=subnets)
    logger.info("Starting device discovery...")

    startup_passes = int(os.environ.get("SCADA_STARTUP_PASSES", "3"))
    for attempt in range(startup_passes):
        client.discover()
        logger.info("Discovery pass %d/%d: %d device(s)",
                     attempt + 1, startup_passes, len(client.devices))
        if attempt < startup_passes - 1:
            time.sleep(10)

    if not client.devices:
        logger.warning("No devices discovered. SCADA will start but will be empty.")

    log_event("STARTUP", message=f"SCADA server started. {len(client.devices)} device(s) discovered.")

    # Load alarm defaults
    _load_alarm_defaults()

    # Load diagram config
    _load_diagram_config()

    _running = True
    _poll_thread = threading.Thread(target=_poll_loop, daemon=True)
    _poll_thread.start()

    port = int(os.environ.get("SCADA_PORT", "8080"))
    logger.info("SCADA web interface starting on port %d", port)
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
