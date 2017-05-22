# Videofront [![Build Status](https://travis-ci.org/openfun/videofront.svg?branch=master)](https://travis-ci.org/openfun/videofront)

Videofront is a self-hosted Youtube: A scalable video hosting platform written in Python 3/Django.

Videofront was developed to host videos of MOOCs taught on [Open edX](https://open.edx.org/) platforms, but it can easily be used in just any web platform that requires video embedding.

The particularity of Videofront is that it supports multiple storage, transcoding and streaming backends. For instance, with Videofront you can transcode your videos with `ffmpeg` (locally), or with [Amazon Elastic Transcoder](https://aws.amazon.com/elastictranscoder/).

## Features

- Video storage, transcoding and streaming
- A RESTful API, with a browsable GUI powered by [Swagger](http://swagger.io/)
- A flexible and extensible set of backends to store and process videos from different providers. Out of the box, the following backend are supported:
    - Local backend: storage on local disk, transcoding with `ffmpeg`, streaming with Nginx
    - Amazon Web Services: storage on [S3](https://aws.amazon.com/s3/), transcoding with [ElasticTranscoder](https://aws.amazon.com/elastictranscoder/), streaming with [Cloudfront](https://aws.amazon.com/cloudfront/).
- A basic user permission system for interacting with the API
- Command line and browser-based video upload (with [CORS](https://en.wikipedia.org/wiki/Cross-origin_resource_sharing))
- Subtitle upload, conversion to [VTT](https://w3c.github.io/webvtt/) format, storage and download
- Thumbnail generation and customisation

## Install

Videofront is a standard Django project. You will not feel lost if you already know how to deploy a Django-based app.

Clone the repository:

    mkdir /opt/videofront && cd /opt/videofront
    git clone https://github.com/openfun/videofront.git
    cd videofront/

Install non-python requirements:

    sudo apt install rabbitmq-server libxml2-dev libxslt1-dev libtiff5-dev libjpeg8-dev zlib1g-dev

Install python requirements in a virtual environment:

    virtualenv --python=python3 venv # note that python3 is required
    source venv/bin/activate
    pip install -r requirements/base.txt

If you wish to interact with Amazon Web Services, additional dependencies need to be installed:

    pip install -r requirements/aws.txt

## Configuration

### Backend configuration

Before you go any further, you need to choose and configure a video backend. Out of the box, Videofront supports two backends: `local` (the default) and `aws`. First, create a settings file for your backend. Sample settings are in `videofront/settings_prod_sample_*.py`. Then, point to the settings file via the `DJANGO_SETTINGS_MODULE` environment variable.

For example, to use a local backend:

    cp videofront/settings_prod_local.py videofront/settings_prod.py
    # Edit videofront/settings_prod.py to match your platform
    export DJANGO_SETTINGS_MODULE='videofront.settings_prod'

#### Specific instructions for local backends

Install additional packages for transcoding:

    sudo apt install faac x264 ffmpeg

Make sure the directory defined in the `VIDEO_STORAGE_ROOT` setting exists:

    mkdir /opt/videofront/storage/

#### Specific instructions for AWS backends

Install additional requirements:

    pip install -r requirements/aws.txt

There are a couple commands that might be useful for setting up some things on AWS:

    # Create S3 buckets according to your settings
    ./manage.py bootstrap-s3

    # Delete folders from the production S3 bucket
    ./manage.py delete-s3-folders videos/xxx folder1/ folder2/somefile.mp4

### Database

Videofront requires an SQL database. It is compatible with all [Django-supported vendor databases](https://docs.djangoproject.com/en/1.11/ref/databases/) (in particular: SQLite, MySQL, PostgreSQL).

The database configured by default is an SQLite database stored in the videofront base directory. To change this, modify the [`DATABASES`](https://docs.djangoproject.com/en/1.11/ref/settings/#databases) setting in the `videofront/settings.py` file. However, we suggest to keep an SQLite database for development and testing; the database setting should be modified only in production, in the `videofront/settings_prod.py` file.

Create the required database tables with:

    ./manage.py migrate
    ./manage.py createcachetable

### User management

Create a user in Videofront to obtain a token and start interacting with the API:

    $ ./manage.py createuser chucknorris fantasticpassword
    Created user 'chucknorris' with token: 6f6801edef3f4b74378f2ac270be464b351efefe

Write down that API token. Alternatively, you can obtain the same token again by re-running the `createuser` command.

To create a user with administrator privilege, add the `--admin` option:

    ./manage.py createuser --admin chucknorris fantasticpassword

## Usage

Start a local server on port 8000:

    ./manage.py runserver

Once a Videofront server is running, a RESTful, browsable API is available at [http://localhost:8000/api/v1/](http://localhost:8000/api/v1/). Documentation is also available at [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs).

Start a celery worker for periodic and non-periodic tasks:

    celery -A videofront worker -B # don't do this in production

**Important note:** do NOT run the above commands in production. Instructions for production deployments are available [below](#production-deployment).

### Administration

Other than with the command line, Videofront can be administered from the Django admin page which can be found at [http://localhost:8000/admin](http://localhost:8000/admin). You will need to create an administrator user account to access this page (See [User management](#user-management)).

### Interacting with the API in command line

Obtain a video upload url:

    $ curl -X POST -H "Authorization: Token 6f6801edef3f4b74378f2ac270be464b351efefe" http://127.0.0.1:8000/api/v1/videouploadurls/
    {"id":"0sqmLiEuLpGJ","expires_at":1474362128,"origin":null,"playlist":null}(env3)

Upload a video to this url:

    $ curl -X POST -H "Authorization: Token 6f6801edef3f4b74378f2ac270be464b351efefe" -F file=@video.mp4 http://127.0.0.1:8000/api/v1/videos/0sqmLiEuLpGJ/upload/

### Using the dedicated CLI client

A dedicated CLI client exists to interact with the Videofront API. Install the [videofront-client](https://github.com/openfun/videofront-client) for easier interaction with the API.

### Custom commands

    # Create a user and print out the corresponding access token
    ./manage.py createuser --admin username password

    # Launch a new video transcoding job; useful if the transcoding job is stuck in pending state
    ./manage.py transcode-video myvideoid

## Development

Install test and contrib requirements:

    pip install -r requirements/tests.txt

Run unit tests:

    ./manage.py test

Check test coverage:

    coverage run ./manage.py test
    coverage report

If you wish to develop a new backend, you will need to create a `Backend` class that inherits from `pipeline.backend.BaseBackend` and implements the required methods. Look at `contrib.plugins.local.backend.Backend` for inspiration.

## Production deployment

### File structure

In the following, we assume the following file hierarchy:

    /opt/videofront
        celery.pid
        celerybeat.pid
        celerybeat-schedule
        venv/bin/
            celery
            gunicorn
        videofront/
            manage.py
            videofront/
                settings_prod.py

### Install requirements

    pip install gunicorn

### Collect static assets

By default, static assets will be stored in the `static/` subfolder:

    ./manage.py collectstatic

### Process supervision

The recommended approach is to start gunicorn and celery workers under supervision with `supervisorctl`.

Install `supervisor`:

    sudo apt install supervisor

Edit `/etc/supervisor/conf.d/videofront.conf`:

    [group:videofront]
    programs=gunicorn,celery,celery-beat

    [program:gunicorn]
    command=/opt/videofront/venv/bin/gunicorn --name videofront --workers 12 --bind=127.0.0.1:8000 --log-level=INFO videofront.wsgi:application
    directory=/opt/videofront/videofront/
    environment=DJANGO_SETTINGS_MODULE="videofront.settings_prod"
    autostart=true
    autorestart=true
    user=videofront
    priority=997

    [program:celery]
    command=/opt/videofront/venv/bin/celery worker -A videofront --loglevel=INFO --pidfile=/opt/videofront/celery.pid --hostname 'w1.%%h'
    directory=/opt/videofront/videofront/
    environment=DJANGO_SETTINGS_MODULE="videofront.settings_prod"
    autostart=true
    autorestart=true
    user=videofront
    priority=998

    [program:celery-beat]
    command=/opt/videofront/venv/bin/celery beat -A videofront --loglevel=INFO --pidfile=/opt/videofront/celerybeat.pid --schedule /opt/videofront/celerybeat-schedule
    directory=/opt/videofront/videofront/
    environment=DJANGO_SETTINGS_MODULE="videofront.settings_prod"
    autostart=true
    autorestart=true
    user=videofront
    priority=999

Reload your configuration with:

    sudo supervisorctl update

Restart all Videofront services with:

    sudo supervisorctl restart videofront:

### Serve content with nginx

Recommended nginx configuration in `/etc/nginx/sites-enabled/videofront`:

    upstream django {
        server 127.0.0.1:8000;
    }

    server {
        listen 80;
        server_name example.com; # FIXME

        client_max_body_size 20M;

        location /static/ {
            # This is according to the STATIC_ROOT setting
            alias /opt/videofront/videofront/static/;
        }
        # The following is necessary only if you are planning on streaming videos
        # from disk with the local backend
        location /backend/storage/ {
            # Here we assume that the ASSETS_ROOT_URL setting refers to the same
            # domain name that is used to access the API.
            # The path defined here should be VIDEO_STORAGE_ROOT/.
            alias /home/regis/Desktop/tmp/videos/videofront/storage/;
        }
        
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $http_host;
        proxy_redirect off;

        location ~ ^/api/v1/videos/(.*)/upload/ {
            # Max video upload size
            client_max_body_size 1G;

            proxy_pass http://django;
        }

        location / {
            proxy_pass http://django;
        }
    }

Reload nginx configuration:

    sudo service nginx reload

## Future work

Videofront is still in early beta, although it is already used in production at [FUN-MOOC](https://www.fun-mooc.fr). Here is the list of upcoming features, by decreasing priority:

- Creation of an `/embed` endpoint for easy video integration inside iframes
- Viewer statistics
- More evolved permission system, with public & private videos
- ... We are open to feature requests! Just [open a new issue](https://github.com/regisb/videofront/issues), describe your problem and we'll start the conversation from there.

## License

The code in this repository is licensed under version 3 of the AGPL unless otherwise noted. Your rights and duties are summarised [here](https://tldrlegal.com/license/gnu-affero-general-public-license-v3-(agpl-3.0)). Please see the LICENSE file for details.
