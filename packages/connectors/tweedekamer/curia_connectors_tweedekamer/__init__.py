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

from curia_connectors_tweedekamer.connector import TweedeKamerConnector
from curia_connectors_tweedekamer.odata_client import (
    Activiteit,
    Agendapunt,
    Besluit,
    Commissie,
    CommissieLid,
    Document,
    DocumentActor,
    Fractie,
    FractieZetel,
    Kamerstukdossier,
    ODataClient,
    ODataEntity,
    Persoon,
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
    "Document",
    "DocumentActor",
    "Fractie",
    "FractieZetel",
    "Kamerstukdossier",
    "ODataClient",
    "ODataEntity",
    "Persoon",
    "Stemming",
    "TweedeKamerConnector",
    "Vergadering",
    "Zaak",
    "ZaakActor",
]
