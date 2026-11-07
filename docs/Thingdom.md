# Thingdom — Core Code Map

Canonical package: `E:/SFK/Project2/Thingdom_Code`

Verified date: 2026-11-07 (Asia/Shanghai). Line ranges are one-based, inclusive, and refer to the delivered copy.

Coverage is inferred from the existing Thingdom architecture: tangible object recognition, character role-play, adaptive vocabulary, memory and parent progress. The map includes the Raspberry Pi runtime and its peripheral adapters.

## 1. Recognize Real Objects

**Path:** `E:/SFK/Project2/Thingdom_Code/Yolo_Raspberry-main/detector.py`

- **Lines:** L9–L16 (`ObjectDetector.__init__`); [Open code](E:/SFK/Project2/Thingdom_Code/Yolo_Raspberry-main/detector.py:9)
- **Lines:** L18–L32 (`ObjectDetector.detect`); [Open code](E:/SFK/Project2/Thingdom_Code/Yolo_Raspberry-main/detector.py:18)
- **Lines:** L34–L37 (`ObjectDetector.summary`); [Open code](E:/SFK/Project2/Thingdom_Code/Yolo_Raspberry-main/detector.py:34)
- **Lines:** L39–L42 (`ObjectDetector.top1`); [Open code](E:/SFK/Project2/Thingdom_Code/Yolo_Raspberry-main/detector.py:39)

**Title:** Recognize Real Objects

**Description:** Ultralytics YOLO runs on a caller-supplied image and local weights. Bounding boxes are converted into dictionaries containing class names, confidence scores and pixel coordinates. Counter aggregates categories; maximum confidence selects the single object used as the character entry point. Empty detections remain empty.

## 2. Train And Export Object Models

**Path:** `E:/SFK/Project2/Thingdom_Code/Yolo_Raspberry-main/train.py`

- **Lines:** L6–L16 (`train`); [Open code](E:/SFK/Project2/Thingdom_Code/Yolo_Raspberry-main/train.py:6)

**Title:** Train And Export Object Models

**Description:** The training entry validates a real dataset YAML and local initialization weights, then passes image size, epochs, device and output location to YOLO.train. No dataset is bundled with the training commands; training results depend on the supplied labeled images.

## 3. Export Models For Device Integration

**Path:** `E:/SFK/Project2/Thingdom_Code/Yolo_Raspberry-main/export.py`

- **Lines:** L6–L11 (`export`); [Open code](E:/SFK/Project2/Thingdom_Code/Yolo_Raspberry-main/export.py:6)

**Title:** Export Models For Device Integration

**Description:** YOLO.export converts actual weights into an explicitly requested format such as ONNX, NCNN or TorchScript. Device runtime compatibility and conversion dependencies require validation before deployment.

## 4. Convert Detection Into Character Dialogue

**Path:** `E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/events.py`

- **Lines:** L5–L16 (`build_object_event`); [Open code](E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/events.py:5)

**Title:** Convert Detection Into Character Dialogue

**Description:** A real detected category and selected chapter become a JSON device event. The instruction explicitly states that the child has not spoken. This initiates character role-play without substituting a scripted greeting for microphone input.

## 5. Route Hardware Events And Conversation State

**Path:** `E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/mqtt_handlers.py`

- **Lines:** L93–L174 (`handle_device_agent_type`); [Open code](E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/mqtt_handlers.py:93)
- **Lines:** L219–L420 (`handle_object_detected_v2`); [Open code](E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/mqtt_handlers.py:219)
- **Lines:** L598–L808 (`handle_user_response_v2`); [Open code](E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/mqtt_handlers.py:598)

**Title:** Route Hardware Events And Conversation State

**Description:** MQTT handlers resolve the account bound to the device, update chapter state, create or resume object conversations, and pass actual child transcriptions to the main agent. Django ORM records messages and conversation encounters. Stream and completion responses are published to per-device topics.

## 6. Generate Contextual Object Identities

**Path:** `E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/agents/naming_agent.py`

- **Lines:** L39–L86 (`invoke_naming_agent`); [Open code](E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/agents/naming_agent.py:39)

**Title:** Generate Contextual Object Identities

**Description:** The naming agent sends the detected category and chapter context to the configured GLM model. A Pydantic NamingAgentResponse validates bilingual identity names and descriptions. ObjectInfoMiddleware persists this generated identity for later encounters with the same character.

## 7. Persist Character Personality

**Path:** `E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/middleware/object_persona.py`

- **Lines:** L42–L85 (`ObjectPersonaMiddleware._process_persona`); [Open code](E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/middleware/object_persona.py:42)
- **Lines:** L88–L102 (`ObjectPersonaMiddleware._load_persona_template`); [Open code](E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/middleware/object_persona.py:88)

**Title:** Persist Character Personality

**Description:** A conversation receives one of twelve persona identifiers, which Django stores with its object identity. The corresponding Markdown template is loaded into the dynamic system prompt. Existing conversations reuse their stored personality across encounters.

## 8. Compose Adaptive Dialogue And Short-Term Memory

**Path:** `E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/agents/main_agent.py`

- **Lines:** L42–L64 (`get_checkpointer`); [Open code](E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/agents/main_agent.py:42)
- **Lines:** L68–L116 (`get_main_agent`); [Open code](E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/agents/main_agent.py:68)
- **Lines:** L118–L204 (`stream_agent_response`); [Open code](E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/agents/main_agent.py:118)

**Title:** Compose Adaptive Dialogue And Short-Term Memory

**Description:** LangChain create_agent combines character, curriculum, child memory and guardrail middleware. GLM generates MainAgentResponse structured output. LangGraph PostgresSaver persists conversation threads, while SummarizationMiddleware compresses conversation context. The streaming entry emits decoded dialogue and structured vocabulary identifiers.

## 9. Decode Fragmented Dialogue Streams

**Path:** `E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/agents/stream_parser.py`

- **Lines:** L13–L45 (`StreamingAiMessageExtractor.feed`); [Open code](E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/agents/stream_parser.py:13)

**Title:** Decode Fragmented Dialogue Streams

**Description:** The incremental extractor buffers arbitrary JSON fragments until the ai_message key is complete. It decodes escaped quotes, Unicode and surrogate pairs before sending text to a callback. Other structured fields remain outside the speech stream.

## 10. Prioritize Vocabulary For Adaptive Teaching

**Path:** `E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/middleware/study.py`

- **Lines:** L115–L175 (`StudyMiddleware._query_candidate_words`); [Open code](E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/middleware/study.py:115)

**Title:** Prioritize Vocabulary For Adaptive Teaching

**Description:** Django queries vocabulary from active study plans, excludes frozen and mastered entries, and orders candidates by review priority. Recently failed words are incorporated into the candidate pool. A bounded list supplies word identifiers and meanings to the teaching prompt.

## 11. Assess Vocabulary From Actual Child Replies

**Path:** `E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/agents/word_mastery_agent.py`

- **Lines:** L54–L119 (`invoke_word_mastery_agent`); [Open code](E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/agents/word_mastery_agent.py:54)

**Title:** Assess Vocabulary From Actual Child Replies

**Description:** The assessment agent receives the actual AI sentence, child transcription and eligible word records. GLM returns recognition, usage, fluency and confidence per word. Pydantic validates the response structure before the handler computes mastery and determines progression.

## 12. Advance Mastery And Schedule Review

**Path:** `E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/mqtt_handlers.py`

- **Lines:** L465–L567 (`_process_word_mastery`); [Open code](E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/mqtt_handlers.py:465)
- **Lines:** L569–L596 (`_advance_learned_type`); [Open code](E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/mqtt_handlers.py:569)

**Title:** Advance Mastery And Schedule Review

**Description:** Recognition and usage each contribute forty percent to mastery; fluency contributes twenty percent. Passing requires confidence of at least 0.55 and mastery of at least 0.65. Eligible vocabulary advances through not_started, learning, review_due and mastered, with freezing between review stages.

## 13. Thaw Vocabulary For Spaced Review

**Path:** `E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/scheduled_tasks.py`

- **Lines:** L19–L52 (`thaw_frozen_words`); [Open code](E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/scheduled_tasks.py:19)
- **Lines:** L72–L99 (`start_scheduled_tasks`); [Open code](E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/scheduled_tasks.py:72)

**Title:** Thaw Vocabulary For Spaced Review

**Description:** The worker checks frozen vocabulary against timestamps. Learning words become eligible after twenty-four hours and review_due words after three days. Mastered words stay frozen. The original background scheduler performs review checks and refreshes plan progress every thirty minutes.

## 14. Summarize Encounters Into Long-Term Memory

**Path:** `E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/mqtt_handlers.py`

- **Lines:** L826–L962 (`handle_user_stop_v2`); [Open code](E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/mqtt_handlers.py:826)

**Title:** Summarize Encounters Into Long-Term Memory

**Description:** A stop event closes the device-owned active conversation. The handler gathers encounter messages, mastery evidence and existing memory, then invokes the summary agent. Returned traits, interests, motivation triggers and English level update LongtermMemory for later personalization.

## 15. Personalize Dialogue With Child Memory

**Path:** `E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/middleware/children_info.py`

- **Lines:** L22–L50 (`ChildrenInfoMiddleware.wrap_model_call`); [Open code](E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/middleware/children_info.py:22)
- **Lines:** L53–L84 (`ChildrenInfoMiddleware._query_child_info`); [Open code](E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/middleware/children_info.py:53)

**Title:** Personalize Dialogue With Child Memory

**Description:** The middleware retrieves persistent child observations for the current conversation and appends them to the system message. Missing memory produces no invented profile. Stored interests, personality, motivation and language level guide subsequent interactions.

## 16. Manage Parent Plans And Progress

**Path:** `E:/SFK/Project2/Thingdom_Code/kids_language_2-main/user_system/views.py`

- **Lines:** L132–L157 (`bind_device`); [Open code](E:/SFK/Project2/Thingdom_Code/kids_language_2-main/user_system/views.py:132)
- **Lines:** L260–L369 (`select_study_plan`); [Open code](E:/SFK/Project2/Thingdom_Code/kids_language_2-main/user_system/views.py:260)
- **Lines:** L412–L502 (`get_study_plan_progress`); [Open code](E:/SFK/Project2/Thingdom_Code/kids_language_2-main/user_system/views.py:412)

**Title:** Manage Parent Plans And Progress

**Description:** Authenticated Django REST endpoints bind devices, convert selected dictionary chapters into study plans and return learning progress. UserStudyPlan and UserOngoingPlan separate chapter selection from per-word learning state, enabling the parent interface to display learned, pending and review vocabulary.

## 17. Calculate Learning Progress

**Path:** `E:/SFK/Project2/Thingdom_Code/kids_language_2-main/user_system/utils.py`

- **Lines:** L10–L83 (`update_learned_percentage`); [Open code](E:/SFK/Project2/Thingdom_Code/kids_language_2-main/user_system/utils.py:10)

**Title:** Calculate Learning Progress

**Description:** The shared ORM utility calculates plan progress from actual per-word learning records and updates stored percentages. Parent APIs and the background scheduler reuse this calculation rather than injecting demonstration progress values.

## 18. Check Incoming Conversation Content

**Path:** `E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/middleware/before_guardrails.py`

- **Lines:** L46–L85 (`BeforeGuardrailsMiddleware.before_agent`); [Open code](E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/middleware/before_guardrails.py:46)

**Title:** Check Incoming Conversation Content

**Description:** A configured GLM classifier evaluates incoming conversation content. Unsafe classifications return a redirecting response and end the current agent path. The inherited error behavior logs classifier failures; this mechanism is not a guarantee of comprehensive content safety.

## 19. Check Generated Conversation Content

**Path:** `E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/middleware/after_guardrails.py`

- **Lines:** L46–L96 (`AfterGuardrailsMiddleware.after_agent`); [Open code](E:/SFK/Project2/Thingdom_Code/kids_language_2-main/agent_system_v2/middleware/after_guardrails.py:46)

**Title:** Check Generated Conversation Content

**Description:** The output middleware reviews generated dialogue with the configured safety model and can replace unsuitable content. This supports child-oriented role-play alongside the teaching prompt and structured response schema.

## Raspberry Pi Hardware

### 20. Detect Real Capture Gestures

**Path:** `E:/SFK/Project2/Thingdom_Code/RaspberryPi/main.py`

- **Lines:** L16–L30 (`wait_for_gesture`); [Open code](E:/SFK/Project2/Thingdom_Code/RaspberryPi/main.py:16)
- **Lines:** L33–L49 (`identify`); [Open code](E:/SFK/Project2/Thingdom_Code/RaspberryPi/main.py:33)

**Title:** Detect Real Capture Gestures

**Description:** Physical GPIO input gates capture; empty detections are retried without publishing.

### 21. Read the Physical Button

**Path:** `E:/SFK/Project2/Thingdom_Code/RaspberryPi/hardware/button.py`

- **Lines:** L43–L57 (`Button._init_gpio`); [Open code](E:/SFK/Project2/Thingdom_Code/RaspberryPi/hardware/button.py:43)
- **Lines:** L59–L72 (`Button.is_pressed`); [Open code](E:/SFK/Project2/Thingdom_Code/RaspberryPi/hardware/button.py:59)

**Title:** Read the Physical Button

**Description:** lgpio reads the active-low button used to start recording and end dialogue.

### 22. Read the Pressure Trigger

**Path:** `E:/SFK/Project2/Thingdom_Code/RaspberryPi/hardware/pressure_sensor.py`

- **Lines:** L42–L55 (`PressureSensor._init_gpio`); [Open code](E:/SFK/Project2/Thingdom_Code/RaspberryPi/hardware/pressure_sensor.py:42)
- **Lines:** L57–L70 (`PressureSensor.is_pressed`); [Open code](E:/SFK/Project2/Thingdom_Code/RaspberryPi/hardware/pressure_sensor.py:57)

**Title:** Read the Pressure Trigger

**Description:** lgpio reads the active-high pressure sensor as a physical capture trigger.

### 23. Capture Camera Frames

**Path:** `E:/SFK/Project2/Thingdom_Code/RaspberryPi/hardware/camera_capture.py`

- **Lines:** L40–L83 (`CameraCapture.capture_photo_usb_camera`); [Open code](E:/SFK/Project2/Thingdom_Code/RaspberryPi/hardware/camera_capture.py:40)

**Title:** Capture Camera Frames

**Description:** OpenCV captures a fresh camera frame and releases the camera after each attempt.

### 24. Select the Closest Detected Object

**Path:** `E:/SFK/Project2/Thingdom_Code/RaspberryPi/utils/object_detection.py`

- **Lines:** L76–L170 (`ObjectDetection.detect_closest_object`); [Open code](E:/SFK/Project2/Thingdom_Code/RaspberryPi/utils/object_detection.py:76)

**Title:** Select the Closest Detected Object

**Description:** Two local YOLO checkpoints locate the reference marker and the nearest valid object.

### 25. Exchange Device Messages Over MQTT

**Path:** `E:/SFK/Project2/Thingdom_Code/RaspberryPi/comm/mqtt_client.py`

- **Lines:** L73–L81 (`BoardMQTT.connect`); [Open code](E:/SFK/Project2/Thingdom_Code/RaspberryPi/comm/mqtt_client.py:73)
- **Lines:** L83–L116 (`BoardMQTT.request`); [Open code](E:/SFK/Project2/Thingdom_Code/RaspberryPi/comm/mqtt_client.py:83)

**Title:** Exchange Device Messages Over MQTT

**Description:** Paho MQTT v5 routes requests and waits for matching acknowledgements or final replies.

### 26. Record Microphone Audio

**Path:** `E:/SFK/Project2/Thingdom_Code/RaspberryPi/hardware/audio_recorder.py`

- **Lines:** L354–L377 (`AudioRecorder.start_recording`); [Open code](E:/SFK/Project2/Thingdom_Code/RaspberryPi/hardware/audio_recorder.py:354)
- **Lines:** L398–L483 (`AudioRecorder._record_async`); [Open code](E:/SFK/Project2/Thingdom_Code/RaspberryPi/hardware/audio_recorder.py:398)

**Title:** Record Microphone Audio

**Description:** PyAudio collects microphone frames in a worker and writes the recording as WAV.

### 27. Transcribe Local Speech

**Path:** `E:/SFK/Project2/Thingdom_Code/RaspberryPi/utils/speech_recognition.py`

- **Lines:** L10–L29 (`transcribe`); [Open code](E:/SFK/Project2/Thingdom_Code/RaspberryPi/utils/speech_recognition.py:10)

**Title:** Transcribe Local Speech

**Description:** SoX normalizes the WAV; DashScope Recognition.call returns the spoken text.

### 28. Run Real Voice Dialogue

**Path:** `E:/SFK/Project2/Thingdom_Code/RaspberryPi/main.py`

- **Lines:** L52–L83 (`interact`); [Open code](E:/SFK/Project2/Thingdom_Code/RaspberryPi/main.py:52)
- **Lines:** L86–L160 (`main`); [Open code](E:/SFK/Project2/Thingdom_Code/RaspberryPi/main.py:86)

**Title:** Run Real Voice Dialogue

**Description:** The session sends transcribed text and prior word IDs, then stops the active conversation.

### 29. Synthesize Spoken Replies

**Path:** `E:/SFK/Project2/Thingdom_Code/RaspberryPi/utils/text_to_speech.py`

- **Lines:** L191–L247 (`TextToSpeech.synthesize_async`); [Open code](E:/SFK/Project2/Thingdom_Code/RaspberryPi/utils/text_to_speech.py:191)

**Title:** Synthesize Spoken Replies

**Description:** MiniMax WebSocket synthesis turns the backend reply into an audio file.

### 30. Play Speech and Display Vocabulary

**Path:** `E:/SFK/Project2/Thingdom_Code/RaspberryPi/presentation.py`

- **Lines:** L12–L32 (`present`); [Open code](E:/SFK/Project2/Thingdom_Code/RaspberryPi/presentation.py:12)

**Title:** Play Speech and Display Vocabulary

**Description:** Server word records drive flashcards; the speaker plays synthesized replies through MPV.

### 31. Render Images Over SPI

**Path:** `E:/SFK/Project2/Thingdom_Code/RaspberryPi/hardware/ep1831t_driver.py`

- **Lines:** L242–L291 (`EP1831TDriver.display_image`); [Open code](E:/SFK/Project2/Thingdom_Code/RaspberryPi/hardware/ep1831t_driver.py:242)

**Title:** Render Images Over SPI

**Description:** Pillow prepares the frame and the EP1831T driver sends RGB565 pixels over SPI.
