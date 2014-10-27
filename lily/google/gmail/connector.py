from lily.google.credentials import get_credentials
from lily.google.services import build_gmail_service


class ConnectorError(Exception):
    pass


class AuthError(ConnectorError):
    pass


class GmailConnector(object):
    service = None

    def __init__(self, gmail_account):
        self.gmail_account = gmail_account

    def get_service(self):
        """
        Get or create GMail api service
        """
        if not self.service:
            credentials = get_credentials(self.gmail_account.user)
            self.service = build_gmail_service(credentials)
        return self.service

    def get_new_or_changed_message_ids(self):
        """
        Get latest message ids and thread ids
        """
        if not self.gmail_account.is_authorized:
            raise AuthError

        if self.gmail_account.history_id:
            return self.get_history()
        else:
            return self.get_all_messages()

    def get_history(self):
        service = self.get_service()
        history_id = self.gmail_account.history_id
        history = service.users().history().list(userId='me', startHistoryId=history_id).execute()

        messages = []
        if 'history' in history:
            for history_item in history['history']:
                messages += history_item['messages']
            self.gmail_account.history_id = history['historyId']
            self.gmail_account.save()

        while 'nextPageToken' in history:
            page_token = history['nextPageToken']
            history = service.users().history().list(userId='me', startHistoryId=history_id, pageToken=page_token).execute()
            for history_item in history['history']:
                messages += history_item['messages']
        return messages

    def get_all_messages(self):
        service = self.get_service()
        response = service.users().messages().list(userId='me').execute()

        messages = response['messages'] if 'messages' in response else []

        while 'nextPageToken' in response:
            page_token = response['nextPageToken']
            response = service.users().messages().list(userId='me', pageToken=page_token).execute()
            messages.extend(response['messages'])

        # Store history_id
        if messages:
            message = self.get_message_info(messages[0])
            self.gmail_account.history_id = message['historyId']
            self.gmail_account.save()

        return messages

    def get_message_info(self, message_id):
        service = self.get_service()
        message = service.users().messages().get(message_id).execute()
        return message

    def get_all_labels(self):
        service = self.get_service()
        response = service.users().labels().list(userId='me').execute()
        return response['labels']
