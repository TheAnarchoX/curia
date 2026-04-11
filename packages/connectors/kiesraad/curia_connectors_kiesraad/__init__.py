"""Kiesraad (Dutch Electoral Council) connector for Curia.

Fetches official election results from:
- data.overheid.nl (REST API, CKAN-based)
- Kiesraad website (EML / Election Markup Language files)

Data available (all elections since 2010):
- Tweede Kamer elections
- Eerste Kamer elections
- Provinciale Staten elections
- Gemeenteraad (municipal council) elections
- Waterschappen elections
- European Parliament elections (NL)

Results include per-municipality breakdowns, candidate-level votes,
party-level aggregates, and seat allocations.

See: https://www.kiesraad.nl/verkiezingen/verkiezingsuitslagen
"""
