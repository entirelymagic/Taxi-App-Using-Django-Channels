# Uber-App-Using-Django-Channels

> Using test-driven development, we'll write and test the server-side code powered by Django and Django Channels. Part 2: We'll set up the client-side Angular app along with authentication and authorization. Also, we'll streamline the development workflow by adding Docker. Part 3: Finally, we'll walk through the process of creating the app UI with Angular.

Our server-side application uses:

Python (v3.9)
Django (v4.0)
Django Channels (v3.0)
Django REST Framework (v3.13)
pytest (v6.2)
Redis (v6.2)
PostgreSQL (v14.1)
Client-side:

Node.js (v16.13)
Angular (v13.0)
Reverse-proxy:

Nginx (v1.21)
We'll also use Docker v20.10.11.

Steps:

- This downloads the official Postgres Docker image from Docker Hub and runs it on port 5437(5432 is used by Local)in the background. It also sets up a database with the user, password, and database name all set to taxi.

`docker run --name some-postgres -p 5437:5432 -e POSTGRES_USER=taxi -e POSTGRES_DB=taxi -e POSTGRES_PASSWORD=taxi -d postgres`

- Next, spin up Redis on port 6379:

`docker run --name some-redis -p 6379:6379 -d redis`

- To test if redis is up and running

`$ docker exec -it some-redis redis-cli ping`

`PONG`

- set system enviroments:
`vim $VIRTUAL_ENV/bin/postactivate`

`export PGDATABASE=taxi PGUSER=taxi PGPASSWORD=taxi`

- We've also added an AUTH_USER_MODEL setting to make Django reference a user model of our design instead of the built-in one since we'll need to store more user data than what the standard fields allow.

- Make migrations and migrate
`python manage.py makemigrations`
`python manage.py migrate`

## Channels Config

<details>
  <summary>More Details:</summary>

Next, configure the CHANNEL_LAYERS by setting a default Redis backend and routing in the settings.py file. This can go at the bottom of the file.

```python
# server/taxi/settings/base.py

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [REDIS_URL],
        },
    },
}
```

Then, add Django Channels to the INSTALLED_APPS:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.postgres',
    'django.contrib.staticfiles',
    'channels', # new
    'rest_framework',
    'trips',
]
```

Put simply, unlike a typical Django app, Channels requires an ASGI_APPLICATION setting.

Create a new file called routing.py within the "taxi" folder:

```python
# server/taxi/routing.py

from django.core.asgi import get_asgi_application

from channels.routing import ProtocolTypeRouter

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
})
```

```python
# server/taxi/settings.py

ASGI_APPLICATION = 'taxi.routing.application'
```

```py
# server/taxi/asgi.py

import os
import django

from channels.routing import get_default_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'taxi.settings')
django.setup()
application = get_default_application()
```

</details>

## Authenthication

Django REST Framework's session authentication and the djangorestframework-simplejwt's JWTAuthentication class.

<details>
  <summary>More Details:</summary>

```python
# server/taxi/settings.py

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    )
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': datetime.timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': datetime.timedelta(days=1),
    'USER_ID_CLAIM': 'id',
}
```

- Sign up for an account:

`api/sign_up/` [name='sign_up']

- Login:

`api/log_in/` [name='log_in']

- Refresh token:

`api/token/refresh/` [name='token_refresh']

</details>
