"""Tweede Kamer (House of Representatives) connector for Curia.

Fetches parliamentary data from the official OData v4 API:
https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0/

Data available (CC-0 license, no auth required):
- Persoon (members of parliament)
- Fractie (parliamentary groups / parties)
- Document (bills, motions, amendments, reports)
- Zaak (legislative cases / dossiers)
- Stemming (votes)
- Vergadering (plenary sessions)
- Commissie (committees)
- Activiteit (activities / events)
- Kamerstukdossier (parliamentary paper dossiers)

See: https://opendata.tweedekamer.nl/documentatie/odata-api
"""

from curia_connectors_tweedekamer.connector import MemberPartySyncResult, TweedeKamerConnector, VoteSyncResult
from curia_connectors_tweedekamer.odata_client import (
    Activiteit,
    Agendapunt,
    Besluit,
    Commissie,
    CommissieLid,
    CommissieZetel,
    Document,
    DocumentActor,
    Fractie,
    FractieZetel,
    FractieZetelPersoon,
    Kamerstukdossier,
    ODataClient,
    ODataEntity,
    Persoon,
    QueryOptions,
    Stemming,
    Vergadering,
    Zaak,
    ZaakActor,
)

__all__ = [
    "Agendapunt",
    "Activiteit",
    "Besluit",
    "Commissie",
    "CommissieLid",
    "CommissieZetel",
    "Document",
    "DocumentActor",
    "Fractie",
    "FractieZetel",
    "FractieZetelPersoon",
    "Kamerstukdossier",
    "MemberPartySyncResult",
    "ODataClient",
    "ODataEntity",
    "Persoon",
    "QueryOptions",
    "Stemming",
    "TweedeKamerConnector",
    "Vergadering",
    "VoteSyncResult",
    "Zaak",
    "ZaakActor",
]
