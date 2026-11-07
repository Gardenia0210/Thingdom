"""Regenerate exact excerpt ranges after editing delivered application code."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
B = 'kids_language_2-main/'
ENTRIES = [
    ('Recognize Real Objects', 'Yolo_Raspberry-main/detector.py', ['ObjectDetector.__init__', 'ObjectDetector.detect', 'ObjectDetector.summary', 'ObjectDetector.top1'],
     'Ultralytics YOLO runs on a caller-supplied image and local weights. Bounding boxes are converted into dictionaries containing class names, confidence scores and pixel coordinates. Counter aggregates categories; maximum confidence selects the single object used as the character entry point. Empty detections remain empty.'),
    ('Train And Export Object Models', 'Yolo_Raspberry-main/train.py', ['train'],
     'The training entry validates a real dataset YAML and local initialization weights, then passes image size, epochs, device and output location to YOLO.train. No dataset is bundled with the training commands; training results depend on the supplied labeled images.'),
    ('Export Models For Device Integration', 'Yolo_Raspberry-main/export.py', ['export'],
     'YOLO.export converts actual weights into an explicitly requested format such as ONNX, NCNN or TorchScript. Device runtime compatibility and conversion dependencies require validation before deployment.'),
    ('Convert Detection Into Character Dialogue', B + 'agent_system_v2/events.py', ['build_object_event'],
     'A real detected category and selected chapter become a JSON device event. The instruction explicitly states that the child has not spoken. This initiates character role-play without substituting a scripted greeting for microphone input.'),
    ('Route Hardware Events And Conversation State', B + 'agent_system_v2/mqtt_handlers.py', ['handle_device_agent_type', 'handle_object_detected_v2', 'handle_user_response_v2'],
     'MQTT handlers resolve the account bound to the device, update chapter state, create or resume object conversations, and pass actual child transcriptions to the main agent. Django ORM records messages and conversation encounters. Stream and completion responses are published to per-device topics.'),
    ('Generate Contextual Object Identities', B + 'agent_system_v2/agents/naming_agent.py', ['invoke_naming_agent'],
     'The naming agent sends the detected category and chapter context to the configured GLM model. A Pydantic NamingAgentResponse validates bilingual identity names and descriptions. ObjectInfoMiddleware persists this generated identity for later encounters with the same character.'),
    ('Persist Character Personality', B + 'agent_system_v2/middleware/object_persona.py', ['ObjectPersonaMiddleware._process_persona', 'ObjectPersonaMiddleware._load_persona_template'],
     'A conversation receives one of twelve persona identifiers, which Django stores with its object identity. The corresponding Markdown template is loaded into the dynamic system prompt. Existing conversations reuse their stored personality across encounters.'),
    ('Compose Adaptive Dialogue And Short-Term Memory', B + 'agent_system_v2/agents/main_agent.py', ['get_checkpointer', 'get_main_agent', 'stream_agent_response'],
     'LangChain create_agent combines character, curriculum, child memory and guardrail middleware. GLM generates MainAgentResponse structured output. LangGraph PostgresSaver persists conversation threads, while SummarizationMiddleware compresses conversation context. The streaming entry emits decoded dialogue and structured vocabulary identifiers.'),
    ('Decode Fragmented Dialogue Streams', B + 'agent_system_v2/agents/stream_parser.py', ['StreamingAiMessageExtractor.feed'],
     'The incremental extractor buffers arbitrary JSON fragments until the ai_message key is complete. It decodes escaped quotes, Unicode and surrogate pairs before sending text to a callback. Other structured fields remain outside the speech stream.'),
    ('Prioritize Vocabulary For Adaptive Teaching', B + 'agent_system_v2/middleware/study.py', ['StudyMiddleware._query_candidate_words'],
     'Django queries vocabulary from active study plans, excludes frozen and mastered entries, and orders candidates by review priority. Recently failed words are incorporated into the candidate pool. A bounded list supplies word identifiers and meanings to the teaching prompt.'),
    ('Assess Vocabulary From Actual Child Replies', B + 'agent_system_v2/agents/word_mastery_agent.py', ['invoke_word_mastery_agent'],
     'The assessment agent receives the actual AI sentence, child transcription and eligible word records. GLM returns recognition, usage, fluency and confidence per word. Pydantic validates the response structure before the handler computes mastery and determines progression.'),
    ('Advance Mastery And Schedule Review', B + 'agent_system_v2/mqtt_handlers.py', ['_process_word_mastery', '_advance_learned_type'],
     'Recognition and usage each contribute forty percent to mastery; fluency contributes twenty percent. Passing requires confidence of at least 0.55 and mastery of at least 0.65. Eligible vocabulary advances through not_started, learning, review_due and mastered, with freezing between review stages.'),
    ('Thaw Vocabulary For Spaced Review', B + 'agent_system_v2/scheduled_tasks.py', ['thaw_frozen_words', 'start_scheduled_tasks'],
     'The worker checks frozen vocabulary against timestamps. Learning words become eligible after twenty-four hours and review_due words after three days. Mastered words stay frozen. The original background scheduler performs review checks and refreshes plan progress every thirty minutes.'),
    ('Summarize Encounters Into Long-Term Memory', B + 'agent_system_v2/mqtt_handlers.py', ['handle_user_stop_v2'],
     'A stop event closes the device-owned active conversation. The handler gathers encounter messages, mastery evidence and existing memory, then invokes the summary agent. Returned traits, interests, motivation triggers and English level update LongtermMemory for later personalization.'),
    ('Personalize Dialogue With Child Memory', B + 'agent_system_v2/middleware/children_info.py', ['ChildrenInfoMiddleware.wrap_model_call', 'ChildrenInfoMiddleware._query_child_info'],
     'The middleware retrieves persistent child observations for the current conversation and appends them to the system message. Missing memory produces no invented profile. Stored interests, personality, motivation and language level guide subsequent interactions.'),
    ('Manage Parent Plans And Progress', B + 'user_system/views.py', ['bind_device', 'select_study_plan', 'get_study_plan_progress'],
     'Authenticated Django REST endpoints bind devices, convert selected dictionary chapters into study plans and return learning progress. UserStudyPlan and UserOngoingPlan separate chapter selection from per-word learning state, enabling the parent interface to display learned, pending and review vocabulary.'),
    ('Calculate Learning Progress', B + 'user_system/utils.py', ['update_learned_percentage'],
     'The shared ORM utility calculates plan progress from actual per-word learning records and updates stored percentages. Parent APIs and the background scheduler reuse this calculation rather than injecting demonstration progress values.'),
    ('Check Incoming Conversation Content', B + 'agent_system_v2/middleware/before_guardrails.py', ['BeforeGuardrailsMiddleware.before_agent'],
     'A configured GLM classifier evaluates incoming conversation content. Unsafe classifications return a redirecting response and end the current agent path. The inherited error behavior logs classifier failures; this mechanism is not a guarantee of comprehensive content safety.'),
    ('Check Generated Conversation Content', B + 'agent_system_v2/middleware/after_guardrails.py', ['AfterGuardrailsMiddleware.after_agent'],
     'The output middleware reviews generated dialogue with the configured safety model and can replace unsuitable content. This supports child-oriented role-play alongside the teaching prompt and structured response schema.'),
]


ENTRIES += [('Detect Real Capture Gestures', 'RaspberryPi/main.py', ['wait_for_gesture', 'identify'], 'Physical GPIO input gates capture; empty detections are retried without publishing.'), ('Read the Physical Button', 'RaspberryPi/hardware/button.py', ['Button._init_gpio', 'Button.is_pressed'], 'lgpio reads the active-low button used to start recording and end dialogue.'), ('Read the Pressure Trigger', 'RaspberryPi/hardware/pressure_sensor.py', ['PressureSensor._init_gpio', 'PressureSensor.is_pressed'], 'lgpio reads the active-high pressure sensor as a physical capture trigger.'), ('Capture Camera Frames', 'RaspberryPi/hardware/camera_capture.py', ['CameraCapture.capture_photo_usb_camera'], 'OpenCV captures a fresh camera frame and releases the camera after each attempt.'), ('Select the Closest Detected Object', 'RaspberryPi/utils/object_detection.py', ['ObjectDetection.detect_closest_object'], 'Two local YOLO checkpoints locate the reference marker and the nearest valid object.'), ('Exchange Device Messages Over MQTT', 'RaspberryPi/comm/mqtt_client.py', ['BoardMQTT.connect', 'BoardMQTT.request'], 'Paho MQTT v5 routes requests and waits for matching acknowledgements or final replies.'), ('Record Microphone Audio', 'RaspberryPi/hardware/audio_recorder.py', ['AudioRecorder.start_recording', 'AudioRecorder._record_async'], 'PyAudio collects microphone frames in a worker and writes the recording as WAV.'), ('Transcribe Local Speech', 'RaspberryPi/utils/speech_recognition.py', ['transcribe'], 'SoX normalizes the WAV; DashScope Recognition.call returns the spoken text.'), ('Run Real Voice Dialogue', 'RaspberryPi/main.py', ['interact', 'main'], 'The session sends transcribed text and prior word IDs, then stops the active conversation.'), ('Synthesize Spoken Replies', 'RaspberryPi/utils/text_to_speech.py', ['TextToSpeech.synthesize_async'], 'MiniMax WebSocket synthesis turns the backend reply into an audio file.'), ('Play Speech and Display Vocabulary', 'RaspberryPi/presentation.py', ['present'], 'Server word records drive flashcards; the speaker plays synthesized replies through MPV.'), ('Render Images Over SPI', 'RaspberryPi/hardware/ep1831t_driver.py', ['EP1831TDriver.display_image'], 'Pillow prepares the frame and the EP1831T driver sends RGB565 pixels over SPI.')]


def symbols(path):
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    result = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result[node.name] = node
        elif isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    result[node.name + '.' + child.name] = child
    return result


def main():
    output = ['# Thingdom — Core Code Map', '',
              'Canonical package: `E:/SFK/Project2/Thingdom_Code`', '',
              'Verified date: 2026-11-07 (Asia/Shanghai). Line ranges are one-based, inclusive, and refer to the delivered copy.', '',
              'Coverage is inferred from the existing Thingdom architecture: tangible object recognition, character role-play, adaptive vocabulary, memory and parent progress. The map includes the Raspberry Pi runtime and its peripheral adapters.', '']
    for number, (title, relative, names, description) in enumerate(ENTRIES, 1):
        assert len(title.split()) <= 10
        assert len(description.split()) < 100
        path = ROOT / relative
        found = symbols(path)
        output += [f'## {number}. {title}', '', f'**Path:** `{path.as_posix()}`', '']
        for name in names:
            node = found[name]
            output += [f'- **Lines:** L{node.lineno}–L{node.end_lineno} (`{name}`); '
                       f'[Open code]({path.as_posix()}:{node.lineno})']
        output += ['', f'**Title:** {title}', '', f'**Description:** {description}', '']
    target = ROOT / 'docs/Thingdom.md'
    target.write_text('\n'.join(output), encoding='utf-8')
    print(f'Generated {len(ENTRIES)} excerpts: {target}')


if __name__ == '__main__':
    main()
