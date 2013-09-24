import urllib
from datetime import datetime

from dateutil.tz import gettz, tzutc
from dateutil.parser import parse
from django import template
from django.conf import settings
from django.core.urlresolvers import reverse
from django.db.models.query_utils import Q
from python_imap.folder import INBOX, SENT, DRAFTS, TRASH, SPAM

from lily.messaging.email.models import EmailAccount, EmailMessage
from lily.tenant.middleware import get_current_user

register = template.Library()


@register.filter(name='pretty_datetime')
def pretty_datetime(time, format=None):
    """
    Returns a string telling how long ago datetime differs from now or format
    it accordingly. Time is an UTC datetime.
    """
    # Convert to utc
    if isinstance(time, basestring):
        parsed_time = parse(time)
        parsed_time.tzinfo._name = None  # clear tzname to rely solely on the offset (not all tznames are supported)
        utc_time = parsed_time.astimezone(tzutc())
    elif isinstance(time, datetime):
        utc_time = time.astimezone(tzutc())
    else:
        return None

    # Convert to local
    localized_time = utc_time.astimezone(gettz(settings.TIME_ZONE))
    localized_now = datetime.now(tzutc()).astimezone(gettz(settings.TIME_ZONE))

    if isinstance(format, basestring):
        return datetime.strftime(localized_time, format)

    # Format based on local times
    if localized_now.toordinal() - localized_time.toordinal() == 0:  # same day
        return datetime.strftime(localized_time, '%H:%M')
    elif localized_now.year != localized_time.year:
        return datetime.strftime(localized_time, '%d-%m-%y')
    else:
        return datetime.strftime(localized_time, '%d-%b.')


def get_folder_unread_count(folder, email_accounts=None):
    if email_accounts is None:
        email_accounts = get_current_user().get_messages_accounts(EmailAccount)

    return EmailMessage.objects.filter(Q(folder_identifier=folder) | Q(folder_name=folder), account__in=email_accounts, is_seen=False).count()


class UnreadMessagesNode(template.Node):
    def __init__(self, folder, accounts=None):
        self.folder = folder
        self.accounts = accounts

    def render(self, context):
        folder = self.folder.resolve(context)
        accounts = self.accounts
        if self.accounts is not None:
            accounts = self.accounts.resolve(context)
            if not isinstance(accounts, list):
                accounts = [accounts]

        return get_folder_unread_count(folder, accounts)


@register.tag(name='unread_folder_count')
def unread_folder_count(parser, token):
    """
    Return the number of sum of unread messages in folder for accounts.
    """
    try:
        tag_name, folder = token.split_contents()
        folder = template.Variable(folder)
    except ValueError:
        try:
            tag_name, folder, accounts = token.split_contents()
            folder = template.Variable(folder)
            accounts = template.Variable(accounts)
        except ValueError:
            raise template.TemplateSyntaxError("%r tag requires either one or two arguments" % token.contents.split()[0])
    else:
        accounts = None
    return UnreadMessagesNode(folder=folder, accounts=accounts)


def get_folder_html(folder_name, folder, request, account=None):
    """
    Return HTML to display a list with e-mail folders and the count for unread messages within each folder.
    """
    expand_parent = active_and_expand = False
    html = u''
    sub_html = u''

    folder_flags = set([INBOX, SENT, DRAFTS, TRASH, SPAM]).intersection(set(folder.get('flags')))
    if len(folder_flags) > 0:
        # In case it's one of the global folders, get html and unread count per account
        flag = folder_flags.pop()

        # Build sub_html, which displays the account's email address and unread count for folder *flag*
        email_accounts = get_current_user().get_messages_accounts(EmailAccount)

        for account in email_accounts:
            # Reverse find urls to each account's folder *flag*
            sub_reverse_url_name = {
                INBOX: 'messaging_email_account_inbox',
                SENT: 'messaging_email_account_sent',
                DRAFTS: 'messaging_email_account_drafts',
                TRASH: 'messaging_email_account_trash',
                SPAM: 'messaging_email_account_spam',
            }.get(flag)
            folder_url = reverse(sub_reverse_url_name, kwargs={'account_id': account.pk})

            # Check if *folder_url* is currently being displayed by checking against *request.path*
            current_is_active = urllib.unquote_plus(folder_url.encode('utf-8')) == urllib.unquote_plus(request.path)
            if current_is_active:
                expand_parent = True

            # Append HTML for folder *flag* for *account*
            sub_html += """
                    <li%s>
                        <a href="%s" style="margin-left: 10px;" title="%s">
                            %s
                            <span class="mws-nav-tooltip mws-inset">%d</span>
                        </a>
                        <span class="spacer"></span>
                    </li>""" % (' class="active expanded"' if current_is_active else '', folder_url, account.email.email_address, account.email.email_address, get_folder_unread_count(flag, email_accounts=[account]))

        # Reverse find url to the combined folder *flag* for *email_accounts*
        reverse_url_name = {
            INBOX: 'messaging_email_inbox',
            SENT: 'messaging_email_sent',
            DRAFTS: 'messaging_email_drafts',
            TRASH: 'messaging_email_trash',
            SPAM: 'messaging_email_spam',
        }.get(flag)
        folder_url = reverse(reverse_url_name)

        # Check if *folder_url* is currently being displayed by checking against *request.path*
        current_is_active = urllib.unquote_plus(folder_url.encode('utf-8')) == urllib.unquote_plus(request.path)
        active_and_expand = current_is_active or expand_parent

        # Append HTML for combined folder *flag* for *email_accounts*
        html += """
            <li class="mws-dropdown-menu%(parent_css_classes)s">
                <a href="%(folder_url)s" class="i-16 i-mailbox mws-dropdown-trigger" title="%(folder_name)s">
                    %(folder_name)s
                    <span class="mws-nav-tooltip mws-inset">%(unread_count)d</span>
                </a>
                <span class="spacer"></span>
                <ul%(sub_folder_css_classes)s>
                    %(sub_folder_html)s
                </ul>
            </li>""" % \
            {
                'parent_css_classes': 'active expanded' if active_and_expand else '',
                'folder_url': folder_url,
                'folder_name': folder_name,
                'unread_count': get_folder_unread_count(flag),
                'sub_folder_css_classes': ' class="active expanded"' if active_and_expand else ' class="closed"',
                'sub_folder_html': sub_html
            }

    else:
        # URL for folders that are not selectable via IMAP or parent folders, clicking this will show sub folders
        folder_url = 'javascript:void(0)'
        if not '\\Noselect' in folder.get('flags') and not folder.get('is_parent'):
            if folder.get('account_id'):
                # Replace *folder_url* with an actual URL to be able to view messages in folder
                folder_url = reverse('messaging_email_account_folder', kwargs={
                    'account_id': folder.get('account_id'),
                    'folder': urllib.quote_plus(folder.get('full_name').encode('utf-8'))
                })

        # Check if *folder_url* is currently being displayed by checking against *request.path*
        current_is_active = urllib.unquote_plus(folder_url.encode('utf-8')).decode('utf-8') == urllib.unquote_plus(request.path)

        if folder.get('is_parent'):
            # Get HTML for sub folders *children*
            sub_html = u''
            for sub_folder_name, sub_folder in folder.get('children', {}).items():
                sub_folder_is_active, sub_folder_html = get_folder_html(sub_folder_name, sub_folder, request, account=account)
                sub_html += sub_folder_html
                if sub_folder_is_active:
                    expand_parent = True

            # Check if a sub folder
            active_and_expand = current_is_active or expand_parent

            # Append HTML for parent folder *folder_name* for *account*
            html += """
                <li class="mws-dropdown-menu%(parent_css_classes)s">
                    <a href="%(folder_url)s" class="mws-dropdown-trigger" title="%(folder_name)s">
                        <i class="ui-icon %(folder_icon)s"></i>
                        %(folder_name)s
                    </a>
                    <span class="spacer"></span>
                    <ul%(sub_folder_css_classes)s>
                        %(sub_folder_html)s
                    </ul>
                </li>""" % \
                {
                    'parent_css_classes': ' active expanded' if active_and_expand else '',
                    'folder_url': folder_url,
                    'folder_name': folder_name,
                    'folder_icon': 'ui-icon-triangle-1-s' if active_and_expand else 'ui-icon-carat-1-e',
                    'sub_folder_css_classes': ' class="active expanded"' if active_and_expand else ' class="closed"',
                    'sub_folder_html': sub_html
                }

        else:
            # Append HTML for folder *folder_name* for *account*
            active_and_expand = current_is_active
            html += """<li%s>
                        <a href="%s" title="%s">
                            %s
                            <span class="mws-nav-tooltip mws-inset">%d</span>
                        </a>
                        <span class="spacer"></span>
                    </li>""" % (' class="active expanded"' if active_and_expand else '', folder_url, folder_name, folder_name, get_folder_unread_count(folder_name))

    return active_and_expand, html


class EmailFolderTreeNode(template.Node):
    def __init__(self):
        self.user = get_current_user()
        self.folders = template.Variable('email_folders')
        self.request = template.Variable('request')

    def render(self, context):
        email_folders = self.folders.resolve(context)
        request = self.request.resolve(context)
        html = u''
        for folder_name, folder in email_folders.items():
            active, folder_html = get_folder_html(folder_name, folder, request)
            html += folder_html

        return html


@register.tag(name='email_folder_tree')
def email_folder_tree(parser, token):
    """
    Return HTML containing the menu layout for e-mail folders.
    """
    return EmailFolderTreeNode()