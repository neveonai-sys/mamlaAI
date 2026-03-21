from __future__ import annotations

from datetime import datetime, timezone

from ecourts_scraper.cache.collections import get_db, get_reference_collection


STATIC_REFERENCE_SECTIONS = {
    "case-status": {
        "title": "Case Status",
        "tabs": [
            {"id": "party-name", "label": "Party Name", "enabled": True},
            {"id": "case-number", "label": "Case Number", "enabled": True},
            {"id": "filing-number", "label": "Filing Number", "enabled": True},
            {"id": "advocate", "label": "Advocate", "enabled": True},
            {"id": "fir-number", "label": "FIR Number", "enabled": False},
            {"id": "act", "label": "Act", "enabled": False},
            {"id": "case-type", "label": "Case Type", "enabled": False},
        ],
        "status_options": [
            {"id": "pending", "label": "Pending"},
            {"id": "disposed", "label": "Disposed"},
            {"id": "both", "label": "Both"},
        ],
        "advocate_modes": [
            {"id": "advocate-name", "label": "Advocate Name"},
            {"id": "bar-code", "label": "Bar Code"},
            {"id": "date-case-list", "label": "Date Case List"},
        ],
        "case_types": [
            "ARBITRATION CASE",
            "ARBITRATION R.D.",
            "CIVIL APPEAL",
            "CIVIL REVISION",
            "CRIMINAL APPEAL",
            "CRIMINAL REVISION",
            "WRIT PETITION",
        ],
    },
    "court-orders": {
        "title": "Court Orders",
        "tabs": [
            {"id": "party-name", "label": "Party Name", "enabled": True},
            {"id": "case-number", "label": "Case Number", "enabled": True},
            {"id": "court-number", "label": "Court Number", "enabled": True},
            {"id": "order-date", "label": "Order Date", "enabled": True},
        ],
        "order_types": [
            {"id": "interim", "label": "Interim Orders"},
            {"id": "final", "label": "Final Orders"},
            {"id": "both", "label": "Both"},
        ],
        "case_types": [
            {"id": "civil", "label": "Civil"},
            {"id": "criminal", "label": "Criminal"},
        ],
    },
    "cause-list": {
        "title": "Cause List",
        "list_types": [
            {"id": "civil", "label": "Civil"},
            {"id": "criminal", "label": "Criminal"},
        ],
    },
    "caveat": {
        "title": "Caveat",
        "search_modes": [
            {"id": "anywhere", "label": "Anywhere"},
            {"id": "starting-with", "label": "Starting with"},
            {"id": "subordinate-court", "label": "Subordinate Court"},
            {"id": "caveat-number", "label": "Caveat Number"},
        ],
    },
}


def _slug(value: str) -> str:
    return (value or "").strip().lower().replace(" ", "-")


def _pick_first(doc: dict, keys: list[str], default: str = "") -> str:
    for key in keys:
        value = doc.get(key)
        if value not in (None, ""):
            return str(value)
    return default


class EcourtsReferenceDataManager:
    def __init__(self):
        self._db = get_db()
        self._col = get_reference_collection()

    def get_dataset(self, reference_key: str) -> dict | None:
        return self._col.find_one({"reference_key": reference_key}, {"_id": 0})

    def upsert_dataset(
        self,
        reference_key: str,
        data: list | dict,
        *,
        scope: str,
        source: str,
        meta: dict | None = None,
    ) -> dict:
        now = datetime.now(timezone.utc)
        doc = {
            "reference_key": reference_key,
            "scope": scope,
            "source": source,
            "data": data,
            "meta": meta or {},
            "refreshed_at": now,
        }
        self._col.update_one({"reference_key": reference_key}, {"$set": doc}, upsert=True)
        return self.get_dataset(reference_key) or doc

    def get_or_build(self, reference_key: str, builder, *, scope: str, source: str, meta: dict | None = None) -> dict:
        existing = self.get_dataset(reference_key)
        if existing and existing.get("data") not in (None, [], {}):
            return existing
        return self.upsert_dataset(reference_key, builder(), scope=scope, source=source, meta=meta)

    def get_static_section(self, section: str) -> dict | None:
        payload = STATIC_REFERENCE_SECTIONS.get(section)
        if payload is None:
            return None
        return self.get_or_build(
            f"static:{section}",
            lambda: payload,
            scope="static",
            source="code",
            meta={"section": section},
        )

    def get_district_states(self) -> dict:
        return self.get_or_build(
            "district-courts:states",
            self._build_district_states,
            scope="district-courts",
            source="state_district_court_data",
        )

    def get_districts(self, state_name: str) -> dict:
        return self.get_or_build(
            f"district-courts:districts:{_slug(state_name)}",
            lambda: self._build_districts(state_name),
            scope="district-courts",
            source="state_district_court_data",
            meta={"state_name": state_name},
        )

    def get_complexes(self, state_name: str, district_name: str) -> dict:
        return self.get_or_build(
            f"district-courts:complexes:{_slug(state_name)}:{_slug(district_name)}",
            lambda: self._build_complexes(state_name, district_name),
            scope="district-courts",
            source="district_court_complex_map",
            meta={"state_name": state_name, "district_name": district_name},
        )

    def get_courts(self, state_name: str, district_name: str, complex_code: str) -> dict:
        return self.get_or_build(
            f"district-courts:courts:{_slug(state_name)}:{_slug(district_name)}:{_slug(complex_code)}",
            lambda: self._build_courts(state_name, district_name, complex_code),
            scope="district-courts",
            source="district_court_complex_court_map",
            meta={
                "state_name": state_name,
                "district_name": district_name,
                "complex_code": complex_code,
            },
        )

    def _build_district_states(self) -> list[dict]:
        pipeline = [
            {
                "$group": {
                    "_id": "$state_name",
                    "state_id": {"$first": "$state_id"},
                }
            },
            {"$sort": {"_id": 1}},
        ]
        rows = self._db["state_district_court_data"].aggregate(pipeline)
        return [
            {"id": str(row.get("state_id") or row["_id"]), "name": row["_id"]}
            for row in rows
            if row.get("_id")
        ]

    def _build_districts(self, state_name: str) -> list[dict]:
        pipeline = [
            {"$match": {"state_name": state_name}},
            {
                "$group": {
                    "_id": "$district_name",
                    "district_id": {"$first": "$district_id"},
                }
            },
            {"$sort": {"_id": 1}},
        ]
        rows = self._db["state_district_court_data"].aggregate(pipeline)
        return [
            {"id": str(row.get("district_id") or row["_id"]), "name": row["_id"]}
            for row in rows
            if row.get("_id")
        ]

    def _build_complexes(self, state_name: str, district_name: str) -> list[dict]:
        collection_names = set(self._db.list_collection_names())
        complexes: list[dict] = []

        if "district_court_complex_map" in collection_names:
            mapped = self._db["district_court_complex_map"].find(
                {
                    "$or": [
                        {"state_name": state_name, "district_name": district_name},
                        {"state": state_name, "district": district_name},
                    ]
                },
                {"_id": 0},
            )
            for doc in mapped:
                complex_id = _pick_first(doc, ["complex_id", "id", "court_complex_id", "code"])
                complex_name = _pick_first(doc, ["complex_name", "name", "court_complex_name", "label"])
                if complex_id and complex_name:
                    complexes.append({
                        "id": complex_id,
                        "name": complex_name,
                        "district_name": district_name,
                        "state_name": state_name,
                        "source": "stored-mapping",
                    })

        if complexes:
            complexes.sort(key=lambda item: item["name"])
            return complexes

        sample = self._db["state_district_court_data"].find_one(
            {"state_name": state_name, "district_name": district_name},
            {"district_id": 1, "district_name": 1, "state_name": 1},
        )
        if not sample:
            return []

        fallback_id = str(sample.get("district_id") or district_name)
        return [{
            "id": fallback_id,
            "name": f"{district_name} District Court Complex",
            "district_name": district_name,
            "state_name": state_name,
            "source": "synthetic-fallback",
        }]

    def _build_courts(self, state_name: str, district_name: str, complex_code: str) -> list[dict]:
        collection_names = set(self._db.list_collection_names())
        courts: list[dict] = []

        if "district_court_complex_court_map" in collection_names:
            mapped = self._db["district_court_complex_court_map"].find(
                {
                    "$or": [
                        {
                            "state_name": state_name,
                            "district_name": district_name,
                            "$or": [
                                {"complex_id": complex_code},
                                {"court_complex_id": complex_code},
                                {"complex_code": complex_code},
                            ],
                        },
                        {
                            "state": state_name,
                            "district": district_name,
                            "$or": [
                                {"complex_id": complex_code},
                                {"court_complex_id": complex_code},
                                {"complex_code": complex_code},
                            ],
                        },
                    ]
                },
                {"_id": 0},
            )
            for doc in mapped:
                court_id = _pick_first(doc, ["court_id", "id", "code", "court_platform_assigned_id"])
                court_name = _pick_first(doc, ["court_name", "name", "label"])
                if court_id and court_name:
                    courts.append({
                        "id": court_id,
                        "name": court_name,
                        "platform_id": _pick_first(doc, ["court_platform_assigned_id", "platform_id"]),
                        "complex_id": complex_code,
                        "source": "stored-mapping",
                    })

        if courts:
            courts.sort(key=lambda item: item["name"])
            return courts

        cursor = self._db["state_district_court_data"].find(
            {"state_name": state_name, "district_name": district_name},
            {"_id": 0, "court_id": 1, "court_name": 1, "court_platform_assigned_id": 1},
        )
        seen = set()
        for doc in cursor:
            court_name = doc.get("court_name")
            if not court_name or court_name in seen:
                continue
            seen.add(court_name)
            courts.append({
                "id": str(doc.get("court_id") or doc.get("court_platform_assigned_id") or court_name),
                "name": court_name,
                "platform_id": doc.get("court_platform_assigned_id", ""),
                "complex_id": complex_code,
                "source": "state-district-court-data",
            })
        courts.sort(key=lambda item: item["name"])
        return courts