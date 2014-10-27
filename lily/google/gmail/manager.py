from lily.google.gmail.builders.label import LabelBuilder
from lily.google.gmail.builders.message import MessageBuilder
from lily.google.gmail.connector import GmailConnector
from lily.google.gmail.models import GmailLabel


class ManagerError(Exception):
    pass


class GmailManager(object):
    def __init__(self, gmail_account):
        self.connector = GmailConnector(gmail_account)
        self.gmail_account = gmail_account
        self.message_builder = MessageBuilder(self)
        self.label_builder = LabelBuilder(self)

    def synchronize(self):
        self.synchronize_labels()
        self.synchronize_messsages()

    def synchronize_labels(self):
        labels = self.connector.get_all_labels()
        for label in labels:
            self.label_builder.get_or_create_label(label)

    def synchronize_messsages(self):
        messages = self.connector.get_new_or_changed_message_ids()
        for message_dict in messages:
            message, created = self.message_builder.get_or_create_message(message_dict)
            if created:
                message_info = self.connector.get_message_info(message_dict['id'])
                self.message_builder.save_message_info(message_info)
            else:
                self.connector.get_message_labels(message.message_id)

            self.message_builder.save()

    def get_label(self, label_id):
        try:
            label = GmailLabel.objects.get(account=self.gmail_account, label_id=label_id)
        except GmailLabel.DoesNotExist:
            label_info = self.connector.get_label_info(label_id)
            self.label_builder.get_or_create_label(label_info)
            label = None

        return label
