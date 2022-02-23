# DRF complete metadata

![Test package](https://github.com/innovationinit/drf-complete-metadata/actions/workflows/test-package.yml/badge.svg?branch=main)
[![Coverage Status](https://coveralls.io/repos/github/innovationinit/drf-complete-metadata/badge.svg)](https://coveralls.io/github/innovationinit/drf-complete-metadata)


## About

This package provides custom metadata class for Django Rest Framework to enrich data returned by OPTIONS requests in easy way.

## Install

```bash
pip install drf-complete-metadata
```

## Usage

Just set the DEFAULT_METADATA_CLASS option in the REST_FRAMEWORK configuration dict in Django settings.

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated'
    ],
    'DEFAULT_METADATA_CLASS': 'complete_metadata.ApiMetadata',
}
```

## License
The DRF complete autocomplete package is licensed under the [FreeBSD
License](https://opensource.org/licenses/BSD-2-Clause).
