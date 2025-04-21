# Public API Endpoints

This document explains how to mark API endpoints as public (not requiring an API key) in the WynnVentory Web application.

## Background

By default, all API endpoints in the application require an API key for authentication. This is enforced by the following line in `modules/__init__.py`:

```python
bp.before_request(require_api_key)
```

However, some endpoints should be freely accessible without requiring an API key. The `@public_endpoint` decorator has been implemented to allow marking specific endpoints as public.

## Usage

To mark an API endpoint as public, simply add the `@public_endpoint` decorator to the route function:

```python
from modules.auth import public_endpoint

@blueprint.route('/some/path')
@public_endpoint
def some_endpoint():
    # This endpoint can be accessed without an API key
    return jsonify({"message": "This is a public endpoint"})
```

## How It Works

The `@public_endpoint` decorator adds the function name to a set of public endpoint names. When a request is made, the `require_api_key` function extracts the endpoint name from the request and checks if it's in this set. If it is, the API key check is bypassed.

This approach ensures that the decorator works correctly even when Flask wraps the original function with additional functionality during route registration.

## Currently Public Endpoints

The following endpoints have been marked as public:

1. `GET /api/item/<item_name>` - Get details for a specific item by name
2. `POST /api/items` - Search for items based on criteria

## Adding More Public Endpoints

To make additional endpoints public, follow these steps:

1. Import the `public_endpoint` decorator from `modules.auth`
2. Add the decorator to the route function you want to make public
3. Make sure the decorator is applied after the route decorator (`@blueprint.route`)

Example:

```python
from flask import Blueprint, jsonify
from modules.auth import public_endpoint

bp = Blueprint('example', __name__, url_prefix='/api')

@bp.get('/public-data')
@public_endpoint
def get_public_data():
    return jsonify({"data": "This is public data"})
```
