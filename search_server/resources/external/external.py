import logging
import re
from typing import Optional

import ypres

from search_server.resources.people.person import Person
from search_server.resources.institutions.institution import Institution
from search_server.resources.sources.full_source import FullSource
from shared_helpers.identifiers import get_identifier, PROJECT_ID_SUB, PROJECT_IDENTIFIERS
from shared_helpers.solr_connection import SolrConnection

log = logging.getLogger("mp_server")


async def handle_external_request(
        req,
        project: str,
        resource_type: str,
        ext_id: str
) -> Optional[dict]:
    solr_id: str = f"{project}_{resource_type}_{ext_id}"
    external_record = await SolrConnection.get(solr_id)

    if not external_record:
        log.warning("No record found for external/%s/%s/%s", project, resource_type, ext_id)
        return None

    return await ExternalRecord(external_record, context={"request": req,
                                                          "direct_request": True}).data


class ExternalRecord(ypres.AsyncDictSerializer):
    erid = ypres.MethodField(
        label="id"
    )
    ertype = ypres.StaticField(
        label="type",
        value="rism:ExternalRecord"
    )
    erproj = ypres.MethodField(
        label="project"
    )

    record = ypres.MethodField()

    def get_erid(self, obj: dict) -> str:
        req = self.context.get("request")
        project: str = obj["project_s"]
        srtype: str = obj["type"]
        id_value: str = re.sub(PROJECT_ID_SUB, "", obj.get("id"))

        return get_identifier(req,
                              "external.external",
                              project=project,
                              resource_type=srtype,
                              ext_id=id_value)

    def get_erproj(self, obj: dict) -> str:
        proj = obj.get("project_s", "rism")
        return PROJECT_IDENTIFIERS[proj]

    async def get_record(self, obj: dict) -> dict:
        req = self.context.get("request")
        return await _record_type_router(req, obj)


async def _record_type_router(req, obj: dict) -> dict:
    obj_type = obj["type"]

    if obj_type == "source":
        source: dict = await FullSource(obj,
                                        context={"request": req}).data
        # replace the "normal" URL with the URL from the project.
        source['id'] = obj["record_uri_sni"]
        return source

    elif obj_type == "person":
        person: dict = await Person(obj,
                                    context={"request": req,
                                             "direct_request": True}).data
        person["id"] = obj["record_uri_sni"]
        return person

    elif obj_type == "institution":
        institution: dict = await Institution(obj,
                                              context={"request": req,
                                                       "direct_request": True}).data
        institution["id"] = obj["record_uri_sni"]
        return institution

    else:
        return {}
