# backend/safety_agent.py — Agentic threat response using GLM 5.1 function calling
#
# Instead of hard-coded if/else rules, the agent receives a threat situation
# and autonomously reasons about WHICH combination of actions to take and WHY.
# GLM 5.1 handles multi-step planning: assess → decide tools → execute → report.
#
# This is the core "agent" component that makes the system intelligent rather
# than just reactive.

import json
import os
import requests
import logging
from typing import Callable

log = logging.getLogger("safety-agent")

Z_AI_API_KEY = os.getenv("Z_AI_API_KEY", "YOUR_Z_AI_KEY")
Z_AI_URL = "https://api.z.ai/api/paas/v4/chat/completions"

_HEADERS = {
    "Authorization": f"Bearer {Z_AI_API_KEY}",
    "Content-Type": "application/json",
    "Accept-Language": "en-US,en",
}

# ── Tool definitions (GLM 5.1 function calling schema) ────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "trigger_alarm",
            "description": (
                "Activate the device's audible alarm (buzzer) and LED siren. "
                "Use for immediate physical deterrence when a threat is nearby."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "duration_seconds": {
                        "type": "integer",
                        "description": "How long to sound the alarm (5–60 seconds)."
                    }
                },
                "required": ["duration_seconds"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_emergency_sms",
            "description": (
                "Send an SMS to the user's emergency contacts via the GSM module. "
                "Use when WiFi may be unavailable or for critical level-4 situations."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The SMS text. Keep under 160 chars. Include key facts."
                    },
                    "include_location": {
                        "type": "boolean",
                        "description": "Append the last known GPS coordinates to the message."
                    },
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "notify_contacts",
            "description": (
                "Send a push notification via Firebase to the guardian/family app. "
                "Use for all threat levels ≥ 2 when internet is available."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Notification title."},
                    "body":  {"type": "string", "description": "Notification body."},
                    "priority": {
                        "type": "string",
                        "enum": ["normal", "high", "critical"],
                        "description": "normal=level 2, high=level 3, critical=level 4.",
                    },
                },
                "required": ["title", "body", "priority"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "capture_photo",
            "description": (
                "Command the device to take a photo immediately for evidence. "
                "Use when a weapon or aggressor has been visually detected."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Why the photo is being captured (logged with the image)."
                    }
                },
                "required": ["reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_incident",
            "description": (
                "Persist the incident to the database with full details. "
                "Always call this as the final step after taking other actions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "threat_level": {
                        "type": "integer",
                        "description": "1=normal, 2=elevated, 3=dangerous, 4=emergency SOS."
                    },
                    "description": {
                        "type": "string",
                        "description": "Plain-language summary of the incident."
                    },
                    "actions_taken": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of tool actions already executed."
                    },
                    "recommended_followup": {
                        "type": "string",
                        "description": "Suggested next step for responders."
                    },
                },
                "required": ["threat_level", "description", "actions_taken"],
            },
        },
    },
]

# ── Tool executor registry ────────────────────────────────────────────────────
# Each entry maps a tool name to a real callable.
# Swap these out with real implementations (MQTT publish, Firebase, SQLite, etc.)

_tool_registry: dict[str, Callable] = {}


def register_tool(name: str, fn: Callable) -> None:
    """Register the actual implementation for a tool name."""
    _tool_registry[name] = fn


def _execute_tool(name: str, arguments: dict) -> str:
    """Dispatch a tool call and return a string result for the model."""
    if name not in _tool_registry:
        return f"[tool not registered: {name}]"
    try:
        result = _tool_registry[name](**arguments)
        return str(result) if result is not None else "ok"
    except Exception as e:
        log.error(f"Tool {name} failed: {e}")
        return f"error: {e}"


# ── Agent loop ────────────────────────────────────────────────────────────────

def run_agent(situation: dict) -> list[dict]:
    """
    Given a threat situation dict, let GLM 5.1 autonomously decide which
    tools to call (and in what order) to respond appropriately.

    Uses GLM 5.1 function calling in a multi-turn agentic loop:
      1. Model receives situation + available tools
      2. Model returns tool_calls (one or more)
      3. We execute each tool and feed results back
      4. Model continues until it decides to stop (no more tool_calls)

    Args:
        situation: Dict with keys like threat_level, source, details,
                   sensor_data, location, history.

    Returns:
        List of action dicts recording every tool called and its result.
    """
    system_prompt = (
        "You are an autonomous safety response agent for a women's personal safety device. "
        "When a threat situation is reported, you must:\n"
        "1. Assess the severity from the available data\n"
        "2. Choose the appropriate combination of response tools\n"
        "3. Execute them in a sensible order (e.g. alarm before SMS before logging)\n"
        "4. Always end by calling log_incident to record everything\n\n"
        "Be decisive. Do not ask clarifying questions. Act immediately.\n"
        "Threat levels: 1=normal (no action), 2=elevated (notify), "
        "3=dangerous (notify+alarm), 4=emergency (all tools)."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                f"Threat situation:\n{json.dumps(situation, indent=2)}\n\n"
                "Respond using the available tools. Start now."
            ),
        },
    ]

    actions_taken = []
    max_turns = 6  # safety cap on agent iterations

    for turn in range(max_turns):
        resp = requests.post(
            Z_AI_URL,
            headers=_HEADERS,
            json={
                "model": "glm-5",
                "messages": messages,
                "tools": TOOLS,
                "tool_choice": "auto",
                "temperature": 0.2,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()

        choice = data["choices"][0]
        message = choice["message"]
        finish_reason = choice.get("finish_reason", "stop")

        # Append assistant message to history
        messages.append(message)

        tool_calls = message.get("tool_calls", [])
        if not tool_calls:
            # Model decided it's done
            log.info(f"Agent finished after {turn + 1} turn(s). Reason: {finish_reason}")
            break

        # Execute each tool call and feed results back
        for tc in tool_calls:
            fn = tc["function"]
            tool_name = fn["name"]
            tool_args = fn["arguments"] if isinstance(fn["arguments"], dict) else json.loads(fn["arguments"])

            log.info(f"[agent] calling tool: {tool_name}({tool_args})")
            result = _execute_tool(tool_name, tool_args)
            log.info(f"[agent] tool result: {result}")

            actions_taken.append({"tool": tool_name, "args": tool_args, "result": result})

            # Feed tool result back to model
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            })

    return actions_taken


# ── Default tool implementations (wire up in server.py) ──────────────────────

def make_default_tools(mqtt_client, device_tokens: dict, sqlite_conn=None):
    """
    Returns a dict of default tool implementations to register.
    Pass your live mqtt_client, Firebase device_tokens, and optional SQLite conn.
    """
    import firebase_admin
    from firebase_admin import messaging

    def trigger_alarm(duration_seconds: int = 10):
        mqtt_client.publish("safety/command", json.dumps({
            "action": "alarm",
            "duration": duration_seconds,
        }))
        return f"alarm triggered for {duration_seconds}s"

    def send_emergency_sms(message: str, include_location: bool = False):
        payload = {"action": "sms", "message": message, "location": include_location}
        mqtt_client.publish("safety/command", json.dumps(payload))
        return f"SMS queued: {message[:40]}..."

    def notify_contacts(title: str, body: str, priority: str = "high"):
        priority_map = {"normal": messaging.AndroidConfig(priority="normal"),
                        "high": messaging.AndroidConfig(priority="high"),
                        "critical": messaging.AndroidConfig(priority="high")}
        for uid, token in device_tokens.items():
            try:
                messaging.send(messaging.Message(
                    notification=messaging.Notification(title=title, body=body),
                    android=priority_map.get(priority),
                    token=token,
                ))
            except Exception as e:
                log.error(f"Push failed {uid}: {e}")
        return f"notified {len(device_tokens)} contact(s)"

    def capture_photo(reason: str = "threat detected"):
        mqtt_client.publish("safety/command", json.dumps({"action": "photo", "reason": reason}))
        return "photo command sent"

    def log_incident(threat_level: int, description: str,
                     actions_taken: list, recommended_followup: str = ""):
        from datetime import datetime
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "threat_level": threat_level,
            "description": description,
            "actions_taken": actions_taken,
            "recommended_followup": recommended_followup,
        }
        if sqlite_conn:
            sqlite_conn.execute(
                "INSERT INTO incidents VALUES (NULL,?,?,?,?,?,?)",
                (record["timestamp"], threat_level, description, None, None, None),
            )
            sqlite_conn.commit()
        log.info(f"[incident logged] {record}")
        return "logged"

    return {
        "trigger_alarm":    trigger_alarm,
        "send_emergency_sms": send_emergency_sms,
        "notify_contacts":  notify_contacts,
        "capture_photo":    capture_photo,
        "log_incident":     log_incident,
    }
