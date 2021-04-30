import itertools
from typing import Dict, List

import serpy

from search_server.helpers.fields import StaticField
from search_server.helpers.serializers import JSONLDContextDictSerializer
from search_server.resources.shared.relationship import Relationship


class RelationshipsSection(JSONLDContextDictSerializer):
    label = serpy.MethodField()
    stype = StaticField(
        label="type",
        value="rism:RelationshipsSection"
    )
    items = serpy.MethodField()

    def get_label(self, obj: Dict):
        req = self.context.get("request")
        transl: Dict = req.app.ctx.translations

        return transl.get("records.relations")

    def get_items(self, obj: Dict) -> List[Dict]:
        people: List = obj.get("related_people_json", [])
        institutions: List = obj.get("related_institutions_json", [])
        places: List = obj.get("related_places_json", [])

        all_relationships = itertools.chain(people, institutions, places)

        return Relationship(all_relationships,
                            many=True,
                            context={"request": self.context.get("request")}).data
