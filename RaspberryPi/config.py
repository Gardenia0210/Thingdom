import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")

MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")

USE_GPIO = True
SENSOR_PIN = 17
BUTTON_PIN = 3
LED_PIN = 27
DEBOUNCE_TIME = 0.3
BUTTON_LONG_PRESS_TIME = 2.0

SCREEN_RST_PIN = 23
SCREEN_DC_PIN = 24
SCREEN_WIDTH = 360
SCREEN_HEIGHT = 360
SCREEN_SPI_SPEED = 32000000

HW_SAMPLE_RATE = 48000
HW_CHANNELS = 2
HW_CHUNK = 9600
HW_FORMAT = 'paInt32'

ASR_SAMPLE_RATE = 16000
ASR_CHANNELS = 1
ASR_BITDEPTH = 16

MAX_DURATION = 30

TTS_MODEL = "speech-2.6-hd"
TTS_VOICE_ID = "male-qn-qingse"
TTS_SPEED = 1
TTS_VOLUME = 1
TTS_PITCH = 0
TTS_SAMPLE_RATE = 32000
TTS_BITRATE = 128000
TTS_FORMAT = "mp3"
TTS_CHANNEL = 1

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
TEMP_DATA_DIR = os.path.join(PROJECT_ROOT, "temp_data")

SAVE_DIR = TEMP_DATA_DIR
OUTPUT_DIR = TEMP_DATA_DIR

FILE_OBJECT_NAME = f"{TEMP_DATA_DIR}/object_name.txt"

DEBUG_LOG = False
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
LOG_FILE = os.path.join(LOG_DIR, "system.log")

CARD_BG_COLOR = (246, 235, 255)
CARD_CIRCLE_COLOR = (255, 255, 255)
CARD_TEXT_COLOR = (0, 0, 0)
CARD_IMAGE_SIZE = 120
CARD_IMAGE_Y_OFFSET = -30

PROGRESS_RING_WIDTH = 5
PROGRESS_RING_COLOR_COMPLETED = (76, 175, 80)
PROGRESS_RING_COLOR_INCOMPLETE = (200, 200, 200)
PROGRESS_RING_COLOR_LOCKED = (100, 100, 100)

FONT_EN_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_CN_PATH = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
FONT_EN_SIZE = 48
FONT_CN_SIZE = 32

SOX_VOLUME_GAIN = 10.0

MQTT_BROKER = os.getenv("MQTT_BROKER", "")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
DEVICE_ID = os.getenv("DEVICE_ID", "")


GPIO_CHIP = int(os.getenv("GPIO_CHIP", "4"))
