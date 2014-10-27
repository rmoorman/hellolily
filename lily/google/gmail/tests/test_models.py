import datetime
from django.db import IntegrityError
from django.test import TestCase
import pytz

from lily.google.gmail.factories import GmailAccountFactory, GmailMessageFactory, GmailHeaderFactory, GmailLabelFactory
from lily.google.gmail.models import GmailAccount, GmailMessage, GmailHeader, GmailLabel
from lily.google.gmail.tests.dummy_data.messages import MESSAGE_HTML_BODY
from lily.users.factories import CustomUserFactory


class GmailAccountTestCase(TestCase):
    def test_gmail_account_default_not_authorized(self):
        account = GmailAccount()
        self.assertFalse(account.is_authorized)

    def test_gmail_account_has_user(self):
        account = GmailAccount()
        account.user = CustomUserFactory()
        account.save()

        self.assertIsNotNone(account.pk)

    def test_gmail_account_has_default_empty_history_id(self):
        account = GmailAccount()
        self.assertEqual(account.history_id, None)

    def test_gmail_account_can_have_history_id_set(self):
        account = GmailAccount()
        account.user = CustomUserFactory()
        account.history_id = 1234
        account.save()


class GmailMessageTestCase(TestCase):
    def _message_with_required_fields(self):
        account = GmailAccountFactory()
        message = GmailMessage()
        message.account = account
        message.message_id = '14952c7eca603cc3'
        message.thread_id = '14952c7eca603cc2'

        message.save()

        return message

    def test_gmail_message_has_required_fields(self):
        message = GmailMessage()

        with self.assertRaises(IntegrityError):
            message.save()

    def test_gmail_message_should_save_on_required_fields(self):
        account = GmailAccountFactory()
        message = GmailMessage()

        message.account = account
        message.message_id = '14952c7eca603cc3'
        message.thread_id = '14952c7eca603cc2'

        message.save()

        saved_message = GmailMessage.objects.get(pk=message.pk)
        self.assertIsNotNone(saved_message.pk)
        self.assertEqual(saved_message.account, account)
        self.assertEqual(saved_message.message_id, '14952c7eca603cc3')
        self.assertEqual(saved_message.thread_id, '14952c7eca603cc2')
        self.assertIsNotNone(saved_message.sent_date)

    def test_gmail_message_is_unique_on_account_and_message_id(self):
        account = GmailAccountFactory()
        message = GmailMessage()

        message.account = account
        message.message_id = '14952c7eca603cc3'
        message.thread_id = '14952c7eca603cc2'

        message.save()

        messag_double = GmailMessage()
        messag_double.account = account
        messag_double.message_id = '14952c7eca603cc3'
        messag_double.thread_id = '14952c7eca603cc2'

        with self.assertRaises(IntegrityError):
            messag_double.save()

    def test_gmail_can_have_snippet(self):
        message = self._message_with_required_fields()
        snippet = 'Code School - Learn by doing Ready to learn but not sure where to get started? Code School offers'
        message.snippet = snippet

        message.save()

        saved_message = GmailMessage.objects.get(pk=message.pk)
        self.assertEqual(saved_message.snippet, snippet)

    def test_gmail_can_have_body_html(self):
        message = self._message_with_required_fields()
        message.body_html = MESSAGE_HTML_BODY

        message.save()

        saved_message = GmailMessage.objects.get(pk=message.pk)

        self.assertEqual(saved_message.body_html, MESSAGE_HTML_BODY)

    def test_gmail_can_have_body_text(self):
        message = self._message_with_required_fields()
        message.body_text = 'text body'

        message.save()

        saved_message = GmailMessage.objects.get(pk=message.pk)
        self.assertEqual(saved_message.body_text, 'text body')

    def test_gmail_message_is_unread(self):
        message = self._message_with_required_fields()

        self.assertFalse(message.read)

    def test_gmail_message_can_be_set_read(self):
        message = self._message_with_required_fields()

        message.read = True
        message.save()

        self.assertTrue(message.read)

    def test_gmail_message_can_have_sent_date(self):
        message = self._message_with_required_fields()

        date = datetime.datetime.now(pytz.utc) - datetime.timedelta(days=1)
        message.sent_date = date
        message.save()

        self.assertTrue(message.sent_date, date)

    def test_gmail_message_can_have_subject(self):
        message = self._message_with_required_fields()

        message.subject = 'test subject'
        message.save()

        self.assertTrue(message.subject, 'test subject')

    def test_gmail_message_can_have_header(self):
        message = self._message_with_required_fields()

        self.assertEqual(message.headers.count(), 0)

        GmailHeaderFactory(message=message, name='testing header')

        self.assertEqual(message.headers.count(), 1)
        self.assertEqual(message.headers.first().name, 'testing header')

    def test_gmail_message_can_have_label(self):
        message = self._message_with_required_fields()

        self.assertEqual(message.labels.count(), 0)

        label = GmailLabelFactory(account=message.account, name='testing label')
        label.messages.add(message)

        self.assertEqual(message.labels.count(), 1)
        self.assertEqual(message.labels.first().name, 'testing label')


class GmailHeadersTestCase(TestCase):
    def test_gmail_header_should_has_required_fields(self):
        header = GmailHeader()

        with self.assertRaises(IntegrityError):
            header.save()

    def test_gmail_header_should_save_on_required_fields(self):
        email = GmailMessageFactory()
        header = GmailHeader()

        header.message = email
        header.name = 'From'
        header.value = 'Code School <faculty@codeschool.com>'
        header.save()

        saved_header = GmailHeader.objects.get(pk=header.pk)
        self.assertEqual(saved_header.name, 'From')
        self.assertEqual(saved_header.value, 'Code School <faculty@codeschool.com>')


class GmailLabelTestCase(TestCase):
    def test_gmail_label_has_required_fields(self):
        label = GmailLabel()

        with self.assertRaises(IntegrityError):
            label.save()

    def test_gmail_message_should_save_on_required_fields(self):
        label = GmailLabel()

        label.account = GmailAccountFactory()
        label.label_id = 'INBOX'
        label.name = 'INBOX'
        label.type = 'system'

        label.save()

        saved_label = GmailLabel.objects.first()
        self.assertEqual(saved_label.label_id, 'INBOX')
        self.assertEqual(saved_label.name, 'INBOX')
        self.assertEqual(saved_label.type, 'system')

    def test_gmail_label_can_have_messages(self):
        label = GmailLabel()

        label.account = GmailAccountFactory()
        label.label_id = 'INBOX'
        label.name = 'INBOX'
        label.type = 'system'

        label.save()
        self.assertEqual(label.messages.count(), 0)
        message = GmailMessageFactory()
        message.labels.add(label)

        self.assertEqual(label.messages.count(), 1)
