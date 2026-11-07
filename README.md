# Thingdom Code

Independent, refined source package for Thingdom's object-based English learning prototype.
The source directories under `E:/SFK/Project2/Code` are unchanged. Python 3.11 or 3.12 is required; the system Python 3.7 is too old for this backend.

## Layout

```text
Thingdom_Code/
  kids_language_2-main/     Django backend, database migrations and persona resources
    user_system/           Authentication, device binding, dictionaries and study plans
    agent_system_v2/       MQTT dialogue, naming, learning, mastery and memory pipeline
    agent_system/          Legacy models and agent helpers retained for compatibility
    kids_language_2/       Settings, URL routing and database routing
  Yolo_Raspberry-main/     Image inference, training and model export commands
  RaspberryPi/             Raspberry Pi runtime, peripheral drivers and local weights
  docs/                    Change notes, core code index and source hashes
  tests/                   Offline regression tests
  requirements.txt         Combined installation entry point
```

The duplicated backend and vendored Ultralytics source are omitted. `ultralytics==8.3.163` supplies the original third-party implementation. Its dependencies include PyTorch, TorchVision, OpenCV, NumPy, Pillow and PyYAML. Component requirement files permit separate backend and training environments. Install board dependencies separately using `RaspberryPi/requirements.txt` on Raspberry Pi OS.

## Backend setup

Use a new environment and install either the backend requirements or the combined root requirements. Run backend commands from `kids_language_2-main`.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Put the generated value into `SECRET_KEY`. Configure PostgreSQL credentials, `ZHIPU_API_KEY`, and the MQTT broker in `.env`. The v2 pipeline uses the original GLM model settings through the OpenAI-compatible Zhipu API; the optional MiniMax factory and legacy SiliconFlow settings remain available. No API keys or database credentials are included.

```powershell
python manage.py migrate --database default
python manage.py createsuperuser
python manage.py check
python manage.py runserver
```

The active database is `kid_language_4` by default. Legacy helpers use a separate `kid_language_3` database and need `python manage.py migrate --database legacy` only if that functionality is required. Their models are retained to preserve migration history and compatibility. Fresh initialization also includes a repair to the original migration's index-removal order; see the verification notes.

HTTP APIs: `/api/auth/token/`, `/api/auth/token/refresh/`, and `/api/user/`. `/api/agent/` and `/api/v2/agent/` are reserved and currently have no domain HTTP views: v2 dialogue runs over MQTT. The Django admin at `/admin/` manages the actual dictionary, word meanings, chapter mappings, chapter prompts and mood records. Import real curriculum data before selecting a study plan. No sample child accounts, vocabulary fixtures or fabricated progress are included.

Keep `MQTT_ENABLED=false` for web workers, checks, tests and migrations. Start exactly one dedicated worker in another terminal:

```powershell
$env:MQTT_ENABLED = 'true'
python manage.py runmqtt
```

The worker subscribes to device events and runs the original 30-minute review scheduler. Use one process because the inherited locks and scheduler are process-local. On Linux, the HTTP service can use Gunicorn; it is excluded from Windows installation.

## Detection, training and export

Run these commands from `Yolo_Raspberry-main`, replacing paths with real files:

```powershell
python -m pip install -r requirements.txt
python main1.py C:/data/object.jpg --weights C:/models/best.pt
python main2.py C:/data/object.jpg --weights C:/models/best.pt --confidence 0.4
python train.py --data C:/data/thingdom.yaml --weights C:/models/yolo11n.pt --epochs 100 --device cpu
python export.py --weights C:/models/best.pt --format onnx
```

`main1.py` returns category counts; `main2.py` returns the highest-confidence category or an empty string when nothing is detected. `ObjectDetector.detect()` returns a list of dictionaries containing `name`, `confidence`, and `box` coordinates. Reuse one `ObjectDetector` for camera frames to avoid repeated model loading. No result is sent to the backend automatically: the board client publishes actual detections through the documented MQTT protocol.

The supplied original YOLO directory contained inference examples but no Thingdom dataset or project training configuration. The separate board archive supplies two inference weights. The new training/export commands accept real inputs; they do not imply a model has already been trained or tested. A detection dataset YAML must specify `path`, `train`, `val`, and `names`; annotations must use the Ultralytics detection format. Relative image paths resolve against the dataset root. Supply locally obtained weights explicitly; the wrapper will not download a model silently. NCNN export requires platform-specific conversion dependencies and later board validation.

## Device integration

See [Raspberry Pi setup and MQTT protocol](RaspberryPi/README.md) for GPIO, camera, speech, playback and display configuration. Physical hardware and live services still require on-device validation.

## Verification and code references

```powershell
python -m unittest discover -s tests -v
cd kids_language_2-main
python manage.py check --settings kids_language_2.test_settings
python manage.py test --settings kids_language_2.test_settings
```

Tests use mocks only at external model/broker boundaries; they do not claim cloud, hardware or model-accuracy validation. See [verification evidence](docs/VALIDATION.md), [refinement notes](docs/CHANGES.md), and [core code map](docs/Thingdom.md). Line ranges in the map refer to this delivered copy. Chinese runtime prompts, curriculum labels and API messages remain intact; source comments and docstrings are English.
