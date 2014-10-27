from django.test import TestCase
from django.test.utils import override_settings
from mock import MagicMock, Mock
from lily.google.gmail.builders.label import LabelBuilder
from lily.google.gmail.builders.message import MessageBuilder

from lily.google.gmail.factories import GmailAccountFactory, GmailMessageFactory, GmailLabelFactory
from lily.google.gmail.manager import GmailManager
from lily.google.gmail.tests.dummy_data.labels import LABEL_INBOX, LABEL_LIST
from lily.google.gmail.tests.dummy_data.messages import MESSAGE_HTML


@override_settings(STATICFILES_STORAGE='pipeline.storage.NonPackagingPipelineStorage', PIPELINE_ENABLED=False)
class GmailManagerTestCase(TestCase):
    def _m_connector(self):
        connector = MagicMock()

        # Messages
        connector.get_new_or_changed_message_ids.return_value = ([{"id": "1494e0cb5907274e", "threadId": "1494e0cb5907274e"}])
        connector.get_message_info.return_value = MESSAGE_HTML

        # Labels
        connector.get_all_labels.return_value = LABEL_LIST['labels']
        connector.get_label_info.return_value = LABEL_INBOX

        return connector

    def _m_message_builder(self):
        message_builder = MagicMock()
        message_builder.get_or_create_message.return_value = GmailMessageFactory(), True

        return message_builder

    def _m_label_builder(self):
        label_builder = Mock()
        label_builder.get_or_create_label.return_value = GmailLabelFactory.build(name='INBOX'), True
        return label_builder

    def test_manager_needs_gmail_account_on_init(self):
        with (self.assertRaises(TypeError)):
            GmailManager()

        manager = GmailManager(GmailAccountFactory.build())

        self.assertEqual(manager.gmail_account, GmailAccountFactory.build())

    def test_manager_should_setup_message_builder_on_init(self):
        manager = GmailManager(GmailAccountFactory.build())
        self.assertIsNotNone(manager.message_builder)
        self.assertEqual(type(manager.message_builder), MessageBuilder)

    def test_manager_should_setup_label_builder_on_init(self):
        manager = GmailManager(GmailAccountFactory.build())
        self.assertIsNotNone(manager.label_builder)
        self.assertEqual(type(manager.label_builder), LabelBuilder)

    def test_manager_should_have_synchronize_method(self):
        manager = GmailManager(GmailAccountFactory.build())

        self.assertIn('synchronize', dir(manager))

    def test_synchronize_should_fetch_message_ids(self):
        manager = GmailManager(GmailAccountFactory.build())
        manager.connector = self._m_connector()
        manager.message_builder = self._m_message_builder()
        manager.label_builder = self._m_label_builder()

        manager.synchronize()

        manager.connector.get_new_or_changed_message_ids.assert_called_once_with()

    def test_synchronize_should_ask_builder_to_create_new_message(self):
        manager = GmailManager(GmailAccountFactory())
        manager.connector = self._m_connector()
        manager.message_builder = self._m_message_builder()

        manager.synchronize()

        manager.message_builder.get_or_create_message.assert_called_with(
            {"id": "1494e0cb5907274e", "threadId": "1494e0cb5907274e"}
        )

    def test_synchronize_should_ask_builder_to_save_message_info(self):
        manager = GmailManager(GmailAccountFactory())
        manager.connector = self._m_connector()
        manager.message_builder = self._m_message_builder()

        manager.synchronize()

        manager.message_builder.save_message_info.assert_called_with(MESSAGE_HTML)

    def test_new_message_should_get_extra_info(self):
        manager = GmailManager(GmailAccountFactory())
        manager.connector = self._m_connector()
        manager.message_builder = self._m_message_builder()

        manager.synchronize()

        manager.connector.get_message_info.assert_called_with('1494e0cb5907274e')

    def test_existing_message_should_not_get_extra_info(self):
        manager = GmailManager(GmailAccountFactory())
        manager.connector = self._m_connector()
        message = GmailMessageFactory()
        message_builder = MagicMock()
        message_builder.get_or_create_message.return_value = message, True
        manager.message_builder = message_builder
        manager.synchronize()
        message_builder.get_or_create_message.return_value = message, False
        manager.connector.reset_mock()

        manager.synchronize()

        self.assertEqual(len(manager.connector.get_message_info.mock_calls), 0)

    def test_existing_message_should_get_label_info(self):
        manager = GmailManager(GmailAccountFactory())
        manager.connector = self._m_connector()
        message = GmailMessageFactory()
        message_builder = MagicMock()
        message_builder.get_or_create_message.return_value = message, True
        manager.message_builder = message_builder
        manager.synchronize()
        message_builder.get_or_create_message.return_value = message, False
        manager.connector.reset_mock()

        manager.synchronize()

        self.assertEqual(len(manager.connector.get_message_labels.mock_calls), 1)

    def test_existing_message_should_not_store_extra_info(self):
        manager = GmailManager(GmailAccountFactory())
        manager.connector = self._m_connector()
        message = GmailMessageFactory()
        message_builder = MagicMock()
        message_builder.get_or_create_message.return_value = message, True
        manager.message_builder = message_builder
        manager.synchronize()
        message_builder.get_or_create_message.return_value = message, False
        manager.connector.reset_mock()

        manager.synchronize()

        self.assertEqual(len(manager.message_builder.save_message_info.mock_calls), 1)

    def test_manager_asked_for_label_should_return_label(self):
        account = GmailAccountFactory()
        manager = GmailManager(account)
        f_label = GmailLabelFactory(account=account, label_id='INBOX')

        label = manager.get_label('INBOX')

        self.assertEqual(label, f_label)

    def test_manager_should_on_sync_get_all_labels(self):
        account = GmailAccountFactory()
        manager = GmailManager(account)
        manager.connector = self._m_connector()
        manager.message_builder = self._m_message_builder()

        manager.synchronize()

        manager.connector.get_all_labels.assert_called_with()

    def test_manager_should_create_labels_on_sync(self):
        account = GmailAccountFactory()
        manager = GmailManager(account)
        manager.connector = self._m_connector()
        manager.message_builder = self._m_message_builder()
        manager.label_builder = self._m_label_builder()

        manager.synchronize()

        self.assertEqual(manager.label_builder.get_or_create_label.call_count, 5)

    def test_manager_asked_for_new_label_should_ask_connector_for_label(self):
        account = GmailAccountFactory()
        manager = GmailManager(account)
        manager.connector = self._m_connector()

        manager.get_label('INBOX')

        manager.connector.get_label_info.assert_called_with('INBOX')

    def test_manager_asked_for_new_label_should_ask_builder_to_create_label(self):
        account = GmailAccountFactory()
        manager = GmailManager(account)
        manager.connector = self._m_connector()
        manager.label_builder = self._m_label_builder()

        manager.get_label('INBOX')

        manager.label_builder.get_or_create_label.assert_called_with(LABEL_INBOX)
