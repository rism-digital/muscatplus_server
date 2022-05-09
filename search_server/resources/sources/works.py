import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.serializers import JSONLDContextDictSerializer
from shared_helpers.solr_connection import SolrResult


# TBD.
class WorksSection(JSONLDContextDictSerializer):
    label = serpy.MethodField()
    stype = StaticField(
        label="type",
        value="rism:WorksSection"
    )

    def get_label(self, obj: SolrResult):
        req = self.context.get("request")
        transl: dict = req.app.ctx.translations

        return transl.get("records.work")
