from collections import (
    defaultdict,
    OrderedDict,
)
import base64
import json

from django.http import Http404
from django.utils.encoding import force_text

from rest_framework import (
    authentication,
    exceptions,
    fields,
    serializers,
)
from rest_framework.metadata import SimpleMetadata
from rest_framework.request import clone_request
from rest_framework.utils.field_mapping import ClassLookupDict

from .mixins import FieldInfoMessagesMixin


class SerializatorMaxDepthReached(Exception):
    pass


class ApiMetadata(SimpleMetadata):

    """Metadata generator used for the OPTIONS request"""

    DESCRIBED_METHODS = [
        'DELETE',
        'PATCH',
        'POST',
        'PUT',
    ]

    METHODS_TO_CHECK_PERMISSION = [
        'DELETE',
        'PUT',
        'PATCH',
    ]

    METHODS_WITHOUT_SERIALIZER_INFO = [
        'DELETE'
    ]

    HEADER_PARTIAL_DATA_NAME = 'HTTP_PARTIAL_DATA'
    HEADER_LIMIT_CHOICES_TO_NAME = 'HTTP_LIMIT_CHOICES_TO'

    label_lookup_mapping = SimpleMetadata.label_lookup.mapping.copy()
    label_lookup_mapping.update({
        serializers.ManyRelatedField: 'multiple choice',
        serializers.RelatedField: 'foreign-key',
        serializers.DurationField: 'timedelta',
    })
    label_lookup = ClassLookupDict(label_lookup_mapping)

    model_label_lookup = ClassLookupDict({
    })

    depth_check = None

    # store data prepared in determine_actions method and used in determine_metadata method
    _permitted_actions = None

    def get_partial_data(self, request):
        try:
            partial_data = request.META[self.HEADER_PARTIAL_DATA_NAME]
        except KeyError:
            return None
        return json.loads(base64.b64decode(partial_data).decode('utf-8'))

    def get_limit_choices_to(self, request):
        try:
            limit_choices_to = request.META[self.HEADER_LIMIT_CHOICES_TO_NAME]
        except KeyError:
            return None
        return json.loads(base64.b64decode(limit_choices_to).decode('utf-8'))

    def determine_metadata(self, request, view):
        # If user token is expired or incorrect do not generate metadata
        if self.incorrect_auth_token(request):
            raise exceptions.AuthenticationFailed

        self.depth_check = defaultdict(int)
        self.partial_data = self.get_partial_data(request)
        self.limit_choices_to = self.get_limit_choices_to(request)
        metadata = super(ApiMetadata, self).determine_metadata(request, view)

        if not metadata.get('actions'):
            # Don't generate extra_metadata if user has no permissions for any actions.
            # It's also good for preflight requests performance.
            return metadata

        extra_metadata = {
            'permitted_actions': self._permitted_actions
        }
        if hasattr(view, 'get_serializer'):
            serializer = self._get_serializer(view, self._get_instance(view))
            if hasattr(serializer, 'get_extra_metadata'):
                extra_metadata.update(
                    serializer.get_extra_metadata(request, view, self)
                )
        metadata.update({
            'extra_metadata': extra_metadata,
        })
        return metadata

    def determine_actions(self, request, view):
        """Return information about the fields that are accepted

        Unfortunately, this method has to be copied from the base class in order to extend the list of described
        methods.
        """
        from rest_framework import generics
        default_action_map = {
            (generics.CreateAPIView, 'post'): 'create',
            (generics.ListAPIView, 'get'): 'list',
            (generics.RetrieveAPIView, 'get'): 'retrieve',
            (generics.DestroyAPIView, 'delete'): 'destroy',
            (generics.UpdateAPIView, 'put'): 'update',
            (generics.UpdateAPIView, 'patch'): 'partial_update',
        }
        actions = {}
        permitted_actions = {}
        instance = self._get_instance(view)  # Optional[object]

        for method in sorted(set(self.DESCRIBED_METHODS) & set(view.allowed_methods)):
            view.request = clone_request(request, method)
            try:
                # Test global permissions
                self._check_global_permissions(view)

                # Test object permissions
                action_name = None
                if hasattr(view, 'action_map'):
                    action_name = view.action_map.get(method.lower(), '')
                elif isinstance(view, generics.GenericAPIView):
                    for (base_class, default_method), default_action_name in default_action_map.items():
                        if isinstance(view, base_class) and method.lower() == default_method:
                            action_name = default_action_name
                            break
                action = getattr(view, action_name, None) if action_name else None
                if (method in self.METHODS_TO_CHECK_PERMISSION or getattr(action, 'detail', False)) and instance is not None:
                    self._check_object_permissions(view, instance, action)
            except exceptions.PermissionDenied:
                permitted_actions[method] = False
            except Http404:
                permitted_actions[method] = False
            except exceptions.APIException:
                view.request = request
                continue
            else:
                permitted_actions[method] = True

            # If user has appropriate permissions for the view, include
            # appropriate metadata about the fields that should be supplied.
            serializer = self._get_serializer(view, instance)
            self.depth_check = defaultdict(int)
            if method not in self.METHODS_WITHOUT_SERIALIZER_INFO:
                actions[method] = self.get_serializer_info(serializer)
            else:
                actions[method] = {}
            view.request = request

        self._permitted_actions = permitted_actions
        return actions

    def get_serializer_info(self, serializer):
        """Given an instance of a serializer, return a dictionary of metadata about its fields.

        Copied from the Django Rest Framework in order to apply some modifications related to
        serializator's recurrence depth.
        """
        if hasattr(serializer, 'child'):
            # If this is a `ListSerializer` then we want to examine the
            # underlying child serializer instance instead.
            serializer = serializer.child

        meta = getattr(serializer, 'Meta', None)
        depth = getattr(meta, 'depth', None)

        if depth is not None and self.depth_check[serializer.__class__.__name__] >= depth and self._get_paths(serializer):
            raise SerializatorMaxDepthReached(
                '"{}" reached max depth level: {}'.format(serializer.__class__.__name__, depth))

        self.depth_check[serializer.__class__.__name__] += 1

        return OrderedDict([
            (field_name, self.get_field_info(field, serializer))
            for field_name, field in serializer.fields.items()
        ])

    def get_field_info(self, field, serializer):
        """Given an instance of a serializer field, return a dictionary of metadata about it.

        Copied from the Django Rest Framework in order to apply some modifications.
        """
        field_info = OrderedDict()
        if isinstance(field, serializers.ModelField):
            try:
                model_field = getattr(field, 'model_field', None)
                if model_field:
                    field_info['type'] = self.model_label_lookup[model_field]
            except KeyError:
                pass

        if not field_info.get('type', None):
            field_info['type'] = self.label_lookup[field]
        field_info['required'] = getattr(field, 'required', False)

        attrs = [
            'read_only',
            'label',
            'help_text',
            'min_length',
            'max_length',
            'min_value',
            'max_value',
        ]

        for attr in attrs:
            value = getattr(field, attr, None)
            if value is not None and value != '':
                field_info[attr] = force_text(value, strings_only=True)

        if hasattr(field, 'get_default_value_representation'):
            # Sometimes default value need to be represented in specific way
            field_info['default'] = field.get_default_value_representation()
        else:
            default_value = getattr(field, 'default', fields.empty)

            if default_value in [fields.empty, None]:
                field_info['default'] = None
            else:
                # Default value in metadata needs to be valid field representation
                field_info['default'] = field.to_representation(default_value)

        if getattr(field, 'child', None):
            field_info['child'] = self.get_field_info(field.child, serializer)
        elif getattr(field, 'fields', None):
            try:
                field_info['children'] = self.get_serializer_info(field)
            except SerializatorMaxDepthReached:
                paths = self._get_paths(field)
                field_info = {
                    'type': 'reference:{}'.format('.'.join(paths[::-1]))
                }
        if getattr(field, 'is_autocomplete', False):
            field_info['autocomplete'] = self._get_field_info_autocomplete(field)
        elif hasattr(field, 'choices'):
            limit_choices_to = self.limit_choices_to.get(field.field_name) if self.limit_choices_to else None
            field_info['choices'] = self._get_field_info_choices(field, limit_choices_to)

        field_info['info_messages'] = []
        if isinstance(serializer, FieldInfoMessagesMixin):
            field_info['info_messages'] = serializer.get_field_info_messages(field.field_name)

        return field_info

    def _get_paths(self, serializer):
        parent, paths = serializer.parent, []
        while parent:
            if parent.__class__.__name__ == serializer.__class__.__name__:
                paths.append(parent.field_name)
            parent = parent.parent
        return paths

    def _check_object_permissions(self, view, instance, action):
        """Check permissions to object basing on object instance, view and action.

        Raises PermissionDenied.
        """
        view.check_object_permissions(view.request, instance)
        if (
            action and hasattr(action, 'predicate') and
            not action.predicate(instance, view.request.user)[0]
        ):
            raise exceptions.PermissionDenied()

    def _check_global_permissions(self, view):
        """Check permissions to view.

        Raises PermissionDenied.
        """
        if hasattr(view, 'check_permissions'):
            view.check_permissions(view.request)

    def _get_field_info_autocomplete(self, field):
        autocomplete = {
            'model_name': field.model_api_name,
        }
        autocomplete_dependencies = getattr(field, 'autocomplete_dependencies', {})
        if autocomplete_dependencies:
            autocomplete['dependencies'] = autocomplete_dependencies
        autocomplete_filters = getattr(field, 'autocomplete_filters', {})
        if autocomplete_filters:
            autocomplete['filters'] = autocomplete_filters
        return autocomplete

    def _get_field_info_choices(self, field, limit_choices_to):
        choices = [
            {
                'value': choice_value,
                'display_name': force_text(choice_name, strings_only=True)
            }
            for choice_value, choice_name in field.choices.items()
        ]
        if limit_choices_to is not None:
            choices = [choice for choice in choices if choice.get('value') in limit_choices_to]
        return choices

    def _get_instance(self, view):
        if not hasattr(self, '_instance_cache'):
            self._instance_cache = self._get_uncached_instance(view)
        return self._instance_cache

    @staticmethod
    def _get_uncached_instance(view):
        if not hasattr(view, 'lookup_url_kwarg') or not hasattr(view, 'lookup_field'):
            return None

        lookup_url_kwarg = view.lookup_url_kwarg or view.lookup_field
        lookup_value = view.kwargs.get(lookup_url_kwarg)
        if isinstance(lookup_value, str) and lookup_value.startswith('__') and lookup_value.endswith('__'):
            # it's a partial request for a new instance
            instance = None
        elif lookup_value is None:
            instance = None
        elif not hasattr(view, 'get_object'):
            instance = None
        else:
            try:
                instance = view.get_object()
            except (exceptions.NotFound, Http404):
                instance = None
        return instance

    def _get_serializer(self, view, instance):
        kwargs = {}
        if self.partial_data and 'data' in self.partial_data:
            kwargs['data'] = self.partial_data['data']
        if instance:
            kwargs['instance'] = instance
        return view.get_serializer(**kwargs)

    def incorrect_auth_token(self, request):
        """Check if token provided and is incorrect"""
        has_auth_header = bool(authentication.get_authorization_header(request))
        return has_auth_header and not request.user.is_authenticated
