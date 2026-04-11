"""Eerste Kamer (Dutch Senate) connector for Curia.

The Eerste Kamer does not provide an official open data API.
Data must be scraped from the website or obtained indirectly:

- eerstekamer.nl — official website (HTML scraping)
- OpenSanctions — structured member data API
- officielebekendmakingen.nl — published legislation

Data targets:
- Senate members and party affiliations
- Committee memberships
- Legislative proceedings (wetsvoorstellen)
- Voting records (where published)
- Debates and plenary sessions

See: https://www.eerstekamer.nl
"""
