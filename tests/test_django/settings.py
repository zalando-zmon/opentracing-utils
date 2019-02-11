ROOT_URLCONF = 'urls'

SECRET_KEY = 'euowhnfckwnqopifnkadc;wmfjgwkns'

INSTALLED_APPS = (
    'app',
)

MIDDLEWARE_CLASSES = (
    'opentracing_utils.OpenTracingHttpMiddleware',
)

MIDDLEWARE = MIDDLEWARE_CLASSES
