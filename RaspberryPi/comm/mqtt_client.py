"""Serialized MQTT v5 exchanges for the Django v2 device protocol."""

import json
import time
from collections import deque


ROUTES = {
    "chapter": ("device/agent_type", "agent_type/response", None),
    "object": ("device/object_detected_v2", "object_detected/response_v2",
               "object_detected/agent_response_v2"),
    "speech": ("device/user_response_v2", "user_response/response_v2",
               "user_response/agent_response_v2"),
    "stop": ("device/user_stop_v2", "user_stop/response_v2", None),
}


class BoardMQTT:
    def __init__(self, host, port, device_id, username=None, password=None, tls=False):
        import paho.mqtt.client as mqtt

        self.host, self.port, self.device_id = host, port, device_id
        self.prefix = f"server/device/{device_id}/"
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5,
                                  reconnect_on_failure=False)
        if username:
            self.client.username_pw_set(username, password)
        if tls:
            self.client.tls_set()
        self.client.on_connect = self._on_connect
        self.client.on_subscribe = self._on_subscribe
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self.ready = False
        self.error = None
        self.messages = deque(maxlen=64)
        self.conversation_id = None

    def _on_connect(self, client, userdata, flags, reason, properties):
        if reason.is_failure:
            self.error = f"Broker connection refused: {reason}"
            return
        subscriptions = [(self.prefix + suffix, 0) for _, ack, reply in ROUTES.values()
                         for suffix in (ack, reply) if suffix]
        rc, _ = client.subscribe(subscriptions)
        if rc:
            self.error = f"Subscription request failed: {rc}"

    def _on_subscribe(self, client, userdata, mid, reasons, properties):
        self.ready = not any(reason.is_failure for reason in reasons)
        if not self.ready:
            self.error = "Broker rejected one or more device subscriptions."

    def _on_message(self, client, userdata, message):
        if message.retain:
            return
        try:
            data = json.loads(message.payload)
        except (ValueError, UnicodeError):
            return
        if isinstance(data, dict) and data.get("type") != "stream":
            self.messages.append((message.topic, data))

    def _on_disconnect(self, client, userdata, flags, reason, properties):
        self.ready = False
        self.error = f"MQTT disconnected: {reason}"

    def _poll(self):
        if self.error:
            raise ConnectionError(self.error)
        time.sleep(0.02)

    def connect(self, timeout=10):
        self.client.connect_timeout = timeout
        self.client.connect(self.host, self.port)
        self.client.loop_start()
        deadline = time.monotonic() + timeout
        while not self.ready and time.monotonic() < deadline:
            self._poll()
        if not self.ready:
            raise TimeoutError("MQTT subscription confirmation timed out.")

    def request(self, kind, payload, timeout=90):
        if not self.ready:
            raise ConnectionError(self.error or "MQTT client is not subscribed.")
        topic, ack, reply = ROUTES[kind]
        self.messages.clear()
        wire = dict(payload, device_id=self.device_id)
        result = self.client.publish(topic, json.dumps(wire, ensure_ascii=False))
        if result.rc:
            raise ConnectionError(f"Could not publish {topic}: {result.rc}")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self._poll()
            while self.messages:
                incoming, data = self.messages.popleft()
                if data.get("device_id", self.device_id) != self.device_id:
                    continue
                if incoming == self.prefix + ack:
                    if data.get("status") != "success":
                        raise RuntimeError(data.get("message") or "Device request failed.")
                    if kind == "object":
                        self.conversation_id = data.get("conversation_id")
                    if not reply:
                        return data
                elif reply and incoming == self.prefix + reply:
                    if data.get("type") == "error":
                        raise RuntimeError(data.get("message") or "Agent request failed.")
                    if data.get("type") == "complete":
                        expected = wire.get("conversation_id") or self.conversation_id
                        if expected and data.get("conversation_id") != expected:
                            continue
                        if kind == "object":
                            self.conversation_id = data.get("conversation_id")
                        return data
        raise TimeoutError(f"No final response for {topic}.")

    def close(self):
        self.client.disconnect()
        self.client.loop_stop()
