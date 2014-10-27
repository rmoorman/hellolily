from lily.google.gmail.models import GmailLabel


class BaseLabelBuilderError(Exception):
    pass


class InvalidLabelDictError(BaseLabelBuilderError):
    pass


class LabelBuilder(object):

    def __init__(self, manager):
        self.label = None
        self.manager = manager

    def get_or_create_label(self, label_dict):
        """
        Get or create Label.

        Arguments:
            label_dict (dict): with label information

        Returns:
            label (instance): unsaved label
            created (boolean): True if label is created
        """
        if 'id' not in label_dict or 'type' not in label_dict:
            raise InvalidLabelDictError

        created = False
        try:
            self.label = GmailLabel.objects.get(
                account=self.manager.gmail_account,
                label_id=label_dict['id'],
                type=label_dict['type'],
            )
        except GmailLabel.DoesNotExist:
            self.label = GmailLabel(
                account=self.manager.gmail_account,
                label_id=label_dict['id'],
                type=label_dict['type'],
            )
            created = True

        self.label.name = label_dict['name']

        return self.label, created

    def save(self):
        """

        :return:
        """
        self.label.save()
