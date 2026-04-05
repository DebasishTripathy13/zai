# backend/zai_client.py — Z.AI API client for threat analysis
# Replaces: Google Cloud Vision, OpenAI Whisper, YOLOv8 on-device inference

import requests
import base64
import json
import os

Z_AI_API_KEY = os.getenv("Z_AI_API_KEY", "YOUR_Z_AI_KEY")
Z_AI_URL = "https://api.z.ai/api/paas/v4/chat/completions"

_HEADERS = {
    "Authorization": f"Bearer {Z_AI_API_KEY}",
    "Content-Type": "application/json",
    "Accept-Language": "en-US,en",
}


def _post(payload: dict, timeout: int = 15) -> dict:
    resp = requests.post(Z_AI_URL, headers=_HEADERS, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def analyze_image(image_bytes: bytes) -> dict:
    """
    Detect weapons / threats in a JPEG frame using glm-5v-turbo (vision model).
    Offloads what would otherwise be YOLOv8 / Google Vision API inference.

    Returns:
        {"threat": bool, "type": "weapon|aggression|none",
         "objects": ["list of detected items"], "confidence": "low|medium|high"}
    """
    b64 = base64.b64encode(image_bytes).decode()
    result = _post({
        "model": "glm-5v-turbo",
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                },
                {
                    "type": "text",
                    "text": (
                        "Analyze this image for personal safety threats. "
                        "Look for weapons (knife, gun, bat, scissors), aggressive body language, "
                        "or dangerous situations. "
                        "Reply ONLY with valid JSON using exactly this schema: "
                        '{"threat": true/false, "type": "weapon/aggression/none", '
                        '"objects": ["detected items"], "confidence": "low/medium/high"}'
                    )
                }
            ]
        }],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    })
    return json.loads(result["choices"][0]["message"]["content"])


def classify_audio_threat(transcript: str) -> dict:
    """
    Classify whether an audio transcript indicates a safety emergency using glm-5.
    Offloads what would otherwise be OpenAI Whisper keyword matching.
    Supports English and Hindi/Urdu distress phrases.

    Args:
        transcript: Text transcribed from the audio clip.

    Returns:
        {"threat": bool, "keywords": ["matched"], "severity": "none|low|medium|high"}
    """
    result = _post({
        "model": "glm-5",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a personal safety assistant. Analyze audio transcripts for distress "
                    "signals, threats, or emergency situations. Be sensitive to context including "
                    "Hindi/Urdu distress words (bachao, chodo, ruko, madat karo)."
                )
            },
            {
                "role": "user",
                "content": (
                    f'Audio transcript: "{transcript}"\n\n'
                    "Does this indicate a personal safety emergency or distress? "
                    "Reply ONLY with valid JSON: "
                    '{"threat": true/false, "keywords": ["matched keywords"], '
                    '"severity": "none/low/medium/high"}'
                )
            }
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    })
    return json.loads(result["choices"][0]["message"]["content"])


def assess_situation(alert_history: list, sensor_data: dict) -> dict:
    """
    Context-aware threat assessment using glm-5.
    Offloads pattern analysis that is non-critical and compute-heavy for the Pico W.

    Args:
        alert_history: Last N alert dicts from the device.
        sensor_data:   Latest sensor readings (accel magnitude, audio RMS, etc.).

    Returns:
        {"threat_level": 1-4, "recommended_action": str, "summary": str}
        Levels: 1=normal, 2=elevated, 3=dangerous, 4=emergency SOS
    """
    result = _post({
        "model": "glm-5",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a safety monitoring assistant for a women's personal safety device. "
                    "Analyze sensor data and alert history to assess the overall threat level. "
                    "Threat levels: 1=normal, 2=elevated, 3=dangerous, 4=emergency SOS."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Recent alerts (newest last): {json.dumps(alert_history)}\n"
                    f"Current sensor readings: {json.dumps(sensor_data)}\n\n"
                    "What is the overall threat assessment? "
                    "Reply ONLY with valid JSON: "
                    '{"threat_level": 1, "recommended_action": "string", "summary": "brief description"}'
                )
            }
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }, timeout=10)
    return json.loads(result["choices"][0]["message"]["content"])


def generate_incident_report(incident_data: dict) -> str:
    """
    Generate a human-readable incident report for emergency responders using glm-5.
    Fully offloaded — no on-device processing needed.

    Args:
        incident_data: Dict containing alert details, assessment, location, timestamps.

    Returns:
        Plain-text report under ~100 words.
    """
    result = _post({
        "model": "glm-5",
        "messages": [
            {
                "role": "system",
                "content": "You are a safety incident report writer. Create concise, factual emergency reports."
            },
            {
                "role": "user",
                "content": (
                    f"Generate a brief emergency incident report from this data:\n"
                    f"{json.dumps(incident_data, indent=2)}\n\n"
                    "Include: timestamp, detected threats, sensor readings, location if available, "
                    "recommended response. Keep it under 100 words, factual, suitable for emergency responders."
                )
            }
        ],
        "temperature": 0.3,
        "max_tokens": 200,
    }, timeout=10)
    return result["choices"][0]["message"]["content"]
