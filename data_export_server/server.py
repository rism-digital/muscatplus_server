import sentry_sdk
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sanic import Sanic

from data_export_server.routes.sitemap import sitemap_blueprint
from data_export_server.routes.opengraph import opengraph_blueprint
from data_export_server.routes.sigla import sigla_blueprint

app = Sanic("mp_dataexport")
config: dict = yaml.safe_load(open('configuration.yml', 'r'))

# Make the application configuration object available in the app context
app.ctx.config = config

debug_mode: bool = config["common"]["debug"]

if debug_mode is False:
    from sentry_sdk.integrations.sanic import SanicIntegration

    # If we have semver then remove the leading 'v', e.g., 'v1.1.1' -> '1.1.1'
    # The full release string would then be 'muscatplus_server@1.1.1'
    # Otherwise, use the version string verbatim, e.g., 'muscatplus_server@development'.
    version_string: str = config['common']['version']
    if version_string.startswith("v"):
        release = version_string[1:]
    else:
        release = version_string

    sentry_sdk.init(
        dsn=config["sentry"]["export"]["dsn"],
        integrations=[SanicIntegration()],
        environment=config["sentry"]["environment"],
        release=f"muscatplus_server@{release}",
    )

template_env = Environment(
    loader=FileSystemLoader('data_export_server/templates'),
    autoescape=select_autoescape(['xml'])
)

app.ctx.template_env = template_env

# register routes with their blueprints
app.blueprint(sitemap_blueprint)
app.blueprint(opengraph_blueprint)
app.blueprint(sigla_blueprint)
