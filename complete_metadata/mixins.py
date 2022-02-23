
class FieldInfoMessagesMixin(object):

    _field_info_messages = None

    def add_field_info_message(self, field_name, message):
        if self._field_info_messages is None:
            self._field_info_messages = {}
        if field_name not in self._field_info_messages:
            self._field_info_messages[field_name] = []
        self._field_info_messages[field_name].append(message)

    def get_field_info_messages(self, field_name):
        messages_dict = self._field_info_messages or {}
        return messages_dict.get(field_name, [])
