# Thingdom Raspberry Pi Client

`main.py` coordinates the board; `comm/` implements the v2 MQTT exchange,
`hardware/` contains peripheral drivers, and `utils/` handles detection, speech and
flashcards. `presentation.py` maps completed replies to audio and screen output.
`imgs/` and `yolo/models/` contain the supplied assets and two local checkpoints.

## Board setup

Use 64-bit Raspberry Pi OS and Python 3.11 or 3.12. Enable SPI and grant the
running account access to SPI, GPIO, the camera and the audio devices.

```sh
sudo apt install sox mpv portaudio19-dev fonts-dejavu-core fonts-wqy-microhei
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Set the real broker, bound device ID and speech-service keys in `.env`. Use
`DASHSCOPE_WEBSOCKET_URL` if your DashScope workspace requires a specific endpoint.
Use `CHAPTER_TYPE` to select a chapter through MQTT, or leave it blank to use
the chapter already selected on the backend. Start the backend MQTT worker first.
Use `MOOD_IMAGE_MAP` to map backend mood names to your numbered images.

Original wiring, using BCM numbers: button GPIO3 (active low), pressure sensor
GPIO17 (active high), screen reset GPIO23 and D/C GPIO24, SPI0 MOSI GPIO10,
SCLK GPIO11 and CE0 GPIO8. The original I²S microphone uses GPIO18/19/20
for clock, word select and data. Check the actual GPIO chip with `gpioinfo`.
Set `GPIO_CHIP` and, if needed, `RPI_LGPIO_CHIP` to the board's header GPIO chip.
Confirm camera and microphone selection in their drivers before deployment.

Run `python main.py` from this directory. Trigger a capture using pressure, or
set `CAPTURE_TRIGGER=button` to use the physical button. Only a detected category
starts a session. In dialogue, press and release to start recording, then press
and release again to stop it; hold for two seconds while waiting or recording
to end the session. Recording also ends at its duration limit.

## MQTT contract

The board publishes `device/agent_type`, `device/object_detected_v2`,
`device/user_response_v2`, and `device/user_stop_v2`. It listens for the matching
acknowledgements and completed agent replies under `server/device/{device_id}/`.
Replies carry the conversation ID, spoken message, mood name and word records.
Only real transcription text and IDs from the preceding reply are sent back.
The current backend does not send island progress in completed replies; the
display uses it only if provided. Missing word art produces a text-only card.

The two YOLO weights are copied from the board source. `best.pt` identifies the
reference object; `yolo11n.pt` supplies general detection categories. No detector
training dataset was supplied in this board archive.
