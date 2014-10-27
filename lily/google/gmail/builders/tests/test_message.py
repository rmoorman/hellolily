import datetime
from django.db import IntegrityError
from django.test import TestCase
from django.test.utils import override_settings
from mock import MagicMock
import pytz

from lily.google.gmail.builders.message import MessageBuilder, InvalidMessageDictError
from lily.google.gmail.factories import GmailAccountFactory, GmailMessageFactory, GmailLabelFactory
from lily.google.gmail.manager import GmailManager
from lily.google.gmail.tests.dummy_data.messages import MESSAGE_HTML, MESSAGE_HTML_BODY, \
    MESSAGE_PLAIN_HTML, MESSAGE_PLAIN_HTML_TEXT, MESSAGE_PLAIN_HTML_BODY, MESSAGE_UNREAD


@override_settings(STATICFILES_STORAGE='pipeline.storage.NonPackagingPipelineStorage', PIPELINE_ENABLED=False)
class MessageBuilderTestCase(TestCase):
    def test_false_initialization(self):
        with self.assertRaises(TypeError):
            MessageBuilder()

    def test_correct_initialization(self):
        manager = GmailManager(GmailAccountFactory())
        builder = MessageBuilder(manager)

        self.assertEqual(builder.manager, manager)

    def test_save_message_info_needs_thread(self):
        builder = MessageBuilder(GmailManager(GmailAccountFactory()))
        builder.message = GmailMessageFactory()

        with self.assertRaises(InvalidMessageDictError):
            builder.save_message_info({'snippet': 'fake snippet'})

    def test_message_should_have_thread_id(self):
        account = GmailAccountFactory()
        builder = MessageBuilder(GmailManager(account))
        builder.message = GmailMessageFactory()
        builder.manager.get_label = MagicMock(return_value=GmailLabelFactory(account=account))

        builder.save_message_info(MESSAGE_HTML)

        self.assertEqual(builder.message.thread_id, MESSAGE_HTML['threadId'])

    def test_message_should_have_snippet(self):
        account = GmailAccountFactory()
        builder = MessageBuilder(GmailManager(account))
        builder.message = GmailMessageFactory()
        builder.manager.get_label = MagicMock(return_value=GmailLabelFactory(account=account))

        builder.save_message_info(MESSAGE_HTML)

        self.assertEqual(builder.message.snippet, MESSAGE_HTML['snippet'])

    def test_message_should_have_html_body(self):
        account = GmailAccountFactory()
        builder = MessageBuilder(GmailManager(account))
        builder.message = GmailMessageFactory()
        builder.manager.get_label = MagicMock(return_value=GmailLabelFactory(account=account))

        builder.save_message_info(MESSAGE_HTML)

        self.assertEqual(builder.message.body_html, MESSAGE_HTML_BODY)

    def test_message_should_have_html_plain_body(self):
        account = GmailAccountFactory()
        builder = MessageBuilder(GmailManager(account))
        builder.message = GmailMessageFactory()
        builder.manager.get_label = MagicMock(return_value=GmailLabelFactory(account=account))

        builder.save_message_info(MESSAGE_PLAIN_HTML)

        self.assertEqual(builder.message.body_html, MESSAGE_PLAIN_HTML_BODY)
        self.assertEqual(builder.message.body_text, MESSAGE_PLAIN_HTML_TEXT)

    def test_message_should_be_read(self):
        account = GmailAccountFactory()
        builder = MessageBuilder(GmailManager(account))
        builder.message = GmailMessageFactory()
        builder.manager.get_label = MagicMock(return_value=GmailLabelFactory(account=account))

        builder.save_message_info(MESSAGE_HTML)

        self.assertEqual(builder.message.read, True)

    def test_message_should_be_unread(self):
        account = GmailAccountFactory()
        builder = MessageBuilder(GmailManager(account))
        builder.message = GmailMessageFactory()
        builder.manager.get_label = MagicMock(return_value=GmailLabelFactory(account=account))

        builder.save_message_info(MESSAGE_UNREAD)

        self.assertEqual(builder.message.read, False)

    def test_message_should_have_headers(self):
        account = GmailAccountFactory()
        builder = MessageBuilder(GmailManager(account))
        builder.message = GmailMessageFactory()
        builder.manager.get_label = MagicMock(return_value=GmailLabelFactory(account=account))


        builder.save_message_info(MESSAGE_UNREAD)

        self.assertEqual(len(builder.headers), 17)

    def test_message_should_have_sent_date(self):
        account = GmailAccountFactory()
        builder = MessageBuilder(GmailManager(account))
        builder.message = GmailMessageFactory()
        date = datetime.datetime(2014, 10, 29, 7, 54, 41, 0, pytz.UTC)
        builder.manager.get_label = MagicMock(return_value=GmailLabelFactory(account=account))

        builder.save_message_info(MESSAGE_UNREAD)

        self.assertEqual(builder.message.sent_date, date)

    def test_message_should_have_subject(self):
        account = GmailAccountFactory()
        builder = MessageBuilder(GmailManager(account))
        builder.message = GmailMessageFactory()
        builder.manager.get_label = MagicMock(return_value=GmailLabelFactory(account=account))

        builder.save_message_info(MESSAGE_UNREAD)

        self.assertEqual(builder.message.subject, 'test')

    def test_message_should_have_all_labels(self):
        account = GmailAccountFactory()
        builder = MessageBuilder(GmailManager(account))
        builder.message = GmailMessageFactory()
        labels = [GmailLabelFactory(account=account) for i in range(3)]
        builder.manager.get_label = MagicMock(side_effect=labels)

        builder.save_message_info(MESSAGE_UNREAD)

        self.assertEqual(len(builder.labels), 3)
        self.assertIsNotNone(builder.labels[0].label_id)
