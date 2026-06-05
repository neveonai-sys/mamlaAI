"""
Canonical legal document versions.

Bump the version string here whenever T&C or Privacy Policy content changes.
This value is embedded in every consent_event record so that historic audits can
show exactly which version the user accepted. The endpoint GET /api/users/legal-doc-versions/
returns these values to the frontend before showing consent dialogs.
"""

LEGAL_DOC_VERSIONS = {
    "terms_of_service": "1.0",
    "privacy_policy": "1.0",
    "cookie_preferences": "1.0",
}

# Documents whose version is authoritative on the server — client-supplied version is
# ignored and replaced with the value above.
SERVER_AUTHORITATIVE_TYPES = {"terms_of_service", "privacy_policy"}
