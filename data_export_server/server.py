import sentry_sdk
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sanic import Sanic

from data_export_server.routes.opengraph import opengraph_blueprint
from data_export_server.routes.sitemap import sitemap_blueprint

app = Sanic("mp_dataexport")

with open("configuration.yml") as c:
    config: dict = yaml.safe_load(c)

# Make the application configuration object available in the app context
app.ctx.config = config

debug_mode: bool = config["common"]["debug"]


@app.listener("before_server_start")
async def init_sentry(_) -> None:
    if debug_mode:
        return None

    from sentry_sdk.integrations.asyncio import AsyncioIntegration

    # If we have semver then remove the leading 'v', e.g., 'v1.1.1' -> '1.1.1'
    # The full release string would then be 'muscatplus_server@1.1.1'
    # Otherwise, use the version string verbatim, e.g., 'muscatplus_server@development'.
    version_string: str = config["common"]["version"]
    release = version_string[1:] if version_string.startswith("v") else version_string

    sentry_sdk.init(
        dsn=config["sentry"]["export"]["dsn"],
        integrations=[AsyncioIntegration()],
        environment=config["sentry"]["environment"],
        release=f"muscatplus_server@{release}",
    )

    return None


template_env = Environment(
    loader=FileSystemLoader("data_export_server/templates"),
    autoescape=select_autoescape(["xml"]),
)

app.ctx.template_env = template_env

# register routes with their blueprints
app.blueprint(sitemap_blueprint)
app.blueprint(opengraph_blueprint)
