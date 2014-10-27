from django.test import TestCase
from lily.accounts.factories import AccountFactory
from lily.utils.models import EmailAddress


class Test(TestCase):

    def test_account_set_email(self):
        """
        Test the pre_save signal involving e-mail addresses for Account.
        This means when setting the attribute 'email', an emailadress instance
        is actually being created and saved when the user instance is saved.
        """

        # Create dummy account
        account = AccountFactory.create(name='Foo Bar inc.')
        account.primary_email = 'first@account.com'

        # assert email is not saved yet
        email = None
        try:
            email = account.email_addresses.get(is_primary=True)
            email = email.email_address
        except EmailAddress.DoesNotExist:
            pass
        self.assertEqual(None, email)

        # Save email
        account.save()

        # assert email equals first@account.com
        email = None
        try:
            email = account.email_addresses.get(is_primary=True)
            email = email.email_address
        except EmailAddress.DoesNotExist:
            pass
        self.assertEqual('first@account.com', email)

        # change and save email
        account.primary_email = 'second@account.com'
        account.save()

        # assert email equals second@account.com
        email = None
        try:
            email = account.email_addresses.get(is_primary=True)
            email = email.email_address
        except EmailAddress.DoesNotExist:
            pass
        self.assertEqual('second@account.com', email)

        # change email (don't save)
        account.primary_email = 'third@account.com'

        # assert email still equals second@user.com
        email = None
        try:
            email = account.email_addresses.get(is_primary=True)
            email = email.email_address
        except EmailAddress.DoesNotExist:
            pass
        self.assertEqual('second@account.com', email)
