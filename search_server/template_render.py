from sanic.log import logger

from search_server.resources.template_data.template_data import (
    AboutTemplateData,
    FrontTemplateData,
    InstitutionTemplateData,
    PersonTemplateData,
    PublicationTemplateData,
    SourceTemplateData,
    TemplateData,
    WorkTemplateData,
)


def render_template(app_context, req, data_obj: dict | None) -> str:
    record_tmpl = app_context.template_env.get_template("main.html.j2")
    record_type = data_obj["type"]
    request_ctx = {"request": req}
    logger.debug("Record type: %s", record_type)
    tmpl_vars: dict

    match record_type:
        case "rism:Source":
            tmpl_vars = SourceTemplateData(data_obj, context=request_ctx).serialized
        case "rism:Person":
            tmpl_vars = PersonTemplateData(data_obj, context=request_ctx).serialized
        case "rism:Institution":
            tmpl_vars = InstitutionTemplateData(
                data_obj, context=request_ctx
            ).serialized
        case "rism:Work":
            tmpl_vars = WorkTemplateData(data_obj, context=request_ctx).serialized
        case "rism:Publication":
            tmpl_vars = PublicationTemplateData(
                data_obj, context=request_ctx
            ).serialized
        case "rism:Front":
            tmpl_vars = FrontTemplateData(data_obj, context=request_ctx).serialized
        case "rism:About":
            tmpl_vars = AboutTemplateData(data_obj, context=request_ctx).serialized
        case _:
            logger.debug("Using default template data response for %s", record_type)
            tmpl_vars = TemplateData(data_obj, context=request_ctx).serialized

    return record_tmpl.render(**tmpl_vars)
