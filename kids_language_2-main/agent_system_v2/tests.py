"""Database-backed checks for the real device input boundary."""
import json
from unittest.mock import patch
from django.test import TestCase
from user_system.models import User
from .models import Conversation, Message
from .mqtt_handlers import handle_object_detected_v2, handle_user_response_v2, handle_user_stop_v2


class DeviceConversationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner', device_id='device-a', chapter_type='fruit')
        self.other = User.objects.create_user('other', device_id='device-b', chapter_type='school')
        self.conversation = Conversation.objects.create(
            user=self.owner, device_id='device-a', object_name='apple', chapter_type='fruit')
        self.publisher = patch('agent_system_v2.mqtt_handlers.mqtt_client_v2.publish')
        self.publish = self.publisher.start()
        self.addCleanup(self.publisher.stop)

    def test_foreign_device_cannot_reply_or_stop(self):
        payload = json.dumps({'device_id': 'device-b', 'conversation_id': self.conversation.id,
                              'human_audio_message': 'I see an apple.'})
        handle_user_response_v2('device/user_response_v2', payload)
        self.assertEqual(self.publish.call_args.args[1]['status'], 'error')
        handle_user_stop_v2('device/user_stop_v2', payload)
        self.assertEqual(self.publish.call_args.args[1]['status'], 'error')
        self.conversation.refresh_from_db()
        self.assertTrue(self.conversation.is_active)
        self.assertFalse(Message.objects.exists())

    @patch('agent_system_v2.agents.main_agent.invoke_agent_with_stream')
    def test_object_input_reaches_agent_as_device_event(self, invoke):
        invoke.return_value = {'ai_message': 'Welcome! What do you see?', 'words_used_id': []}
        handle_object_detected_v2('device/object_detected_v2', json.dumps(
            {'device_id': 'device-a', 'object_name': 'bottle'}))
        event = invoke.call_args.kwargs['user_message']
        self.assertEqual(json.loads(event.split('\n', 1)[1])['object_name'], 'bottle')
        self.assertTrue(Conversation.objects.filter(device_id='device-a', object_name='bottle').exists())
        self.assertFalse(Message.objects.filter(sender='human').exists())

    @patch('agent_system_v2.agents.main_agent.invoke_agent_with_stream')
    def test_unselected_chapter_does_not_create_conversation(self, invoke):
        self.owner.chapter_type = None
        self.owner.save()
        handle_object_detected_v2('device/object_detected_v2', json.dumps(
            {'device_id': 'device-a', 'object_name': 'bottle'}))
        invoke.assert_not_called()
        self.assertFalse(Conversation.objects.filter(object_name='bottle').exists())
        self.assertEqual(self.publish.call_args.args[1]['status'], 'error')

    @patch('agent_system_v2.agents.word_mastery_agent.invoke_word_mastery_agent')
    def test_foreign_vocabulary_cannot_advance(self, invoke):
        from user_system.models import Dictionary, UserStudyPlan, UserOngoingPlan
        from .mqtt_handlers import _process_word_mastery
        dictionary = Dictionary.objects.create(dict_name='Test curriculum')
        plan = UserStudyPlan.objects.create(user=self.other, dictionary=dictionary,
                                            is_activated=True, is_locked=False)
        word = UserOngoingPlan.objects.create(user=self.other, plan=plan, words='book',
                                              part_of_speech='noun', chinese_translation='书')
        results = _process_word_mastery(self.conversation, [word.id], 'A book.',
                                        'I see a book.', self.owner)
        self.assertEqual(results, ([], []))
        invoke.assert_not_called()
        word.refresh_from_db()
        self.assertEqual(word.learned_type, 'not_started')

    def test_review_thaws_due_words_only(self):
        from datetime import timedelta
        from django.utils import timezone
        from user_system.models import Dictionary, UserStudyPlan, UserOngoingPlan
        from .scheduled_tasks import thaw_frozen_words
        dictionary = Dictionary.objects.create(dict_name='Review curriculum')
        plan = UserStudyPlan.objects.create(user=self.owner, dictionary=dictionary)
        due = UserOngoingPlan.objects.create(user=self.owner, plan=plan, words='apple',
            part_of_speech='noun', chinese_translation='苹果', learned_type='learning', is_frozen=True)
        mastered = UserOngoingPlan.objects.create(user=self.owner, plan=plan, words='red',
            part_of_speech='adjective', chinese_translation='红', learned_type='mastered', is_frozen=True)
        UserOngoingPlan.objects.filter(id__in=[due.id, mastered.id]).update(
            updated_at=timezone.now() - timedelta(days=4))
        thaw_frozen_words()
        due.refresh_from_db()
        mastered.refresh_from_db()
        self.assertFalse(due.is_frozen)
        self.assertTrue(mastered.is_frozen)


class AgentAssemblyTests(TestCase):
    def test_pipeline_builds_without_network(self):
        from langchain_openai import ChatOpenAI
        from langgraph.checkpoint.memory import InMemorySaver
        from .agents import main_agent
        model = ChatOpenAI(api_key='test-only', model='glm-4.7-flash')
        with patch.object(main_agent, '_agent_instance', None), \
                patch.object(main_agent, 'get_zhipu_model', return_value=model), \
                patch.object(main_agent, 'get_checkpointer', return_value=InMemorySaver()):
            self.assertIsNotNone(main_agent.get_main_agent())
