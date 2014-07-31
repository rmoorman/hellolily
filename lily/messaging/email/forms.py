import socket
import traceback
from smtplib import SMTPAuthenticationError

from django import forms
from django.db.models import Q
from django.core.mail import get_connection
from django.forms.widgets import RadioSelect, SelectMultiple
from django.template.defaultfilters import linebreaksbr
from django.utils.translation import ugettext as _
from python_imap.server import IMAP

from lily.contacts.models import Contact
from lily.messaging.email.models import EmailProvider, EmailAccount, EmailTemplate, EmailDraft
from lily.messaging.email.utils import get_email_parameter_choices, TemplateParser
from lily.tenant.middleware import get_current_user
from lily.users.models import CustomUser
from lily.utils.fields import TagsField
from lily.utils.forms import HelloLilyForm, HelloLilyModelForm
from lily.utils.fields import HostnameField
from lily.utils.widgets import ShowHideWidget


class EmailConfigurationWizard_1(HelloLilyForm):
    """
    Fields in e-mail configuration wizard step 1.
    """
    email = forms.CharField(max_length=255, label=_('E-mail address'), widget=forms.TextInput(attrs={
        'placeholder': _('email@example.com')
    }))
    username = forms.CharField(max_length=255, label=_('Username'))
    password = forms.CharField(max_length=255, label=_('Password'), widget=forms.PasswordInput())


class EmailConfigurationWizard_2(HelloLilyForm):
    """
    Fields in e-mail configuration wizard step 2.
    """
    preset = forms.ModelChoiceField(queryset=EmailProvider.objects.none(), empty_label=_('Manually set email server settings'), required=False)

    def __init__(self, *args, **kwargs):
        super(EmailConfigurationWizard_2, self).__init__(*args, **kwargs)

        self.fields['preset'].queryset = EmailProvider.objects.filter(~Q(name=None))


class EmailConfigurationWizard_3(HelloLilyForm):
    """
    Fields in e-mail configuration wizard step 3.
    """
    imap_host = HostnameField(max_length=255, label=_('Incoming server (IMAP)'))
    imap_port = forms.IntegerField(label=_('Incoming port'))
    imap_ssl = forms.BooleanField(label=_('Incoming SSL'), required=False)
    smtp_host = HostnameField(max_length=255, label=_('Outgoing server (SMTP)'))
    smtp_port = forms.IntegerField(label=_('Outgoing port'))
    smtp_ssl = forms.BooleanField(label=_('Outgoing SSL'), required=False)
    share_preset = forms.BooleanField(label=_('Share preset'), required=False)
    preset_name = forms.CharField(max_length=255, label=_('Preset name'), required=False, widget=forms.HiddenInput(),
                                  help_text=_('Entering a name will allow other people in your organisation to use these settings as well'))

    def __init__(self, *args, **kwargs):
        self.username = kwargs.pop('username', '')
        self.password = kwargs.pop('password', '')
        self.preset = kwargs.pop('preset', None)

        super(EmailConfigurationWizard_3, self).__init__(*args, **kwargs)

        if self.preset is not None:
            self.fields['share_preset'].widget = forms.HiddenInput()

    def clean(self):
        if hasattr(self, 'preset') and self.preset is not None:
            data = {
                'imap_host': self.preset.imap_host,
                'imap_port': self.preset.imap_port,
                'imap_ssl': self.preset.imap_ssl,
                'smtp_host': self.preset.smtp_host,
                'smtp_port': self.preset.smtp_port,
                'smtp_ssl': self.preset.smtp_ssl
            }
        else:
            data = self.cleaned_data

            if not data['share_preset']:
                # Store name as null/None
                data['preset_name'] = None
            elif data['share_preset']:
                if not data['preset_name'] or data['preset_name'].strip() == '':
                    if 'preset_name' not in self._errors:
                        self._errors['preset_name'] = []

                    # If 'Share preset' is checked and preset name is empty, show error
                    self._errors['preset_name'].append(_('Preset name can\'t be empty when \'Share preset\' is checked'))

        if not self.errors:
            # Start verifying when the form has no errors
            defaulttimeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(1)

            try:
                imap_host = data.get('imap_host')
                imap_port = int(data.get('imap_port'))
                imap_ssl = data.get('imap_ssl')
                try:
                    # Resolve host name
                    socket.gethostbyname(imap_host)
                except Exception, e:
                    print traceback.format_exc(e)
                    raise forms.ValidationError(_('Could not resolve %s' % imap_host))
                else:
                    try:
                        # Try connecting
                        imap = IMAP(imap_host, imap_port, imap_ssl)
                        if not imap:
                            raise forms.ValidationError(_('Could not connect to %s:%s' % (imap_host, data.get('imap_port'))))
                    except Exception, e:
                        print traceback.format_exc(e)
                        raise forms.ValidationError(_('Could not connect to %s:%s' % (imap_host, data.get('imap_port'))))
                    else:
                        try:
                            # Try authenticating
                            if not imap.login(self.username, self.password):
                                raise forms.ValidationError(_('Unable to login with provided username and password on the IMAP host'))
                        except Exception, e:
                            print traceback.format_exc(e)
                            raise forms.ValidationError(_('Unable to login with provided username and password on the IMAP host'))

                smtp_host = data.get('smtp_host')
                smtp_port = int(data.get('smtp_port'))
                smtp_ssl = data.get('smtp_ssl')
                try:
                    # Resolve SMTP server
                    socket.gethostbyname(smtp_host)
                except Exception, e:
                    raise forms.ValidationError(_('Could not resolve %s' % smtp_host))
                else:
                    try:
                        # Try connecting
                        kwargs = {
                            'host': smtp_host,
                            'port': smtp_port,
                            'use_tls': smtp_ssl,
                            'username': self.username,
                            'password': self.password,
                        }
                        smtp_server = get_connection('django.core.mail.backends.smtp.EmailBackend', fail_silently=False, **kwargs)
                        smtp_server.open()
                        smtp_server.close()
                    except SMTPAuthenticationError, e:
                        raise forms.ValidationError(_('Unable to login with provided username and password on the SMTP host'))
                    except Exception, e:
                        print traceback.format_exc(e)
                        raise forms.ValidationError(_('Could not connect to %s:%s' % (smtp_host, data.get('smtp_port'))))
            except:
                raise
            finally:
                socket.setdefaulttimeout(defaulttimeout)

        return data


class EmailConfigurationWizard_4(HelloLilyForm):
    """
    Fields in e-mail configuration wizard step 4.
    """
    name = forms.CharField(max_length=255, label=_('Your name'), widget=forms.TextInput(attrs={
        'placeholder': _('First Last')
    }))
    # signature = forms.CharField(label=_('Your signature'), widget=forms.Textarea(), required=False)


class EmailShareForm(HelloLilyModelForm):
    """
    Form to share an e-mail account.
    """
    def __init__(self, *args, **kwargs):
        """
        Overload super().__init__ to change the appearance of the form.
        """
        self.original_user = kwargs.pop('original_user', None)
        super(EmailShareForm, self).__init__(*args, **kwargs)

        # Exclude original user from queryset when provided
        if self.original_user is not None:
            self.fields['user_group'].queryset = CustomUser.objects.filter(tenant=get_current_user().tenant).exclude(pk=self.original_user.pk)
        else:
            self.fields['user_group'].queryset = CustomUser.objects.filter(tenant=get_current_user().tenant)

        # Overwrite help_text
        self.fields['user_group'].help_text = ''

        # Only a required field when selecting 'Specific users'
        self.fields['user_group'].required = False

    def clean(self):
        """
        Please specify which users to share this email address with.
        """
        cleaned_data = self.cleaned_data

        if cleaned_data.get('shared_with', 0) == 2 and len(cleaned_data.get('user_group', [])) == 0:
            self._errors['user_group'] = self.error_class([_('Please specify which users to share this email address with.')])

        return cleaned_data

    def save(self, commit=True):
        """
        Overloading super().save to at least always add the original user to user_group when provided.
        """
        if self.instance.shared_with < 2:
            # clear relation set for *don't share* and *everybody*
            self.instance.user_group.clear()
        else:
            # save m2m relations properly
            super(EmailShareForm, self).save(commit)

        if self.original_user is not None:
            self.instance.user_group.add(self.original_user)

        self.instance.save()
        return self.instance

    class Meta:
        exclude = ('account_type', 'tenant', 'email_account', 'from_name', 'signature', 'email', 'username', 'password', 'provider', 'last_sync_date', 'folders')
        model = EmailAccount
        widgets = {
            'shared_with': RadioSelect(),
            'user_group': SelectMultiple(attrs={'class': 'chzn-select'})
        }


class ComposeEmailForm(HelloLilyModelForm):
    """
    Form for writing an EmailMessage as a draft, reply or forwarded message.
    """
    template = forms.ModelChoiceField(label=_('Template'), queryset=EmailTemplate.objects, empty_label=_('Choose a template'), required=False)
    send_to_normal = TagsField(label=_('To'))
    send_to_cc = TagsField(required=False, label=_('Cc'))
    send_to_bcc = TagsField(required=False, label=_('Bcc'))

    def __init__(self, *args, **kwargs):
        self.draft_id = kwargs.pop('draft_id', None)
        self.message_type = kwargs.pop('message_type', 'reply')
        super(ComposeEmailForm, self).__init__(*args, **kwargs)

        user = get_current_user()
        email_accounts = user.get_messages_accounts(EmailAccount)

        # Only provide choices you have access to
        self.fields['send_from'].choices = [(email_account.id, email_account) for email_account in email_accounts]

        contacts = Contact.objects.all()
        contacts_list = []

        for contact in contacts:
            if contact.get_any_email_address():
                contacts_list.append(contact.full_name() + ' <' + str(contact.get_any_email_address()) + '>')

        self.fields['send_to_normal'].choices = contacts_list
        self.fields['send_to_cc'].choices = contacts_list
        self.fields['send_to_bcc'].choices = contacts_list
        self.fields['send_from'].empty_label = None

        # Set user's primary_email as default choice if there is no initial value
        initial_email_account = self.initial.get('send_from', None)
        if not initial_email_account:
            for email_account in email_accounts:
                if email_account.email.email_address == user.primary_email.email_address:
                    initial_email_account = email_account
        elif isinstance(initial_email_account, basestring):
            for email_account in email_accounts:
                if email_account.email.email_address == initial_email_account:
                    initial_email_account = email_account

        self.initial['send_from'] = initial_email_account

    def is_multipart(self):
        """
        Return True since file uploads are possible.
        """
        return True

    def clean(self):
        cleaned_data = super(ComposeEmailForm, self).clean()

        # Make sure at least one of the send_to_X fields is filled in when sending it.
        if 'submit-send' in self.data:
            if not any([cleaned_data.get('send_to_normal'), cleaned_data.get('send_to_cc'), cleaned_data.get('send_to_bcc')]):
                self._errors["send_to_normal"] = self.error_class([_('Please provide at least one recipient.')])

        # Clean send_to addresses.
        cleaned_data['send_to_normal'] = self.format_recipients(cleaned_data.get('send_to_normal'))
        cleaned_data['send_to_cc'] = self.format_recipients(cleaned_data.get('send_to_cc'))
        cleaned_data['send_to_bcc'] = self.format_recipients(cleaned_data.get('send_to_bcc'))

        return cleaned_data

    def format_recipients(self, recipients):
        """
        Strips newlines and trailing spaces & commas from recipients.

        Args:
            recipients (str): The string that needs cleaning up.

        Returns:
            String of comma separated email addresses.
        """
        formatted_recipients = []
        for recipient in recipients:
            formatted_recipients.append(recipient.rstrip(', '))
        return ', '.join(formatted_recipients)

    def clean_send_from(self):
        """
        Verify send_from is a valid account the user has access to.
        """
        cleaned_data = self.cleaned_data
        send_from = cleaned_data.get('send_from')

        email_accounts = get_current_user().get_messages_accounts(EmailAccount)
        if send_from.pk not in [account.pk for account in email_accounts]:
            self._errors['send_from'] = _(u'Invalid email account selected to use as sender.')

        return send_from

    class Meta:
        model = EmailDraft
        fields = ('send_from', 'send_to_normal', 'send_to_cc', 'send_to_bcc', 'subject', 'template', 'body_html',)
        widgets = {
            'body_html': forms.Textarea(attrs={
                'rows': 12,
                'class': 'inbox-editor inbox-wysihtml5 form-control',
            }),
        }


class CreateUpdateEmailTemplateForm(HelloLilyModelForm):
    """
    Form used for creating and updating email templates.
    """
    variables = forms.ChoiceField(label=_('Insert variable'), choices=[['', 'Select a category']], required=False)
    values = forms.ChoiceField(label=_('Insert value'), choices=[['', 'Select a variable']], required=False)

    def __init__(self, *args, **kwargs):
        """
        Overload super().__init__ to change the appearance of the form and add parameter fields if necessary.
        """
        self.draft_id = kwargs.pop('draft_id', None)
        self.message_type = kwargs.pop('message_type', 'reply')
        super(CreateUpdateEmailTemplateForm, self).__init__(*args, **kwargs)

        email_parameter_choices = get_email_parameter_choices()
        self.fields['variables'].choices += [[x, x] for x in email_parameter_choices.keys()]

        for value in email_parameter_choices:
            for val in email_parameter_choices[value]:
                self.fields['values'].choices += [[val, email_parameter_choices[value][val]], ]

    def clean(self):
        """
        Make sure the form is valid.
        """
        cleaned_data = super(CreateUpdateEmailTemplateForm, self).clean()
        html_part = cleaned_data.get('body_html')
        text_part = cleaned_data.get('body_text')

        if not html_part and not text_part:
            self._errors['body_html'] = _('Please fill in the html part or the text part, at least one of these is required.')
        elif html_part:
            parsed_template = TemplateParser(html_part)
            if parsed_template.is_valid():
                cleaned_data.update({
                    'body_html': parsed_template.get_text(),
                })
            else:
                self._errors['body_html'] = parsed_template.error.message
                del cleaned_data['body_html']
        elif text_part:
            parsed_template = TemplateParser(text_part)
            if parsed_template.is_valid():
                cleaned_data.update({
                    'body_text': parsed_template.get_text(),
                })
            else:
                self._errors['body_text'] = parsed_template.error.message
                del cleaned_data['body_text']

        return cleaned_data

    def save(self, commit=True):
        instance = super(CreateUpdateEmailTemplateForm, self).save(False)
        instance.body_html = linebreaksbr(instance.body_html.strip())

        if commit:
            instance.save()
        return instance

    class Meta:
        model = EmailTemplate
        fields = ('name', 'description', 'subject', 'variables', 'values', 'body_html',)
        widgets = {
            'values': forms.Select(attrs={
                'disabled': 'disabled',
            }),
            'description': ShowHideWidget(forms.Textarea(attrs={
                'rows': 2,
            })),
            'body_html': forms.Textarea(attrs={
                'rows': 12,
                'class': 'inbox-editor inbox-wysihtml5 form-control',
            }),
        }


class EmailTemplateFileForm(HelloLilyForm):
    """
    Form that is used to parse uploaded template files.
    """
    accepted_content_types = ['text/html', 'text/plain']
    body_file = forms.FileField(label=_('Email Template file'))
    default_error_messages = {
        'invalid': _(u'Upload a valid template file. Valid files are: %s.'),
        'syntax': _(u'There was an error in your file:<br> %s'),
    }

    def clean(self):
        """
        Form validation: message body_file should be a valid html file.
        """
        cleaned_data = super(EmailTemplateFileForm, self).clean()
        body_file = cleaned_data.get('body_file', False)

        if body_file:
            if body_file.content_type in self.accepted_content_types:
                parsed_file = TemplateParser(body_file.read().decode('utf-8'))
                if parsed_file.is_valid():
                    # Add body_html to cleaned_data
                    cleaned_data.update(parsed_file.get_parts(default_part='body_html'))
                else:
                    # Syntax error in the template tags/variables
                    self._errors['body_file'] = self.default_error_messages.get('syntax') % parsed_file.error.message
            else:
                # When it doesn't seem like an text/html or text/plain file
                self._errors['body_file'] = self.default_error_messages.get('invalid') % self.accepted_content_types

            del cleaned_data['body_file']
        else:
            # When there is no file at all
            self._errors['body_file'] = self.default_error_messages.get('invalid') % self.accepted_content_types

        return cleaned_data
