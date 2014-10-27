import base64
import email
import datetime
from bs4 import BeautifulSoup, UnicodeDammit
import pytz

from lily.google.gmail.models import GmailMessage, GmailHeader


class BaseMessageBuilderError(Exception):
    pass


class InvalidMessageDictError(BaseMessageBuilderError):
    pass


class MessageBuilder(object):
    """
    Builder to get, create or update Messages
    """

    def __init__(self, manager):
        self.manager = manager
        self.message = None
        self.labels = []
        self.headers = []

    def get_or_create_message(self, message_dict):
        """
        Get or create Message.

        Arguments:
            message_dict (dict): with label information

        Returns:
            message (instance): unsaved message
            created (boolean): True if label is created
        """
        if 'id' not in message_dict or 'threadId' not in message_dict:
            raise InvalidMessageDictError

        created = False
        try:
            self.message = GmailMessage.get(
                message_id=message_dict['id'],
                account=self.manager.gmail_account,
            )
        except GmailMessage.DoesNotExist:
            self.message = GmailMessage(
                message_id=message_dict['id'],
                account=self.manager.gmail_account,
            )
            created = True

        self.message.thread_id = message_dict['threadId'],

        return self.message, created

    def save_message_info(self, message_info):
        if 'snippet' not in message_info or 'threadId' not in message_info:
            raise InvalidMessageDictError
        self.message.snippet = message_info['snippet']
        self.message.thread_id = message_info['threadId']

        self._save_message_labels(message_info['labelIds'])
        self._save_message_payload(message_info['payload'])

    def _save_message_labels(self, labels):
        self.message.read = 'UNREAD' not in labels
        for label in labels:
            if label != 'UNREAD':
                self.labels.append(self.manager.get_label(label))

    def _save_message_payload(self, payload):
        self._save_message_headers(payload['headers'])

        self.message.body_html = ''
        self.message.body_text = ''
        if 'parts' in payload:
            for part in payload['parts']:
                self._handle_part(part)
        else:
            self._handle_part(payload)

    def _handle_part(self, part):
        content_type = part['mimeType']
        headers = dict([(header['name'], header['value']) for header in part['headers']])
        encoding = headers.get('Content-Type', None)
        if encoding:
            encoding = encoding.split(';')[1].split('=')[1].lower().strip('"\'')
        body = base64.urlsafe_b64decode(part['body']['data'])
        if content_type == 'text/html':
            self._handle_text_html(body, encoding)
        elif content_type == 'text/plain':
            self._handle_text_plain(body, encoding)

    def _handle_text_html(self, body, encoding):
        decoded_payload = None
        if encoding:
            try:
                decoded_payload = body.decode(encoding)
            except (LookupError, UnicodeDecodeError) as e:
                print e
                print 'soup'
                soup = BeautifulSoup(body)
                if soup.original_encoding:
                    encoding = soup.original_encoding
                    try:
                        decoded_payload = body.decode(encoding)
                    except (LookupError, UnicodeDecodeError) as e:
                        print e
                        print encoding
                        print 'soup failed'

        # If decoding fails, just force utf-8
        if not decoded_payload:
            decoded_payload = body.decode('utf-8', errors='replace')

        self.message.body_html += decoded_payload

    def _handle_text_plain(self, body, encoding):
        decoded_payload = None
        if encoding:
            try:
                decoded_payload = body.decode(encoding)
            except (LookupError, UnicodeDecodeError) as e:
                print encoding
                print 'dammit'
                dammit = UnicodeDammit(body)
                if dammit.original_encoding:
                    encoding = dammit.original_encoding
                    try:
                        decoded_payload = body.decode(encoding)
                    except (LookupError, UnicodeDecodeError) as e:
                        print e
                        print encoding
                        print 'dammit failed'

        # If decoding fails, just force utf-8
        if decoded_payload is None and body is not None:
            decoded_payload = body.decode('utf-8', errors='replace')

        self.message.body_text += decoded_payload

    def _save_message_headers(self, headers):
        for header in headers:
            if header['name'] is 'Date':
                date = email.utils.parsedate_tz(header['value'])
                self.message.sent_date = datetime.datetime.fromtimestamp(email.utils.mktime_tz(date), pytz.UTC)
            elif header['name'] is 'Subject':
                self.message.subject = header['value']
            else:
                self.headers.append(GmailHeader(
                    name=header['name'],
                    value=header['value'],
                ))

    def save(self):
        self.message.labels.add(self.labels)
        self.message.headers.add(self.headers)
        self.message.save()
