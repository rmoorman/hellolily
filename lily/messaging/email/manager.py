import logging
import gc
import traceback

import anyjson
from django.conf import settings
from googleapiclient.errors import HttpError

from .builders.label import LabelBuilder
from .builders.message import MessageBuilder
from .connector import GmailConnector
from .credentials import InvalidCredentialsError
from .models.models import EmailLabel, EmailMessage, NoEmailMessageId


logger = logging.getLogger(__name__)


class ManagerError(Exception):
    pass


class SyncLimitReached(ManagerError):
    pass


class GmailManager(object):
    """
    Manager for handling in and output of EmailAccount that connects through Gmail Api.

    Attributes:
        connector: GmailConnector instance
        email_account: EmailAccount instance
        message_builder: MessageBuilder instance
        label_builder: LabelBuilder instance
    """
    def __init__(self, email_account):
        """
        Args:
            email_account (instance): EmailAccount instance

        Raises:
            ManagerError: if sync is not possible
        """
        self.email_account = email_account
        try:
            self.connector = GmailConnector(self.email_account)
        except InvalidCredentialsError:
            raise ManagerError
        else:
            self.message_builder = MessageBuilder(self)
            self.label_builder = LabelBuilder(self)

    def synchronize(self, **kwargs):
        """
        Synchronize complete email account.

        Arguments:
            limit (int, optional): maximum number of messages to synchronize
            full_sync (boolean, optional): if True, it does a complete scan of the EmailAccount

        Raises:
            SyncLimitReached: if limit is reached, this error is raised
        """
        self.synchronize_messages(**kwargs)
        self.update_unread_count()

    def synchronize_labels(self):
        """
        Synchronize all labels for email account.
        """
        labels = self.connector.get_label_list()
        for label in labels:
            self.label_builder.get_or_create_label(label)

    def synchronize_messages(self, limit=None, full_sync=False):
        """
        Fetch updated message info and batch update the info

        Arguments:
            limit (int, optional): maximum number of messages to synchronize
            full_sync (boolean, optional): if True, it does a complete scan of the EmailAccount

        Raises:
            SyncLimitReached: if limit is reached, this error is raised
        """
        logger.debug('Syncing messages for %s' % self.email_account.email_address)

        # Get the message ids from the messages to update
        if not full_sync and self.email_account.history_id:
            self.sync_by_history()
        else:
            self.sync_by_message_ids(limit=limit, full_sync=full_sync)

    def sync_by_message_ids(self, limit, full_sync):
        message_ids = self.connector.get_all_message_id_list()

        # Store history id in temporary column to make label batch sync quick
        if limit and not self.email_account.temp_history_id:
            self.email_account.temp_history_id = self.connector.history_id
            self.email_account.save()

        message_ids_full_download = set()
        message_ids_update_labels = set()
        # Check for message_ids that are saved as non email messages
        no_message_ids_in_db = set(
            NoEmailMessageId.objects.filter(
                account=self.email_account
            ).values_list('message_id', flat='true')
        )

        # Check for message_ids that are saved as email messages
        message_ids_in_db = set(
            EmailMessage.objects.filter(
                account=self.email_account
            ).values_list('message_id', flat='true')
        )

        # What do we need to do with every email message?
        for i, message_dict in enumerate(message_ids):
            logger.debug('Check for existing messages, %s/%s' % (i, len(message_ids)))
            if message_dict['id'] in no_message_ids_in_db:
                # Not an email, but chatmessage, skip
                pass
            elif message_dict['id'] not in message_ids_in_db:
                # If message is new, we need extra info from connector
                message_ids_full_download.add(message_dict['id'])
            else:
                # We only need to update the labels for this message
                message_ids_update_labels.add(message_dict['id'])

        message_ids_full_download = list(message_ids_full_download)
        # Synchronize full messages in batches
        for i in range(0, len(message_ids_full_download), int(settings.GMAIL_FULL_MESSAGE_BATCH_SIZE)):

            # Check if we hit the limit of how many messages to sync
            if limit and limit < i:
                raise SyncLimitReached

            logger.debug('Batch sync full messages (%(i)s/%(total)s to %(iplus)s/%(total)s)' % {
                'i': i,
                'total': len(message_ids_full_download),
                'iplus': min(i + int(settings.GMAIL_FULL_MESSAGE_BATCH_SIZE), len(message_ids_full_download)),
            })
            self._batch_sync_full_messages(message_ids_full_download[i:i + int(settings.GMAIL_FULL_MESSAGE_BATCH_SIZE)])

        # If there is a temporary history id, there is no need to sync all
        # labels, just set the temporary history id as the new history id.
        if not full_sync and self.email_account.temp_history_id:
            self.email_account.history_id = self.email_account.temp_history_id
            self.email_account.temp_history_id = None
            self.email_account.save()
        else:
            # Synchronize label info in batches
            message_ids_update_labels = list(message_ids_update_labels)
            for i in range(0, len(message_ids_update_labels), int(settings.GMAIL_LABEL_UPDATE_BATCH_SIZE)):
                logger.debug('Batch sync label info (%(i)s/%(total)s to %(iplus)s/%(total)s)' % {
                    'i': i,
                    'total': len(message_ids_update_labels),
                    'iplus': min(i + settings.GMAIL_LABEL_UPDATE_BATCH_SIZE, len(message_ids_update_labels)),
                })
                self._batch_sync_label_info(message_ids_update_labels[i:i + int(settings.GMAIL_LABEL_UPDATE_BATCH_SIZE)])
            self.connector.save_history_id()

        # Only if transaction was successful, we update the history ID
        logger.debug('Finished syncing, storing history id for %s' % self.email_account.email_address)

    def _batch_sync_full_messages(self, message_ids):
        """
        Fetch message info in a batch.

        Arguments:
            message_ids (list): message ids to get info for
        """
        messages_info = self.connector.get_message_list_info(message_ids)

        for message_id in message_ids:
            if message_id in messages_info:
                logger.debug('Storing message: %s, account %s' % (
                    message_id, self.email_account.email_address
                ))
                self.message_builder.store_message_info(messages_info[message_id], message_id)
                try:
                    self.message_builder.save()
                except Exception:
                    logger.exception('Couldn\'t save message %s for account %s' % (message_id, self.email_account.id))

            else:
                # Message was deleted, we need to remove it
                logger.debug('Deleting message %s, account %s' % (
                    message_id, self.email_account.email_address
                ))
                EmailMessage.objects.filter(message_id=message_id).delete()

    def _batch_sync_label_info(self, message_ids):
        """
        Fetch label info for messages in a batch.

        Args:
            message_ids (list): message ids to get info for
        """
        labels_info = self.connector.get_label_list_info(message_ids)

        for message_id in message_ids:
            if message_id in labels_info:
                logger.debug('Storing label info for message: %s, account %s' % (
                    message_id,
                    self.email_account.email_address
                ))
                self.message_builder.store_labels_for_message(labels_info.get(message_id, {}), message_id)
                try:
                    self.message_builder.save()
                except Exception:
                    logger.exception('Couldn\'t save message %s for account %s' % (message_id, self.email_account.id))
            else:
                # Message was deleted, we need to remove it
                logger.debug('Deleting message %s, account %s' % (
                    message_id, self.email_account.email_address
                ))
                EmailMessage.objects.filter(message_id=message_id).delete()

    def sync_by_history(self, history):
        """
        Synchronize emailaccount by history.

        Fetches the changed from the GMail api and updates the email direct without parsing
        """

        for history_item in history:
            logger.debug('parsing history %s' % history_item)
            # Get new messages
            if 'messagesAdded' in history_item:
                logger.debug('downloading messages %s' % [item['message']['id'] for item in history_item['messagesAdded']])
                self._batch_sync_full_messages(
                    [item['message']['id'] for item in history_item['messagesAdded']]
                )

            # Remove messages
            for message in history_item.get('messagesDeleted', []):
                logger.debug('deleting message %s' % message['message']['id'])
                EmailMessage.objects.filter(message_id=message['message']['id'], account=self.email_account).delete()

            # Make sure we have all the correct labels for
            update_labels_for_messages = []
            update_labels_for_messages.extend(history_item.get('labelsAdded', []))
            update_labels_for_messages.extend(history_item.get('labelsRemoved', []))

            if len(update_labels_for_messages):
                self._batch_sync_label_info([message['message']['id'] for message in update_labels_for_messages])

            # TODO: fix sync issues before incremental update of labels
            # # Add labels to existing messages
            # for message_dict in history_item.get('labelsAdded', []):
            #     logger.debug('labels added, message: %s' % message_dict['message']['id'])
            #     message = EmailMessage.objects.get(message_id=message_dict['message']['id'], account=self.email_account)
            #     for added_label_id in message_dict['labelIds']:
            #         if added_label_id == settings.GMAIL_UNREAD_LABEL:
            #             message.read = False
            #         else:
            #             message.labels.add(self.get_label(added_label_id))
            #     message.save()
            #
            # # Remove labels from existing messages
            # for message_dict in history_item.get('labelsRemoved', []):
            #     logger.debug('labels removed, message: %s' % message_dict['message']['id'])
            #     message = EmailMessage.objects.get(message_id=message_dict['message']['id'], account=self.email_account)
            #     for removed_label_id in message_dict['labelIds']:
            #         if removed_label_id == settings.GMAIL_UNREAD_LABEL:
            #             message.read = True
            #         else:
            #             message.labels.remove(self.get_label(removed_label_id))
            #     message.save()

        self.connector.save_history_id()

    def update_unread_count(self):
        """
        Update unread count on every label.
        """
        logger.debug('Updating unread count for every label, account %s' % self.email_account.email_address)
        for label in self.email_account.labels.all():
            unread_count = label.messages.filter(read=False).count()
            label.unread = unread_count
            label.save()

    def get_label(self, label_id):
        """
        Returns the label given the label_id

        Args:
            label_id (string): label_id of the label

        Returns:
            EmailLabel instance
        """
        try:
            label = EmailLabel.objects.get(account=self.email_account, label_id=label_id)
        except EmailLabel.DoesNotExist:
            label_info = self.connector.get_label_info(label_id)
            label = self.label_builder.get_or_create_label(label_info)[0]

        return label

    def get_attachment(self, message_id, attachment_id):
        """
        Returns the attachment given the message_id and attachment_id

        Args:
            message_id (string): message_id of the message
            attachment_id (string): attachment_id of the message

        Returns:
            dict with attachment info
        """
        return self.connector.get_attachment(message_id, attachment_id)

    def add_and_remove_labels_for_message(self, email_message, add_labels=[], remove_labels=[]):
        """
        Add and/or removes labels for the EmailMessage.

        Args:
            email_message (instance): EmailMessage instance
            add_labels (list, optional): list of label_ids to add
            remove_labels (list, optional): list of label_ids to remove
        """
        # We should do some tries to update
        for n in range(0, 6):
            existing_labels = self.connector.get_labels_from_message(email_message.message_id)

            labels = {}
            for label in remove_labels:
                if label in existing_labels and label != settings.GMAIL_SENT_LABEL:
                    labels.setdefault('removeLabelIds', []).append(label)

            for label in add_labels:
                # Temporary set traceback in logging to find out what triggers adding SENT label
                if label == settings.GMAIL_SENT_LABEL:
                    logger.warning('trying to add label SENT: %s' % traceback.print_stack())
                # UNREAD isn't added to the database as an available label, so do a separate check
                if label not in existing_labels and label != settings.GMAIL_SENT_LABEL:
                    if email_message.account.labels.filter(label_id=label).exists() or label == settings.GMAIL_UNREAD_LABEL:
                        labels.setdefault('addLabelIds', []).append(label)

            if labels:
                try:
                    message_dict = self.connector.update_labels(email_message.message_id, labels)
                except HttpError, e:
                    error = anyjson.loads(e.content)
                    error = error.get('error', error)
                    if error.get('code') != 400:
                        # No label error, raise
                        raise
                else:
                    full_message_dict = self.connector.get_message_info(email_message.message_id)
                    # Store updated message
                    self.message_builder.store_message_info(full_message_dict, message_dict['id'])
                    self.message_builder.save()
                    break

        self.update_unread_count()

    def toggle_read_email_message(self, email_message, read=True):
        """
        Mark message as read or unread.

        Args:
            email_message(instance): EmailMessage instance
            read (bool, optional): If True, mark message as read
        """
        if read:
            self.add_and_remove_labels_for_message(email_message, remove_labels=[settings.GMAIL_UNREAD_LABEL])
        else:
            self.add_and_remove_labels_for_message(email_message, add_labels=[settings.GMAIL_UNREAD_LABEL])

    def archive_email_message(self, email_message):
        """
        Archive message by removing all labels except for possible UNREAD label

        Args:
            email_message(instance): EmailMessage instance
        """
        existing_labels = self.connector.get_labels_from_message(email_message.message_id)

        self.add_and_remove_labels_for_message(email_message, remove_labels=existing_labels)

    def trash_email_message(self, email_message):
        """
        Trash current EmailMessage.

        Args:
            email_message (instance): EmailMessage instance
        """
        message_dict = self.connector.trash_email_message(email_message.message_id)
        full_message_dict = self.connector.get_message_info(message_dict['id'])

        # Store updated message
        self.message_builder.store_message_info(full_message_dict, message_dict['id'])
        self.message_builder.save()
        self.update_unread_count()

    def delete_email_message(self, email_message):
        """
        Trash current EmailMessage.

        Args:
            email_message (instance): EmailMessage instance
        """
        self.connector.delete_email_message(email_message.message_id)
        self.update_unread_count()

    def send_email_message(self, email_message, thread_id=None):
        """
        Send email.

        Args:
            email_message (instance): Email instance
            thread_id (string): Thread ID of original message that is replied or forwarded on
        """
        # Send message
        message_dict = self.connector.send_email_message(email_message.as_string(), thread_id)
        full_message_dict = self.connector.get_message_info(message_dict['id'])

        # Store updated message
        self.message_builder.store_message_info(full_message_dict, message_dict['id'])
        self.message_builder.save()
        self.update_unread_count()

    def create_draft_email_message(self, email_message):
        """
        Create email draft.

        Args:
            email_message (instance): Email instance
        """
        # Send message
        message_dict = self.connector.create_draft_email_message(email_message.as_string())
        full_message_dict = self.connector.get_message_info(message_dict['message']['id'])

        # Store updated message
        self.message_builder.store_message_info(full_message_dict, message_dict['id'])
        self.message_builder.message.draft_id = message_dict.get('id', '')
        self.message_builder.save()
        self.update_unread_count()

    def update_draft_email_message(self, email_message, draft_id):
        """
        Update email draft.

        Args:
            email_message (instance): Email instance
            draft_id (string): id of current draft
        """
        # Send message
        message_dict = self.connector.update_draft_email_message(email_message.as_string(), draft_id)
        full_message_dict = self.connector.get_message_info(message_dict['message']['id'])

        # Store updated message
        self.message_builder.store_message_info(full_message_dict, message_dict['id'])
        self.message_builder.message.draft_id = message_dict.get('id', '')
        self.message_builder.save()
        self.update_unread_count()

    def cleanup(self):
        """
        Cleanup references, to prevent reference cycle.
        """
        self.message_builder.cleanup()
        self.message_builder = None
        self.label_builder.cleanup()
        self.label_builder = None
        self.connector.cleanup()
        self.connector = None
        self.email_account = None

        gc.collect()
