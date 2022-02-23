import pytest

from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models
from django.test import TestCase

from rest_framework import (
    exceptions,
    metadata,
    serializers,
    status,
    versioning,
    views
)
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.test import APIRequestFactory

from complete_metadata import ApiMetadata


request = APIRequestFactory().options('/')


def test_metadata():
    class ExampleView(views.APIView):
        """Example view."""
        metadata_class = ApiMetadata

    view = ExampleView.as_view()
    response = view(request=request)
    expected = {
        'name': 'Example',
        'description': 'Example view.',
        'renders': [
            'application/json',
            'text/html'
        ],
        'parses': [
            'application/json',
            'application/x-www-form-urlencoded',
            'multipart/form-data'
        ]
    }
    assert response.status_code == status.HTTP_200_OK
    assert response.data == expected


def test_actions():
    class NestedField(serializers.Serializer):
        child1 = serializers.IntegerField()
        child2 = serializers.IntegerField()

    class ExampleSerializer(serializers.Serializer):
        choice_field = serializers.ChoiceField(['circle', 'triangle', 'square'])
        integer_field = serializers.IntegerField(min_value=1, max_value=1024)
        char_field = serializers.CharField(required=False, min_length=2, max_length=20)
        list_field = serializers.ListField(child=serializers.ListField(child=serializers.IntegerField()))
        nested_field = NestedField()

    class ExampleView(views.APIView):
        """Example view."""
        metadata_class = ApiMetadata

        def post(self, request):
            pass

        def get_serializer(self):
            return ExampleSerializer()

    view = ExampleView.as_view()
    response = view(request=request)
    expected = {
        'name': 'Example',
        'description': 'Example view.',
        'renders': [
            'application/json',
            'text/html'
        ],
        'parses': [
            'application/json',
            'application/x-www-form-urlencoded',
            'multipart/form-data'
        ],
        'actions': {
            'POST': {
                'choice_field': {
                    'type': 'choice',
                    'required': True,
                    'read_only': False,
                    'label': 'Choice field',
                    'default': None,
                    'choices': [
                        {'display_name': 'circle', 'value': 'circle'},
                        {'display_name': 'triangle', 'value': 'triangle'},
                        {'display_name': 'square', 'value': 'square'}
                    ],
                    'info_messages': []
                },
                'integer_field': {
                    'type': 'integer',
                    'required': True,
                    'read_only': False,
                    'label': 'Integer field',
                    'min_value': 1,
                    'max_value': 1024,
                    'default': None,
                    'info_messages': []
                },
                'char_field': {
                    'type': 'string',
                    'required': False,
                    'read_only': False,
                    'label': 'Char field',
                    'min_length': 2,
                    'max_length': 20,
                    'default': None,
                    'info_messages': []
                },
                'list_field': {
                    'type': 'list',
                    'required': True,
                    'read_only': False,
                    'label': 'List field',
                    'default': None,
                    'child': {
                        'type': 'list',
                        'required': True,
                        'read_only': False,
                        'default': None,
                        'child': {
                            'type': 'integer',
                            'required': True,
                            'read_only': False,
                            'default': None,
                            'info_messages': []
                        },
                        'info_messages': []
                    },
                    'info_messages': []
                 },
                'nested_field': {
                    'type': 'nested object',
                    'required': True,
                    'read_only': False,
                    'label': 'Nested field',
                    'default': None,
                    'children': {
                        'child1': {
                            'type': 'integer',
                            'required': True,
                            'read_only': False,
                            'label': 'Child1',
                            'default': None,
                            'info_messages': []
                        },
                        'child2': {
                            'type': 'integer',
                            'required': True,
                            'read_only': False,
                            'label': 'Child2',
                            'default': None,
                            'info_messages': []
                        }
                    },
                    'info_messages': []
                }
            }
       },
       'extra_metadata':{
          'permitted_actions': {
             'POST': True
          }
       }
    }
    assert response.status_code == status.HTTP_200_OK
    assert response.data == expected
