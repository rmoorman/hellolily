from django.test import TestCase
from django.test.utils import override_settings
from mock import MagicMock, call

from lily.google.gmail.connector import GmailConnector, AuthError
from lily.google.gmail.factories import GmailAccountFactory
from lily.google.gmail.tests.dummy_data.history_list import HISTORY_LIST_WITH_NEXT_PAGE, HISTORY_LIST_WITHOUT_NEXT_PAGE
from lily.google.gmail.tests.dummy_data.labels import LABEL_LIST
from lily.google.gmail.tests.dummy_data.message_list import MESSAGE_LIST_WITH_NEXT_PAGE, MESSAGE_LIST_WITHOUT_NEXT_PAGE
from lily.google.gmail.tests.dummy_data.messages import MESSAGE_HTML


@override_settings(STATICFILES_STORAGE='pipeline.storage.NonPackagingPipelineStorage', PIPELINE_ENABLED=False)
class GmailConnectorTestCase(TestCase):
    def test_connector_should_get_gmail_account_on_init(self):
        with (self.assertRaises(TypeError)):
            GmailConnector()

        GmailConnector(GmailAccountFactory.build())

    def test_connector_raises_error_on_no_auth(self):
        connector = GmailConnector(GmailAccountFactory.build())

        with (self.assertRaises(AuthError)):
            connector.get_new_or_changed_message_ids()

    def _m_service(self):
        # Setup service
        service = MagicMock()
        users = service.users.return_value

        # Messages
        messages = users.messages.return_value

        # List Messages
        list = messages.list.return_value
        list.execute.side_effect = [MESSAGE_LIST_WITH_NEXT_PAGE, MESSAGE_LIST_WITHOUT_NEXT_PAGE]

        # Get message
        get = messages.get.return_value
        get.execute.side_effect = [MESSAGE_HTML]

        # History
        history = users.history.return_value

        # History list
        list = history.list.return_value
        list.execute.side_effect = [HISTORY_LIST_WITH_NEXT_PAGE, HISTORY_LIST_WITHOUT_NEXT_PAGE]

        # Labels
        labels = users.labels.return_value

        # Labels list
        list = labels.list.return_value
        list.execute.return_value = LABEL_LIST

        return service

    def test_synchronize_should_not_raise_error_on_auth_ok(self):
        connector = GmailConnector(GmailAccountFactory.build(is_authorized=True))
        connector.service = MagicMock()
        connector.get_new_or_changed_message_ids()

    def test_synchronize_should_fetch_all_messages_from_service(self):
        connector = GmailConnector(GmailAccountFactory(is_authorized=True))

        # Setup service
        service = self._m_service()
        connector.service = service

        message_ids = connector.get_new_or_changed_message_ids()

        self.assertEquals(
            service.users().messages().list.call_args_list,
            [call(userId='me'), call(pageToken='03260194651002044827', userId='me')]
        )

        self.assertEqual(len(message_ids), 2)
        self.assertEqual(message_ids[0]['id'], '14952c7eca603cc3')
        self.assertEqual(message_ids[0]['threadId'], '14952c7eca603cc3')
        self.assertEqual(message_ids[1]['id'], '149526f469dd928e')
        self.assertEqual(message_ids[1]['threadId'], '14951ab5b3a189bf')

    def test_synchronize_should_store_history_id(self):
        account = GmailAccountFactory(is_authorized=True)
        connector = GmailConnector(account)

        # Setup service
        service = self._m_service()
        connector.service = service

        connector.get_new_or_changed_message_ids()

        self.assertEqual(account.history_id, '306232')

    def test_synchronize_should_fetch_history_when_history_id_exists(self):
        connector = GmailConnector(GmailAccountFactory(is_authorized=True, history_id=9))

        # Setup service
        service = self._m_service()
        connector.service = service

        message_ids = connector.get_new_or_changed_message_ids()

        self.assertEquals(service.users().history().list.call_args_list, [
            call(userId='me', startHistoryId=9),
            call(userId='me', startHistoryId=9, pageToken='fake next page')
        ])

        self.assertEqual(len(message_ids), 2)

        self.assertEqual(message_ids[0]['id'], '149526f469dd928e')
        self.assertEqual(message_ids[0]['threadId'], '14951ab5b3a189bf')
        self.assertEqual(message_ids[1]['id'], '149526f469dd928e')
        self.assertEqual(message_ids[1]['threadId'], '14951ab5b3a189bf')

    def test_synchronize_should_get_history_on_second_call(self):
        account = GmailAccountFactory(is_authorized=True)
        connector = GmailConnector(account)

        # Setup service
        service = self._m_service()
        connector.service = service

        connector.get_new_or_changed_message_ids()
        connector.get_new_or_changed_message_ids()

        self.assertEquals(service.users().history().list.call_args_list, [
            call(userId='me', startHistoryId='306232'),
            call(userId='me', startHistoryId='306232', pageToken='fake next page')
        ])

    def test_can_get_message_info_can_be_called(self):
        connector = GmailConnector(GmailAccountFactory(is_authorized=True, history_id=9))

        # Setup service
        service = self._m_service()
        connector.service = service

        connector.get_message_info('1494e0cb5907274e')

    def test_get_message_info_should_call_service(self):
        connector = GmailConnector(GmailAccountFactory(is_authorized=True, history_id=9))

        # Setup service
        service = self._m_service()
        connector.service = service

        connector.get_message_info('14952c7eca603cc3')

        service.users().messages().get.assert_called_with('14952c7eca603cc3')

    def test_get_message_info_should_get_info(self):
        connector = GmailConnector(GmailAccountFactory(is_authorized=True, history_id=9))

        # Setup service
        service = self._m_service()
        connector.service = service

        message = connector.get_message_info('14952c7eca603cc3')

        self.assertEqual(message, MESSAGE_HTML)

    def test_get_all_labels_should_return_all_labels(self):
        connector = GmailConnector(GmailAccountFactory(is_authorized=True, history_id=9))

        # Setup service
        service = self._m_service()
        connector.service = service

        labels = connector.get_all_labels()

        self.assertEqual(len(labels), 5)
