# Security policy

Please report a suspected vulnerability privately to the repository owner rather than opening a public issue.

Never commit:

- NASA FIRMS map keys;
- private Cesium ion tokens;
- cloud deployment credentials;
- farm owner identities or confidential field records; or
- unpublished research datasets without permission.

Browser variables prefixed `VITE_` are public by design. A Cesium browser token must be scoped and domain-restricted. `FIRMS_MAP_KEY` belongs only in the backend environment.
