from django.test import TestCase

from lily.google.gmail.builders.label import LabelBuilder
from lily.google.gmail.factories import GmailAccountFactory
from lily.google.gmail.manager import GmailManager
from lily.google.gmail.tests.dummy_data.labels import LABEL_INBOX, LABEL_NOTES


class MessageBuilderTestCase(TestCase):
    def test_correct_initialization(self):
        manager = GmailManager(GmailAccountFactory())
        builder = LabelBuilder(manager)

        self.assertIsNotNone(builder)

    def test_create_label(self):
        manager = GmailManager(GmailAccountFactory())
        builder = LabelBuilder(manager)

        label, created = builder.get_or_create_label(LABEL_INBOX)

        self.assertIsNotNone(label)
        self.assertTrue(created)

    def test_label_not_created_on_second_call(self):
        manager = GmailManager(GmailAccountFactory())
        builder = LabelBuilder(manager)

        label = builder.get_or_create_label(LABEL_INBOX)[0]
        label.save()
        label, created = builder.get_or_create_label(LABEL_INBOX)

        self.assertIsNotNone(label)
        self.assertFalse(created)

    def test_label_has_label_id(self):
        manager = GmailManager(GmailAccountFactory())
        builder = LabelBuilder(manager)

        label = builder.get_or_create_label(LABEL_INBOX)[0]

        self.assertEqual(label.label_id, LABEL_INBOX['id'])

    def test_label_has_name(self):
        manager = GmailManager(GmailAccountFactory())
        builder = LabelBuilder(manager)

        label = builder.get_or_create_label(LABEL_INBOX)[0]

        self.assertEqual(label.name, LABEL_INBOX['name'])

    def test_label_has_correct_account(self):
        account = GmailAccountFactory()
        manager = GmailManager(account)
        builder = LabelBuilder(manager)

        label = builder.get_or_create_label(LABEL_INBOX)[0]

        self.assertEqual(label.account, account)

    def test_label_has_correct_system_type(self):
        account = GmailAccountFactory()
        manager = GmailManager(account)
        builder = LabelBuilder(manager)

        label = builder.get_or_create_label(LABEL_NOTES)[0]

        self.assertEqual(label.type, LABEL_NOTES['type'])

    def test_label_has_correct_user_type(self):
        account = GmailAccountFactory()
        manager = GmailManager(account)
        builder = LabelBuilder(manager)

        label = builder.get_or_create_label(LABEL_INBOX)[0]

        self.assertEqual(label.type, LABEL_INBOX['type'])
