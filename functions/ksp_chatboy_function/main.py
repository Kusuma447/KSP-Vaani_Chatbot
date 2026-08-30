import os
import re
import json
import time
import requests
import zcatalyst_sdk

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL_PRIMARY = os.getenv("GEMINI_MODEL_PRIMARY", "gemini-3.7-flash").strip()
GEMINI_MODEL_FALLBACK = os.getenv("GEMINI_MODEL_FALLBACK", "gemini-3.6-flash").strip()
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"


def _gemini_url(model):
    return GEMINI_BASE_URL.format(model)

conversation_memory = {}
conversation_state = {}
REFERENCE_CACHE = {"loaded_at": 0, "data": {}}
REFERENCE_CACHE_TTL = 300

# ============================================================
# SECURITY / GOVERNANCE
# ============================================================

VAANI_ENFORCE_AUTH = os.getenv("VAANI_ENFORCE_AUTH", "true").strip().lower() in {
    "1", "true", "yes", "on"
}

VAANI_ALLOWED_ROLES = {
    role.strip()
    for role in os.getenv(
        "VAANI_ALLOWED_ROLES",
        "App Administrator,App User,Investigator,Analyst,Supervisor"
    ).split(",")
    if role.strip()
}

AUDIT_TABLE_NAME = "VaaniAuditLog"
VAANI_AUDIT_REQUIRED = os.getenv("VAANI_AUDIT_REQUIRED", "true").strip().lower() in {
    "1", "true", "yes", "on"
}

SCHEMA_DESCRIPTION = """
Karnataka State Police crime database in Zoho Catalyst Data Store.

CaseMaster: CaseMasterID, CrimeNo, CaseNO, CrimeRegisteredDate,
PolicePersonID, PoliceStationID, CaseCategoryID, GravityOffenceID,
CrimeMajorHeadID, CrimeMinorHeadID, CaseStatusID, CourtID,
IncidentFromDate, IncidentToDate, InfoReceivedPSDate, latitude,
longitude, BriefFacts

Accused: AccusedMasterID, CaseMasterID, AccusedName, AgeYear, GenderID, PersonID
Victim: VictimMasterID, CaseMasterID, VictimName, AgeYear, GenderID, VictimPolice
ComplainantDetails: ComplainantID, CaseMasterID, ComplainantName, AgeYear,
OccupationID, ReligionID, CasteID, GenderID
Act: ActCode, ActDescription, ShortName, Active
Section: ActCode, SectionCode, SectionDescription, Active
ActSectionAssociation: CaseMasterID, ActID, SectionID, ActOrderID, SectionOrderID
ChargesheetDetails: CSID, CaseMasterID, csdate, cstype, PolicePersonID
ArrestSurrender: ArrestSurrenderID, CaseMasterID, ArrestSurrenderTypeID,
ArrestSurrenderDate, ArrestSurrenderStateId, ArrestSurrenderDistrictId,
PoliceStationID, IOID, CourtID, AccusedMasterID, IsAccused, IsComplainantAccused
CrimeHead: CrimeHeadID, CrimeGroupName, Active
CrimeSubHead: CrimeSubHeadID, CrimeHeadID, CrimeHeadName, SeqID
CaseCategory: CaseCategoryID, LookupValue
GravityOffence: GravityOffenceID, LookupValue
CaseStatusMaster: CaseStatusID, CaseStatusName
Unit: UnitID, UnitName, TypeID, ParentUnit, StateID, DistrictID, Active
District: DistrictID, DistrictName, StateID, Active
State: StateID, StateName, NationalityID, Active
Employee: EmployeeID, DistrictID, UnitID, RankID, DesignationID, KGID,
FirstName, EmployeeDOB, GenderID, BloodGroupID, PhysicallyChallenged, AppointmentDate
Court: CourtID, CourtName, DistrictID, StateID, Active
Rank: Rank, RankID, RankName, Hierarchy, Active
Designation: DesignationID, DesignationName, Active

Rules: ZCQL only; SELECT only; no SELECT *; no COUNT(*); max 4 joins;
never use complaints/sqlite_master; never invent columns or tables.
"""

ALL_FIRS_QUERY = """
SELECT CaseMasterID, CrimeNo, CaseNO, CrimeRegisteredDate,
PolicePersonID, PoliceStationID, CaseCategoryID, GravityOffenceID,
CrimeMajorHeadID, CrimeMinorHeadID, CaseStatusID, CourtID,
IncidentFromDate, IncidentToDate, InfoReceivedPSDate, latitude,
longitude, BriefFacts
FROM CaseMaster
LIMIT 50
""".strip()


RECENT_FIRS_QUERY = """
SELECT CaseMasterID, CrimeNo, CaseNO, CrimeRegisteredDate,
PolicePersonID, PoliceStationID, CaseCategoryID, GravityOffenceID,
CrimeMajorHeadID, CrimeMinorHeadID, CaseStatusID, CourtID,
IncidentFromDate, IncidentToDate, InfoReceivedPSDate, latitude,
longitude, BriefFacts
FROM CaseMaster
ORDER BY CrimeRegisteredDate DESC
LIMIT 20
""".strip()

ALL_ACCUSED_QUERY = """
SELECT AccusedMasterID, CaseMasterID, AccusedName, AgeYear, GenderID, PersonID
FROM Accused
LIMIT 300
""".strip()

CASE_LOOKUP_QUERY = """
SELECT CaseMasterID, CrimeNo, CaseNO, CrimeRegisteredDate, BriefFacts,
PoliceStationID, CaseCategoryID, GravityOffenceID, CrimeMajorHeadID,
CrimeMinorHeadID, CaseStatusID, CourtID, latitude, longitude
FROM CaseMaster
LIMIT 300
""".strip()

MASTER_QUERIES = {
    "Unit": "SELECT UnitID, UnitName, DistrictID, StateID FROM Unit",
    "CaseCategory": "SELECT CaseCategoryID, LookupValue FROM CaseCategory",
    "GravityOffence": "SELECT GravityOffenceID, LookupValue FROM GravityOffence",
    "CrimeHead": "SELECT CrimeHeadID, CrimeGroupName FROM CrimeHead",
    "CrimeSubHead": "SELECT CrimeSubHeadID, CrimeHeadID, CrimeHeadName FROM CrimeSubHead",
    "CaseStatusMaster": "SELECT CaseStatusID, CaseStatusName FROM CaseStatusMaster",
    "Court": "SELECT CourtID, CourtName, DistrictID, StateID FROM Court",
    "Employee": "SELECT EmployeeID, FirstName, UnitID, RankID, DesignationID FROM Employee",
    "District": "SELECT DistrictID, DistrictName, StateID FROM District",
    "State": "SELECT StateID, StateName FROM State",
}


def flatten_rows(rows):
    out = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        clean = {}
        for key, value in row.items():
            if isinstance(value, dict):
                for k2, v2 in value.items():
                    clean[k2] = v2
            else:
                clean[key] = value
        out.append(clean)
    return out


def execute_zcql(app, query):
    result = app.zcql().execute_query(query)
    if isinstance(result, list):
        rows = result
    elif isinstance(result, dict):
        rows = result.get("content", result.get("data", []))
    else:
        rows = []
    return flatten_rows(rows)


def build_lookup(rows, id_field, value_field):
    return {str(r[id_field]): r.get(value_field) for r in rows if r.get(id_field) is not None}


def load_reference_data(app):
    now = time.time()
    if REFERENCE_CACHE["data"] and now - REFERENCE_CACHE["loaded_at"] < REFERENCE_CACHE_TTL:
        return REFERENCE_CACHE["data"]
    data = {}
    for name, query in MASTER_QUERIES.items():
        try:
            data[name] = execute_zcql(app, query)
        except Exception as exc:
            print(f"REFERENCE ERROR [{name}]: {exc}")
            data[name] = []
    REFERENCE_CACHE["data"] = data
    REFERENCE_CACHE["loaded_at"] = now
    return data


def enrich_case_rows(app, rows):
    if not rows:
        return rows
    m = load_reference_data(app)
    units = build_lookup(m["Unit"], "UnitID", "UnitName")
    categories = build_lookup(m["CaseCategory"], "CaseCategoryID", "LookupValue")
    gravity = build_lookup(m["GravityOffence"], "GravityOffenceID", "LookupValue")
    heads = build_lookup(m["CrimeHead"], "CrimeHeadID", "CrimeGroupName")
    subheads = build_lookup(m["CrimeSubHead"], "CrimeSubHeadID", "CrimeHeadName")
    statuses = build_lookup(m["CaseStatusMaster"], "CaseStatusID", "CaseStatusName")
    courts = build_lookup(m["Court"], "CourtID", "CourtName")
    officers = build_lookup(m["Employee"], "EmployeeID", "FirstName")
    districts = build_lookup(m["District"], "DistrictID", "DistrictName")
    states = build_lookup(m["State"], "StateID", "StateName")
    out = []
    for row in rows:
        r = dict(row)
        r["StationName"] = units.get(str(row.get("PoliceStationID")))
        r["CrimeCategory"] = categories.get(str(row.get("CaseCategoryID")))
        r["Gravity"] = gravity.get(str(row.get("GravityOffenceID")))
        r["CrimeGroup"] = heads.get(str(row.get("CrimeMajorHeadID")))
        r["CrimeType"] = subheads.get(str(row.get("CrimeMinorHeadID")))
        r["Status"] = statuses.get(str(row.get("CaseStatusID")))
        r["CourtName"] = courts.get(str(row.get("CourtID")))
        r["OfficerName"] = officers.get(str(row.get("PolicePersonID")))
        r["DistrictName"] = districts.get(str(row.get("DistrictID")))
        r["StateName"] = states.get(str(row.get("StateID")))
        out.append(r)
    return out


def load_case_index(app):
    # Keep the case index enriched because downstream cross-pillar analysis
    # needs human-readable station/crime labels in addition to IDs.
    rows = execute_zcql(app, CASE_LOOKUP_QUERY)
    try:
        rows = enrich_case_rows(app, rows)
    except Exception as exc:
        print(f"CASE INDEX ENRICHMENT ERROR: {exc}")
    return {str(r["CaseMasterID"]): r for r in rows if r.get("CaseMasterID") is not None}


def extract_fir(text):
    match = re.search(r"\bFIR[-\s]?(\d{3,})\b", text, flags=re.IGNORECASE)
    return f"FIR-{match.group(1)}" if match else None


def is_investigation_question(text):
    q = text.lower().strip()
    english = any(
        p in q for p in [
            "investigate", "investigation", "intelligence summary",
            "case intelligence", "analyze fir", "analyse fir",
            "details of fir", "details for fir", "tell me about fir"
        ]
    )
    kannada = any(
        p in q for p in [
            "ತನಿಖೆ", "ವಿಚಾರಣೆ", "ವಿವರಗಳು", "ಕೇಸ್ ವಿವರ", "ಪ್ರಕರಣದ ವಿವರ"
        ]
    )
    return bool(extract_fir(text)) and (english or kannada)


def get_case_by_fir(app, fir):
    safe = fir.replace("'", "''")
    query = f"""
SELECT CaseMasterID, CrimeNo, CaseNO, CrimeRegisteredDate,
PolicePersonID, PoliceStationID, CaseCategoryID, GravityOffenceID,
CrimeMajorHeadID, CrimeMinorHeadID, CaseStatusID, CourtID,
IncidentFromDate, IncidentToDate, InfoReceivedPSDate, latitude,
longitude, BriefFacts
FROM CaseMaster
WHERE CaseNO = '{safe}'
LIMIT 1
""".strip()
    rows = execute_zcql(app, query)
    if not rows:
        return None, query
    return enrich_case_rows(app, rows)[0], query


def query_by_case_id(table, case_id, fields, limit=100):
    return f"SELECT {', '.join(fields)} FROM {table} WHERE CaseMasterID = {int(case_id)} LIMIT {limit}"


def build_case_intelligence(app, case):

    case_id = int(case["CaseMasterID"])

    # --------------------------------------------------------
    # CASE-RELATED TABLES
    # --------------------------------------------------------

    queries = {
        "accused": query_by_case_id(
            "Accused",
            case_id,
            [
                "AccusedMasterID",
                "CaseMasterID",
                "AccusedName",
                "AgeYear",
                "GenderID",
                "PersonID"
            ]
        ),

        "victims": query_by_case_id(
            "Victim",
            case_id,
            [
                "VictimMasterID",
                "CaseMasterID",
                "VictimName",
                "AgeYear",
                "GenderID",
                "VictimPolice"
            ]
        ),

        "complainants": query_by_case_id(
            "ComplainantDetails",
            case_id,
            [
                "ComplainantID",
                "CaseMasterID",
                "ComplainantName",
                "AgeYear",
                "OccupationID",
                "ReligionID",
                "CasteID",
                "GenderID"
            ]
        ),

        "legal": query_by_case_id(
            "ActSectionAssociation",
            case_id,
            [
                "CaseMasterID",
                "ActID",
                "SectionID",
                "ActOrderID",
                "SectionOrderID"
            ]
        ),

        "chargesheets": query_by_case_id(
            "ChargesheetDetails",
            case_id,
            [
                "CSID",
                "CaseMasterID",
                "csdate",
                "cstype",
                "PolicePersonID"
            ]
        ),

        "arrests": query_by_case_id(
            "ArrestSurrender",
            case_id,
            [
                "ArrestSurrenderID",
                "CaseMasterID",
                "ArrestSurrenderTypeID",
                "ArrestSurrenderDate",
                "PoliceStationID",
                "IOID",
                "CourtID",
                "AccusedMasterID",
                "IsAccused",
                "IsComplainantAccused"
            ]
        )
    }

    data = {}

    for name, query in queries.items():

        try:
            data[name] = execute_zcql(
                app,
                query
            )

        except Exception as exc:

            print(
                f"CASE INTELLIGENCE QUERY FAILED [{name}]: {exc}"
            )

            data[name] = []

    # --------------------------------------------------------
    # RESOLVE LEGAL ACT / SECTION REFERENCES
    # --------------------------------------------------------

    try:

        acts = execute_zcql(
            app,
            "SELECT ActCode, ActDescription, ShortName FROM Act LIMIT 300"
        )

        sections = execute_zcql(
            app,
            "SELECT ActCode, SectionCode, SectionDescription FROM Section LIMIT 300"
        )

        act_map = {
            str(row.get("ActCode")): row
            for row in acts
        }

        section_map = {
            f"{row.get('ActCode')}:{row.get('SectionCode')}": row
            for row in sections
        }

        legal_resolved = []

        for item in data["legal"]:

            act = act_map.get(
                str(item.get("ActID")),
                {}
            )

            section = section_map.get(
                f"{act.get('ActCode', item.get('ActID'))}:{item.get('SectionID')}",
                {}
            )

            legal_resolved.append({
                **item,

                "ActName": (
                    act.get("ActDescription")
                    or act.get("ShortName")
                ),

                "ActShortName": act.get(
                    "ShortName"
                ),

                "SectionName": (
                    section.get("SectionDescription")
                    or item.get("SectionID")
                )
            })

        data["legal"] = legal_resolved

    except Exception as exc:

        print(
            "LEGAL RESOLUTION FAILED:",
            exc
        )

    # --------------------------------------------------------
    # FIND RELATED CASES THROUGH SHARED ACCUSED
    # --------------------------------------------------------

    accused_all = execute_zcql(
        app,
        ALL_ACCUSED_QUERY
    )

    target_person_ids = set()
    target_names = set()

    for accused in data["accused"]:

        if accused.get("PersonID") is not None:

            target_person_ids.add(
                str(accused["PersonID"])
            )

        if accused.get("AccusedName"):

            target_names.add(
                accused["AccusedName"]
                .strip()
                .lower()
            )

    related_case_ids = set()
    related_people = []

    for accused in accused_all:

        if str(
            accused.get("CaseMasterID")
        ) == str(case_id):

            continue

        same_person = (
            accused.get("PersonID") is not None
            and str(accused.get("PersonID"))
            in target_person_ids
        )

        same_name = (
            accused.get("AccusedName")
            and accused.get("AccusedName")
            .strip()
            .lower()
            in target_names
        )

        if same_person or same_name:

            related_case_ids.add(
                str(accused.get("CaseMasterID"))
            )

            related_people.append(
                accused
            )

    case_index = load_case_index(
        app
    )

    related_cases = []

    for related_id in sorted(
        related_case_ids,
        key=lambda x:
            int(x)
            if x.isdigit()
            else x
    ):

        case_row = case_index.get(
            related_id
        )

        if case_row:

            related_cases.append({
                "CaseMasterID": related_id,

                "FIR": (
                    case_row.get("CaseNO")
                    or case_row.get("CrimeNo")
                    or f"Case {related_id}"
                ),

                "CrimeNo": case_row.get(
                    "CrimeNo"
                ),

                "Date": case_row.get(
                    "CrimeRegisteredDate"
                ),

                "BriefFacts": case_row.get(
                    "BriefFacts"
                )
            })

    data["related_cases"] = related_cases
    data["related_people"] = related_people

    # --------------------------------------------------------
    # DEDUPLICATED RELATIONSHIP EVIDENCE
    # --------------------------------------------------------

    unique_people = {}

    for person in related_people:

        person_id = person.get(
            "PersonID"
        )

        person_name = (
            person.get("AccusedName")
            or "Unknown"
        ).strip()

        if person_id is not None:

            identity_key = (
                f"id:{person_id}"
            )

        else:

            identity_key = (
                f"name:{person_name.lower()}"
            )

        if identity_key not in unique_people:

            unique_people[identity_key] = {
                "PersonID": person_id,
                "PersonName": person_name
            }

    relationship_evidence = []

    for person in sorted(
        unique_people.values(),
        key=lambda x:
            (x.get("PersonName") or "").lower()
    ):

        person_id = person.get(
            "PersonID"
        )

        person_name = (
            person.get("PersonName")
            or "Unknown"
        )

        shared_case_ids = []

        for accused in accused_all:

            same_identity = False

            if (
                person_id is not None
                and accused.get("PersonID") is not None
            ):

                same_identity = (
                    str(accused.get("PersonID"))
                    == str(person_id)
                )

            if not same_identity:

                same_identity = (
                    (
                        accused.get("AccusedName")
                        or ""
                    )
                    .strip()
                    .lower()
                    ==
                    person_name
                    .strip()
                    .lower()
                )

            if (
                same_identity
                and str(
                    accused.get("CaseMasterID")
                ) != str(case_id)
            ):

                related_id = str(
                    accused.get("CaseMasterID")
                )

                if related_id not in shared_case_ids:

                    shared_case_ids.append(
                        related_id
                    )

        shared_cases = []

        for related_id in sorted(
            shared_case_ids,
            key=lambda x:
                int(x)
                if x.isdigit()
                else x
        ):

            case_row = case_index.get(
                related_id,
                {}
            )

            shared_cases.append({
                "CaseMasterID": related_id,

                "FIR": (
                    case_row.get("CaseNO")
                    or case_row.get("CrimeNo")
                    or f"Case {related_id}"
                ),

                "CrimeNo": case_row.get(
                    "CrimeNo"
                ),

                "Date": case_row.get(
                    "CrimeRegisteredDate"
                )
            })

        if shared_cases:

            relationship_evidence.append({
                "PersonID": person_id,

                "PersonName": person_name,

                "Relationship":
                    "Same accused identity",

                "SharedCaseCount":
                    len(shared_cases),

                "SharedCases":
                    shared_cases
            })

    data[
        "relationship_evidence"
    ] = relationship_evidence

    # --------------------------------------------------------
    # INVESTIGATION TIMELINE
    # --------------------------------------------------------

    timeline = []

    def add_timeline_event(label, value, event_type):
        if value:
            timeline.append({
                "label": label,
                "date": str(value),
                "event_type": event_type,
            })

    add_timeline_event("Incident started", case.get("IncidentFromDate"), "incident")
    add_timeline_event("Incident ended", case.get("IncidentToDate"), "incident")
    add_timeline_event("Information received at police station", case.get("InfoReceivedPSDate"), "information")
    add_timeline_event("FIR registered", case.get("CrimeRegisteredDate"), "registration")

    for row in data["chargesheets"]:
        add_timeline_event("Chargesheet recorded", row.get("csdate"), "chargesheet")

    for row in data["arrests"]:
        add_timeline_event("Arrest / surrender recorded", row.get("ArrestSurrenderDate"), "arrest")

    timeline.sort(key=lambda x: x["date"])
    data["investigation_timeline"] = timeline

    # --------------------------------------------------------
    # SIMILAR PAST CASES
    # --------------------------------------------------------

    similar_cases = []
    current_id = str(case_id)

    for candidate_id, candidate in case_index.items():
        if str(candidate_id) == current_id:
            continue

        score = 0
        basis = []

        if (
            candidate.get("CrimeMinorHeadID") is not None
            and str(candidate.get("CrimeMinorHeadID")) == str(case.get("CrimeMinorHeadID"))
        ):
            score += 5
            basis.append("same crime type")

        if (
            candidate.get("CrimeMajorHeadID") is not None
            and str(candidate.get("CrimeMajorHeadID")) == str(case.get("CrimeMajorHeadID"))
        ):
            score += 3
            basis.append("same crime group")

        if (
            candidate.get("PoliceStationID") is not None
            and str(candidate.get("PoliceStationID")) == str(case.get("PoliceStationID"))
        ):
            score += 2
            basis.append("same station")

        if (
            candidate.get("GravityOffenceID") is not None
            and str(candidate.get("GravityOffenceID")) == str(case.get("GravityOffenceID"))
        ):
            score += 1
            basis.append("same gravity")

        if score == 0:
            continue

        similar_cases.append({
            "CaseMasterID": str(candidate_id),
            "FIR": candidate.get("CaseNO") or candidate.get("CrimeNo") or f"Case {candidate_id}",
            "CrimeNo": candidate.get("CrimeNo"),
            "Date": candidate.get("CrimeRegisteredDate"),
            "BriefFacts": candidate.get("BriefFacts"),
            "Status": candidate.get("Status"),
            "SimilarityScore": score,
            "MatchBasis": basis,
        })

    similar_cases.sort(
        key=lambda x: (-x["SimilarityScore"], x.get("Date") or "")
    )
    data["similar_cases"] = similar_cases[:5]

    # --------------------------------------------------------
    # INVESTIGATIVE LEADS
    # --------------------------------------------------------

    leads = []

    if data["related_cases"]:
        leads.append({
            "priority": "High",
            "lead": "Review cross-case links and recurring accused identities.",
            "basis": f"{len(data['related_cases'])} related case(s) found through accused identity matches.",
        })

    if data["similar_cases"]:
        leads.append({
            "priority": "Medium",
            "lead": "Compare similar past cases for investigation outcomes and common patterns.",
            "basis": f"{len(data['similar_cases'])} structurally similar case(s) identified.",
        })

    if not data["legal"]:
        leads.append({
            "priority": "Medium",
            "lead": "Verify applicable Act/Section associations for the case.",
            "basis": "No Act/Section association record is currently available.",
        })

    if not data["chargesheets"]:
        leads.append({
            "priority": "Medium",
            "lead": "Review the current investigation status and chargesheet milestone.",
            "basis": "No chargesheet record is currently available.",
        })

    if not data["arrests"] and data["accused"]:
        leads.append({
            "priority": "Low",
            "lead": "Check arrest/surrender status where applicable.",
            "basis": "Accused records exist but no arrest/surrender record is available.",
        })

    data["investigative_leads"] = leads[:6]

    # --------------------------------------------------------
    # INVESTIGATIVE SIGNALS
    # --------------------------------------------------------

    data["signals"] = {
        "accused_count":
            len(data["accused"]),

        "victim_count":
            len(data["victims"]),

        "complainant_count":
            len(data["complainants"]),

        "legal_link_count":
            len(data["legal"]),

        "related_case_count":
            len(data["related_cases"]),

        "chargesheeted":
            len(data["chargesheets"]) > 0,

        "arrest_or_surrender_recorded":
            len(data["arrests"]) > 0
    }

    # --------------------------------------------------------
    # FINAL RETURN
    # --------------------------------------------------------

    return data



def build_connected_investigation(app, case, intelligence):
    """Build a bounded cross-pillar evidence view for a case.

    This does not invent new conclusions. It links already-supported case,
    person, location, and crime-type evidence into one investigation view.
    """
    case_id = str(case.get("CaseMasterID"))
    accused = intelligence.get("accused") or []
    case_index = load_case_index(app)

    # Person-centric connections for accused attached to this case.
    try:
        accused_rows = execute_zcql(app, ALL_ACCUSED_QUERY)
    except Exception:
        accused_rows = []

    people = []
    seen_people = set()
    for person in accused:
        name = (person.get("AccusedName") or "").strip()
        pid = person.get("PersonID")
        if not name and pid is None:
            continue
        key = f"id:{pid}" if pid is not None else f"name:{normalize_person_name(name)}"
        if key in seen_people:
            continue
        seen_people.add(key)
        try:
            net = build_network_analysis(accused_rows, case_index, name or str(pid))
        except Exception:
            net = {"target_network": None}
        target = (net.get("target_network") or {}).get("target") or {}
        connections = (net.get("target_network") or {}).get("connections") or []
        target_cases = target.get("Cases") or []
        people.append({
            "name": target.get("AccusedName") or name or str(pid),
            "case_count": int(target.get("CaseCount") or len(target_cases)),
            "connections": [
                {"name": c.get("AccusedName"), "shared_cases": int(c.get("ConnectionStrength") or 0)}
                for c in connections[:5]
            ],
            "case_ids": [c.get("CaseMasterID") for c in target_cases if c.get("CaseMasterID") is not None],
        })

    # Spatial recurrence around the current case.
    location = None
    same_cell = []
    try:
        lat = round(float(case.get("latitude")), 2)
        lon = round(float(case.get("longitude")), 2)
        location = {"latitude": lat, "longitude": lon}
        for cid, row in case_index.items():
            try:
                rlat = round(float(row.get("latitude")), 2)
                rlon = round(float(row.get("longitude")), 2)
            except (TypeError, ValueError):
                continue
            if (rlat, rlon) == (lat, lon):
                same_cell.append({
                    "case_id": cid,
                    "fir": row.get("CaseNO") or row.get("CrimeNo") or f"Case {cid}",
                    "date": row.get("CrimeRegisteredDate"),
                    "crime_type": row.get("CrimeType") or row.get("CrimeGroup") or "Unknown",
                    "station": row.get("StationName") or "Unknown station",
                })
        same_cell.sort(key=lambda x: (x.get("date") or "", x.get("fir") or ""))
    except (TypeError, ValueError):
        pass

    # Crime-type recurrence among cases linked through the accused on this case.
    related_ids = set()
    for person in people:
        related_ids.update(str(x) for x in person.get("case_ids") or [])
    related_ids.discard(case_id)
    crime_counts = {}
    for cid in related_ids:
        row = case_index.get(str(cid), {})
        label = row.get("CrimeType") or row.get("CrimeGroup") or "Unknown"
        crime_counts[label] = crime_counts.get(label, 0) + 1
    recurring_types = sorted(
        [{"crime_type": k, "case_count": v} for k, v in crime_counts.items()],
        key=lambda x: (-x["case_count"], x["crime_type"].lower())
    )[:5]

    # Evidence-backed early-warning signals that are directly relevant to this case.
    # We reuse the existing deterministic engine and filter only by evidence tied
    # to this case/person/spatial cell. No predictive inference is introduced.
    early_signals = []
    try:
        early = build_early_warning_analytics(app)
        candidate_signals = early.get("signals", []) if isinstance(early, dict) else []
        case_fir = case.get("CaseNO") or case.get("CrimeNo")
        person_names = {p["name"].strip().lower() for p in people if p.get("name")}
        cell_keys = set()
        if location:
            cell_keys.add((round(float(location["latitude"]), 2), round(float(location["longitude"]), 2)))
        for signal in candidate_signals:
            evidence_cases = {str(x).strip() for x in (signal.get("evidence_cases") or [])}
            title = (signal.get("title") or "").lower()
            evidence = (signal.get("evidence_summary") or signal.get("evidence") or "").lower()
            relevant = bool(case_fir and str(case_fir) in evidence_cases)
            if not relevant and person_names:
                relevant = any(name in title or name in evidence for name in person_names)
            if not relevant and cell_keys:
                coords = signal.get("coordinates") or signal.get("hotspot")
                if isinstance(coords, (list, tuple)) and len(coords) >= 2:
                    try:
                        relevant = (round(float(coords[0]), 2), round(float(coords[1]), 2)) in cell_keys
                    except (TypeError, ValueError):
                        pass
            if relevant:
                early_signals.append({
                    "signal_id": signal.get("signal_id") or "EW",
                    "severity": signal.get("severity") or "MEDIUM",
                    "priority_score": signal.get("priority_score"),
                    "title": signal.get("title") or "Evidence-backed signal",
                    "evidence": signal.get("evidence_summary") or signal.get("evidence") or "Supporting evidence available.",
                    "lead": signal.get("recommended_lead") or "Review the linked evidence.",
                })
    except Exception as exc:
        print("CONNECTED EARLY WARNING FILTER FAILED:", exc)

    leads = []
    for person in people:
        if person["case_count"] > 1:
            leads.append({
                "priority": "High",
                "title": f"Review {person['name']}'s cross-case connections",
                "evidence": f"{person['name']} appears in {person['case_count']} case(s)."
            })
    if len(same_cell) > 1:
        leads.append({
            "priority": "Medium",
            "title": "Review recurring activity at the case location",
            "evidence": f"{len(same_cell)} FIRs fall in the same 0.01-degree spatial cell."
        })
    if recurring_types:
        leads.append({
            "priority": "Medium",
            "title": f"Compare recurring crime type: {recurring_types[0]['crime_type']}",
            "evidence": f"{recurring_types[0]['case_count']} linked case(s) share this crime type."
        })
    # Keep connected leads focused on NEW investigator actions.
    # Early-warning signals are rendered in their own section and should not
    # be duplicated here.

    return {
        "case": {
            "fir": case.get("CaseNO") or case.get("CrimeNo") or "Case",
            "crime_type": case.get("CrimeType") or case.get("CrimeGroup") or "Unknown",
        },
        "people": people,
        "location": location,
        "same_cell_cases": same_cell,
        "recurring_crime_types": recurring_types,
        "early_warning_signals": early_signals[:5],
        "leads": leads[:7],
        "method": "Deterministic linkage of case, accused identity, spatial cell, crime-type evidence, and relevant early-warning signals. No predictive inference is applied.",
    }

def build_investigation_workspace(case, intel):
    """Evidence-only case workspace metadata for the investigator UI."""
    signals = intel.get("signals") or {}
    leads = intel.get("investigative_leads") or []
    related_cases = intel.get("related_cases") or []
    relationship_evidence = intel.get("relationship_evidence") or []
    timeline = intel.get("investigation_timeline") or []
    return {
        "case_id": case.get("CaseMasterID"),
        "fir": case.get("CaseNO") or case.get("CrimeNo") or "Case",
        "crime_type": case.get("CrimeType") or case.get("CrimeGroup") or "Unknown",
        "station": case.get("StationName") or "Unknown station",
        "status": case.get("Status") or "Unknown",
        "gravity": case.get("Gravity") or "Unknown",
        "registered": case.get("CrimeRegisteredDate"),
        "location": {"latitude": case.get("latitude"), "longitude": case.get("longitude")},
        "counts": {
            "accused": int(signals.get("accused_count") or 0),
            "victims": int(signals.get("victim_count") or 0),
            "related_cases": len(related_cases),
            "connected_people": len(relationship_evidence),
            "legal_links": int(signals.get("legal_link_count") or signals.get("legal_section_count") or 0),
            "timeline_events": len(timeline),
        },
        "lead_count": len(leads),
        "focus": (
            "Cross-case relationship evidence is the primary lead."
            if related_cases else
            "Review available evidence and investigation milestones."
        ),
    }


def build_case_summary(case, intel):
    people = intel["related_people"]
    signals = intel["signals"]
    pieces = []

    pieces.append(
        f"{case.get('CaseNO') or case.get('CrimeNo') or 'Case'} is a "
        f"{case.get('CrimeType') or 'crime'} case registered at "
        f"{case.get('StationName') or 'an unidentified station'} on "
        f"{case.get('CrimeRegisteredDate') or 'an unknown date'}."
    )
    if case.get("Status"):
        pieces.append(f"Current status: {case['Status']}.")
    if case.get("Gravity"):
        pieces.append(f"Gravity: {case['Gravity']}.")
    if signals["related_case_count"]:
        pieces.append(
            f"The case shares an accused identity with {signals['related_case_count']} other case(s), "
            "which is the strongest current relationship signal."
        )
    if signals["chargesheeted"]:
        pieces.append("A chargesheet record is present.")
    if signals["arrest_or_surrender_recorded"]:
        pieces.append("An arrest/surrender record is present.")
    return " ".join(pieces)


def ask_gemini(question, memory_hint):
    """Generate ZCQL with bounded retries for transient Gemini failures.

    Deterministic Vaani paths do not call Gemini at all. This function is only
    used for genuinely open-ended natural-language requests.
    """
    if not GEMINI_API_KEY:
        return "-- GEMINI_AUTH_ERROR: language engine credentials are unavailable"

    prompt = f"""
You are Vaani, a query intelligence engine for the Karnataka State Police crime database.

{SCHEMA_DESCRIPTION}

Previous context:
{memory_hint}

Reference date: 2026-08-23

User question:
{question}

Generate ONE valid ZCQL SELECT query. Maximum 4 joins. No SELECT *.
Never query sqlite_master. Never invent tables or columns. Never query complaints.
Return ONLY the query.
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 1200,
        },
    }

    transient_statuses = {429, 500, 502, 503, 504}
    max_attempts = 2
    models = [GEMINI_MODEL_PRIMARY]
    if GEMINI_MODEL_FALLBACK and GEMINI_MODEL_FALLBACK != GEMINI_MODEL_PRIMARY:
        models.append(GEMINI_MODEL_FALLBACK)

    last_transient = None
    for model_index, model in enumerate(models):
        for attempt in range(1, max_attempts + 1):
            try:
                response = requests.post(
                    _gemini_url(model),
                    params={"key": GEMINI_API_KEY},
                    headers={"Content-Type": "application/json"},
                    json=payload,
                    timeout=(5, 25),
                )

                status = response.status_code

                if status == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])

                    if not candidates:
                        return (
                            "-- GEMINI_RESPONSE_ERROR: "
                            + json.dumps(data, ensure_ascii=False)[:1200]
                        )

                    text = (
                        candidates[0]
                        .get("content", {})
                        .get("parts", [{}])[0]
                        .get("text", "")
                        .strip()
                    )

                    text = (
                        text
                        .replace("```sql", "")
                        .replace("```", "")
                        .strip()
                    )

                    match = re.search(
                        r"\bSELECT\b.*",
                        text,
                        flags=re.IGNORECASE | re.DOTALL,
                    )

                    return match.group(0).strip() if match else text

                if status in transient_statuses:
                    last_transient = status
                    if attempt < max_attempts:
                        time.sleep(1.5 * (2 ** (attempt - 1)))
                        continue
                    break

                # Do not expose provider credentials/errors to the client.
                # Keep the diagnostic in server logs and return a stable internal code.
                detail = response.text[:1200]
                print(f"GEMINI HTTP ERROR [{status}] [{model}]: {detail}")
                try:
                    error_payload = response.json()
                except Exception:
                    error_payload = {}

                reason_text = json.dumps(error_payload, ensure_ascii=False).lower()
                if status == 400 and "api_key_invalid" in reason_text:
                    return "-- GEMINI_AUTH_ERROR: language engine credentials are unavailable"
                return f"-- GEMINI_HTTP_ERROR: HTTP {status}"

            except (requests.Timeout, requests.ConnectionError) as exc:
                last_transient = type(exc).__name__
                if attempt < max_attempts:
                    time.sleep(1.5 * (2 ** (attempt - 1)))
                    continue
                break

            except Exception as exc:
                return "-- GEMINI_EXCEPTION: " + repr(exc)

    return (
        "-- GEMINI_TRANSIENT_ERROR: Gemini temporarily unavailable "
        f"after bounded retries on {', '.join(models)}. Last status: {last_transient}"
    )



def is_safe_query(query):
    if not query or not re.match(r"^SELECT\b", query.strip(), flags=re.IGNORECASE):
        return False
    upper = query.upper()
    for word in ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "REPLACE", "ATTACH", "DETACH", "PRAGMA", "SQLITE_MASTER", "SQLITE_SCHEMA", "COMPLAINTS"]:
        if re.search(rf"\b{re.escape(word)}\b", upper):
            return False
    if ";" in query:
        return False
    if len(re.findall(r"\b(?:INNER|LEFT|RIGHT|FULL)?\s*JOIN\b", query, flags=re.IGNORECASE)) > 4:
        return False
    return True


def get_memory(session_id):
    history = conversation_memory.get(session_id, [])
    return "\n".join(f"User: {x['question']}\nQuery: {x['query']}" for x in history[-5:]) or "No previous context."


def save_memory(session_id, question, query):
    conversation_memory.setdefault(session_id, []).append({"question": question, "query": query})
    conversation_memory[session_id] = conversation_memory[session_id][-10:]


def get_conversation_state(session_id):
    return conversation_state.get(session_id, {})


def update_conversation_state(session_id, **kwargs):
    state = conversation_state.setdefault(session_id, {})
    for key, value in kwargs.items():
        if value is not None:
            state[key] = value
    allowed = {
        "active_person", "active_fir", "active_case_ids",
        "active_filters", "last_intent", "last_query_type", "last_query_text"
    }
    for key in list(state):
        if key not in allowed:
            state.pop(key, None)
    return state


def is_all_firs_question(text):
    q = re.sub(r"\s+", " ", text.lower().strip())
    return any(
        p in q for p in [
            "show me all firs", "show all firs", "show all fir",
            "list all firs", "all firs", "show cases", "all cases",
            "ಎಲ್ಲ fir", "ಎಲ್ಲ firs", "ಎಲ್ಲ FIR", "ಎಲ್ಲ FIRಗಳನ್ನು",
            "ಎಲ್ಲಾ FIR", "ಎಲ್ಲಾ FIRಗಳನ್ನು", "ಎಲ್ಲ ಪ್ರಕರಣ", "ಎಲ್ಲ ಪ್ರಕರಣಗಳನ್ನು"
        ]
    )


def is_recent_firs_question(text):
    q = re.sub(r"\s+", " ", text.lower().strip())
    return any(term in q for term in [
        "recent fir", "recent firs",
        "latest fir", "latest firs",
        "newest fir", "newest firs",
        "recently registered fir", "recently registered firs",
        "latest registered fir", "latest registered firs",
        "recent cases", "latest cases",
        "ಇತ್ತೀಚಿನ fir", "ಇತ್ತೀಚಿನ FIR", "ಇತ್ತೀಚಿನ ಪ್ರಕರಣ",
        "ಇತ್ತೀಚೆಗೆ ನೋಂದಾಯಿತ fir", "ಇತ್ತೀಚೆಗೆ ನೋಂದಾಯಿಸಿದ fir"
    ])


def _contains_any(text, phrases):
    return any(p in text for p in phrases)


def _parse_kannada_month_year(text):
    months = {
        "ಜನವರಿ": 1, "ಫೆಬ್ರವರಿ": 2, "ಮಾರ್ಚ್": 3, "ಏಪ್ರಿಲ್": 4,
        "ಮೇ": 5, "ಜೂನ್": 6, "ಜುಲೈ": 7, "ಆಗಸ್ಟ್": 8,
        "ಸೆಪ್ಟೆಂಬರ್": 9, "ಅಕ್ಟೋಬರ್": 10, "ನವೆಂಬರ್": 11, "ಡಿಸೆಂಬರ್": 12,
    }
    for word, month in months.items():
        if word in text:
            m = re.search(r"\b(20\d{2})\b", text)
            return (month, int(m.group(1)) if m else 2026)
    return None


def _normalize_kannada_person_alias(name):
    aliases = {
        "ರವಿ ಕುಮಾರ್": "Ravi Kumar",
        "ಅರುಣ್ ದಾಸ್": "Arun Das",
        "ಸುರೇಶ್ ರಾವ್": "Suresh Rao",
        "ಮಹೇಶ್ ಗೌಡ": "Mahesh Gowda",
        "ಕಿರಣ್ ಶಾ": "Kiran Shah",
    }
    cleaned = re.sub(r"\s+", " ", name.strip())
    return aliases.get(cleaned, cleaned)


def _month_start(year, month):
    return f"{year:04d}-{month:02d}-01"


def _next_month(year, month):
    if month == 12:
        return year + 1, 1
    return year, month + 1


def _parse_month_year(text):
    months = {
        "january": 1, "jan": 1, "february": 2, "feb": 2,
        "march": 3, "mar": 3, "april": 4, "apr": 4,
        "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
        "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
        "october": 10, "oct": 10, "november": 11, "nov": 11,
        "december": 12, "dec": 12,
    }
    m = re.search(
        r"\b(" + "|".join(months.keys()) + r")\s+(20\d{2})\b",
        text.lower()
    )
    if not m:
        return None
    return months[m.group(1)], int(m.group(2))


def _parse_iso_date(text):
    m = re.search(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b", text)
    if not m:
        return None
    return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"


def _resolve_reference_ids(app, table_name, id_field, value_field, needle):
    refs = load_reference_data(app).get(table_name, [])
    needle = needle.strip().lower()
    exact = []
    partial = []
    for row in refs:
        value = str(row.get(value_field) or "").strip()
        if not value or row.get(id_field) is None:
            continue
        if value.lower() == needle:
            exact.append(str(row[id_field]))
        elif needle in value.lower() or value.lower() in needle:
            partial.append(str(row[id_field]))
    return exact or partial


# ============================================================
# CANONICAL INTENT / ENTITY / CONSTRAINT LAYER
# ============================================================

def _normalize_query_text(text):
    # Normalize whitespace and invisible Kannada/Unicode joiner characters so
    # spoken/typed variants such as "ಹಾಟ್ಸ್ಪಾಟ್" and "ಹಾಟ್‌ಸ್ಪಾಟ್" match.
    value = (text or "").replace("\u200b", "").replace("\u200c", "").replace("\u200d", "")
    value = value.replace("\ufeff", "")
    return re.sub(r"\s+", " ", value.strip())


def _query_contains_any(q, phrases):
    # Normalize both query and phrase so Unicode joiner variants in Kannada
    # (e.g. ಹಾಟ್‌ಸ್ಪಾಟ್ vs ಹಾಟ್ಸ್ಪಾಟ್) are treated identically.
    normalized_q = _normalize_query_text(q).lower()
    return any(_normalize_query_text(p).lower() in normalized_q for p in phrases)


def resolve_pairwise_people(text, accused_rows):
    """Resolve exactly two distinct people from the actual Accused dataset."""
    q_norm = normalize_person_name(text)
    candidates = []
    seen = set()
    for row in accused_rows or []:
        name = (row.get("AccusedName") or "").strip()
        norm = normalize_person_name(name)
        if not norm or norm in seen:
            continue
        if norm in q_norm:
            candidates.append((len(norm), name))
            seen.add(norm)
    candidates.sort(key=lambda x: -x[0])
    unique = []
    used = set()
    for _, name in candidates:
        key = normalize_person_name(name)
        if key not in used:
            unique.append(name)
            used.add(key)
    return unique[:2]


def resolve_person_from_query(text, accused_rows, session_state=None):
    """Resolve a person only from actual Accused data or safe session context."""
    session_state = session_state or {}
    query_norm = normalize_person_name(text)

    # Dataset-driven direct name match. This handles arbitrary names and possessives.
    matched = []
    for row in accused_rows or []:
        name = (row.get("AccusedName") or "").strip()
        norm = normalize_person_name(name)
        if norm and norm in query_norm:
            matched.append((len(norm), name))
    if matched:
        return max(matched, key=lambda x: x[0])[1]

    # Relationship syntax fallback, validated against the dataset.
    extracted = extract_target_name(text)
    if extracted:
        extracted_norm = normalize_person_name(extracted)
        matched = []
        for row in accused_rows or []:
            name = (row.get("AccusedName") or "").strip()
            norm = normalize_person_name(name)
            if norm and (norm == extracted_norm or extracted_norm in norm or norm in extracted_norm):
                matched.append((len(norm), name))
        if matched:
            return max(matched, key=lambda x: x[0])[1]

    # Follow-up reference is safe only when a previous target exists in session state.
    if has_followup_person_reference(text):
        active = session_state.get("active_person")
        if active:
            return active

    # Kannada conversational follow-up: resolve the active person from context
    # when the user asks for that person's related cases/relationships.
    # This avoids sending a valid Kannada request to Gemini just because the
    # English person-name patterns are not present in the utterance.
    q_lower = _normalize_query_text(text).lower()
    kannada_person_followup = [
        "ಸಂಬಂಧಿಸಿದ ಪ್ರಕರಣಗಳನ್ನು ತೋರಿಸಿ",
        "ಸಂಬಂಧಿಸಿದ ಪ್ರಕರಣಗಳನ್ನು ತೋರಿಸು",
        "ಸಂಬಂಧಿಸಿದ ಪ್ರಕರಣ ತೋರಿಸಿ",
        "ಸಂಬಂಧ ಹೊಂದಿರುವವರು",
        "ಸಂಪರ್ಕ ಹೊಂದಿರುವವರು",
    ]
    if session_state.get("active_person") and (
        any(p in q_lower for p in kannada_person_followup)
        or ("ಸಂಬಂಧಿಸಿದ" in q_lower and ("ತೋರಿಸಿ" in q_lower or "ತೋರಿಸು" in q_lower))
    ):
        return session_state.get("active_person")

    return None


def classify_canonical_intent(text, session_state=None, accused_rows=None):
    """Return a stable intent representation rather than routing on exact sentences."""
    session_state = session_state or {}
    q = _normalize_query_text(text).lower()

    fir = extract_fir(text)
    if fir and ("investigat" in q or _query_contains_any(q, ["case intelligence", "case details", "analyze fir", "analyse fir", "ತನಿಖೆ", "ವಿವರ"])):
        return {"intent": "CASE_INVESTIGATION", "entities": {"fir": fir}, "constraints": {}}

    # A short hotspot request immediately after an investigation is a
    # contextual drill-down, not a new global analytics request. Keep the
    # current investigation context and use the deterministic hotspot engine.
    contextual_hotspot_phrases = [
        "show me the hotspot",
        "show the hotspot",
        "where is the hotspot",
        "show me hotspot",
        "show hotspot",
        "hotspot for this case",
        "hotspot around this case",
        "hotspot here",
        "show the map",
        "show me the map",
        # Kannada conversational hotspot follow-ups
        "ಹಾಟ್‌ಸ್ಪಾಟ್ ತೋರಿಸಿ",
        "ಹಾಟ್‌ಸ್ಪಾಟ್ ತೋರಿಸು",
        "ಹಾಟ್‌ಸ್ಪಾಟ್ ಎಲ್ಲಿದೆ",
        "ಹಾಟ್ಸ್ಪಾಟ್ ತೋರಿಸಿ",
        "ಹಾಟ್ಸ್ಪಾಟ್ ತೋರಿಸು",
        "ಹಾಟ್ಸ್ಪಾಟ್ ಎಲ್ಲಿದೆ",
        "ಹಾಟ್ಸ್ಪಾಟ್",
    ]
    has_investigation_context = bool(
        session_state.get("active_fir") or session_state.get("active_case_ids")
    )
    if has_investigation_context and _query_contains_any(q, contextual_hotspot_phrases):
        return {"intent": "CONTEXTUAL_HOTSPOT", "entities": {}, "constraints": {}}

    if ("hotspot" in q or "hotspots" in q or "spatial" in q or _query_contains_any(q, ["crime locations", "concentration"])) and _query_contains_any(q, ["repeat accused", "repeat offender", "recurring accused", "same accused", "ಪುನರಾವರ್ತಿತ ಆರೋಪಿ"]):
        return {"intent": "REPEAT_ACCUSED_HOTSPOT", "entities": {}, "constraints": {}}

    # Pairwise shared-case questions must outrank generic person-network routing.
    pairwise_people = resolve_pairwise_people(text, accused_rows or [])
    pairwise_language = _query_contains_any(q, [
        "shared by", "shared between", "common between", "common to",
        "cases shared", "shared cases", "same cases", "joint cases",
        "cases do .* share", "how many cases",
    ])
    if len(pairwise_people) == 2 and ("shared" in q or "common" in q or "same cases" in q or "between" in q):
        return {
            "intent": "PERSON_PAIR_SHARED_CASES",
            "entities": {"person_a": pairwise_people[0], "person_b": pairwise_people[1]},
            "constraints": {},
        }

    # Investigation follow-ups must stay inside the active case before global analytics.
    # These are deliberately deterministic and reuse existing case/process engines.
    has_investigation_context = bool(
        session_state.get("active_fir") or session_state.get("active_case_ids")
    )
    contextual_gap_phrases = [
        "investigation gaps",
        "missing investigation records",
        "what investigation records are missing",
        "what is missing in the investigation",
        "show me the gaps",
        "show the gaps",
        "what are the gaps",
        "check the gaps",
        # Kannada conversational investigation-gap follow-ups
        "ತನಿಖೆಯಲ್ಲಿರುವ ಅಂತರಗಳು ಯಾವುವು",
        "ತನಿಖೆಯಲ್ಲಿ ಏನು ಕೊರತೆಯಿದೆ",
        "ತನಿಖೆಯಲ್ಲಿ ಏನು ಬಾಕಿಯಿದೆ",
        "ತನಿಖೆಯ ಅಂತರಗಳನ್ನು ತೋರಿಸಿ",
    ]
    if has_investigation_context and _query_contains_any(q, contextual_gap_phrases):
        return {"intent": "CONTEXTUAL_INVESTIGATION_GAPS", "entities": {}, "constraints": {}}

    next_action_phrases = [
        "what should i check next",
        "what should we check next",
        "what should the investigator check next",
        "what should an investigator check next",
        "what should i investigate next",
        "what should we investigate next",
        "what should the investigator investigate next",
        "what should the investigated check next",
        "what should the investigator check next",
        "what should the investigator check",
        "what do i check next",
        "what do we check next",
        "what do i investigate next",
        "what is the next step",
        "what are the next steps",
        "what should i do next",
        "what should we do next",
        "recommended next step",
        "recommended next action",
        "next action",
        "next step",
        "next steps",
        # Kannada conversational next-action follow-ups
        "ಮುಂದೆ ಏನು ಪರಿಶೀಲಿಸಬೇಕು",
        "ಮುಂದೆ ಏನು ಮಾಡಬೇಕು",
        "ಮುಂದೆ ಏನು ತನಿಖೆ ಮಾಡಬೇಕು",
        "ಮುಂದೆ ತನಿಖಾಧಿಕಾರಿ ಏನು ಪರಿಶೀಲಿಸಬೇಕು",
        "ಮುಂದೆ ತನಿಖಾಧಿಕಾರಿ ಏನು ಮಾಡಬೇಕು",
    ]
    if has_investigation_context and _query_contains_any(q, next_action_phrases):
        return {"intent": "INVESTIGATIVE_NEXT_ACTION", "entities": {}, "constraints": {}}

    # Analytics must outrank generic network wording such as “most cases”.
    # This prevents monthly peak questions from being mistaken for repeat-accused queries.
    # Sociological/person-profile analytics get an explicit priority so they do not
    # fall into generic network/Gemini routing.
    sociological_type = classify_sociological_question(text)
    if sociological_type:
        return {"intent": "ANALYTICS", "entities": {"analytics_type": sociological_type}, "constraints": {}}

    analytics_type = classify_analytics_question(text)
    if analytics_type:
        return {"intent": "ANALYTICS", "entities": {"analytics_type": analytics_type}, "constraints": {}}

    person = resolve_person_from_query(text, accused_rows or [], session_state)
    relationship_language = _query_contains_any(q, [
        "connected", "connection", "linked", "associated", "related", "network",
        "shared case", "common case", "case history", "cases involving", "firs involving",
        "other cases", "previous cases", "appear in", "involved in",
        "ಸಂಪರ್ಕ", "ಸಂಬಂಧ", "ಜಾಲ", "ಲಿಂಕ್", "ಪ್ರಕರಣ", "ಎಷ್ಟು ಪ್ರಕರಣ",
        "ಅವನ", "ಅವಳ", "ಅವರ", "ಜೊತೆ"
    ])
    case_language = _query_contains_any(q, ["case", "cases", "fir", "firs", "ಪ್ರಕರಣ", "ಎಫ್ ಐಆರ್", "firs"])

    # Network intent must outrank generic case/history interpretation.
    # This covers both targeted and global network questions such as:
    #   "Who is connected to Ravi Kumar?"
    #   "Which people appear in multiple cases?"
    #   "Show repeat accused activity"
    #   "How many cases are shared by Ravi Kumar and Arun Das?"
    network_language = _query_contains_any(q, [
        "connected", "connection", "connected to", "linked", "linked to", "linked with",
        "associated with", "network", "who else", "people connected",
        "shared cases", "shared case", "common cases", "repeat offender",
        "repeat accused", "repeated accused", "multiple cases", "appear in multiple cases",
        "appear in", "same person", "people in multiple cases",
        "appears repeatedly", "appear repeatedly", "accused appears repeatedly",
        "which accused person appears repeatedly", "which accused persons appear repeatedly",
        "which accused appear repeatedly", "which accused person appears in multiple cases",
        "most cases", "most case", "highest number of cases", "most involved",
        "highest number of firs", "most firs", "most accused",
        "ಪುನರಾವರ್ತಿತ ಆರೋಪಿ", "ಬಹು ಪ್ರಕರಣ", "ಒಂದಕ್ಕಿಂತ ಹೆಚ್ಚು ಪ್ರಕರಣ",
        "ಸಂಪರ್ಕ ಹೊಂದಿರುವವರು", "ಸಂಬಂಧ ಹೊಂದಿರುವವರು", "ಯಾರೊಂದಿಗೆ", "ಯಾರು ಸಂಪರ್ಕ",
        "ಸಂಬಂಧಿಸಿದ ಪ್ರಕರಣಗಳನ್ನು ತೋರಿಸಿ", "ಸಂಬಂಧಿಸಿದ ಪ್ರಕರಣಗಳನ್ನು ತೋರಿಸು",
        "ಸಂಬಂಧಿಸಿದ ಪ್ರಕರಣ ತೋರಿಸಿ", "ಸಂಬಂಧಿಸಿದ ಪ್ರಕರಣಗಳನ್ನು ತೋರಿಸಿ",
        "ರವಿ ಕುಮಾರ್ ಗೆ ಸಂಬಂಧಿಸಿದ ಪ್ರಕರಣಗಳನ್ನು ತೋರಿಸಿ", "ರವಿಕುಮಾರ್ ಗೆ ಸಂಬಂಧಿಸಿದ ಪ್ರಕರಣಗಳನ್ನು ತೋರಿಸಿ"
    ])
    if network_language:
        return {"intent": "PERSON_NETWORK", "entities": {"person": person} if person else {}, "constraints": {}}

    if person:
        # Any explicit case/FIR reference for a resolved person is a person-case-history
        # request, including natural possessive forms such as:
        #   "Show me Ravi Kumar's cases"
        #   "Show cases of Ravi Kumar"
        #   "What FIRs does Ravi Kumar have?"
        possessive_case = bool(re.search(
            r"\b(?:case|cases|fir|firs)\b.*\b(?:of|for)\s+", q
        )) or bool(re.search(
            r"\b(?:his|her|their)\s+(?:case|cases|fir|firs)\b", q
        )) or bool(re.search(
            r"\b(?:case|cases|fir|firs)\b", q
        ))
        if case_language or possessive_case or "case history" in q or "case" in q or _query_contains_any(q, ["about", "regarding", "details on"]):
            return {"intent": "PERSON_CASE_HISTORY", "entities": {"person": person}, "constraints": {}}

    if relationship_language and person:
        return {"intent": "PERSON_NETWORK", "entities": {"person": person}, "constraints": {}}

    filters = parse_common_fir_filters(text)
    if filters:
        return {"intent": "FIR_SEARCH", "entities": {}, "constraints": filters}

    if is_recent_firs_question(text):
        return {"intent": "RECENT_FIRS", "entities": {}, "constraints": {}}

    if is_all_firs_question(text):
        return {"intent": "ALL_FIRS", "entities": {}, "constraints": {}}

    return {"intent": "OPEN_ENDED", "entities": {}, "constraints": {}}


def _active_case_ids_from_state(app, state):
    """Resolve active conversational case IDs from server-side case data."""
    state = state or {}
    ids = {str(x) for x in (state.get("active_case_ids") or []) if x is not None}
    active_fir = str(state.get("active_fir") or "").strip()
    if active_fir:
        try:
            case_index = load_case_index(app)
            for cid, row in case_index.items():
                labels = {
                    str(row.get("CaseNO") or "").strip(),
                    str(row.get("CrimeNo") or "").strip(),
                }
                if active_fir in labels:
                    ids.add(str(cid))
                    break
        except Exception as exc:
            print("ACTIVE CASE RESOLUTION FAILED:", exc)
    return ids


def build_contextual_investigation_gaps(app, session_state):
    """Filter the existing deterministic investigation-gap engine to active cases."""
    active_ids = _active_case_ids_from_state(app, session_state)
    if not active_ids:
        raise ValueError("No active investigation case context is available for investigation-gap analysis.")

    analytics = build_process_intelligence_analytics(app, "investigation_gaps")
    rows = []
    for row in analytics.get("records") or []:
        # The process engine already emits canonical FIR labels. Resolve those labels
        # against the server-side case index so client context never grants access.
        rows.append(dict(row))

    case_index = load_case_index(app)
    allowed_labels = set()
    for cid in active_ids:
        c = case_index.get(str(cid), {})
        for label in (c.get("CaseNO"), c.get("CrimeNo")):
            if label:
                allowed_labels.add(str(label).strip())

    filtered = [r for r in rows if str(r.get("FIR") or "").strip() in allowed_labels]
    total = len(filtered)
    return {
        **analytics,
        "title": "Investigation Gaps",
        "labels": [r.get("FIR") for r in filtered],
        "values": [1 for _ in filtered],
        "records": filtered,
        "matched_count": total,
        "total": total,
        "contextual": True,
        "context_case_ids": sorted(active_ids),
        "method": "Deterministic CaseMasterID linkage for the active investigation context; no LLM fallback.",
    }


def build_investigative_next_actions(app, session_state):
    """Return evidence-backed next actions from the existing case-intelligence leads."""
    active_fir = str((session_state or {}).get("active_fir") or "").strip()
    if not active_fir:
        raise ValueError("No active investigation case context is available for next-action guidance.")

    case, lookup_query = get_case_by_fir(app, active_fir)
    if not case:
        raise ValueError(f"No case was found for {active_fir}.")

    intelligence = build_case_intelligence(app, case)
    leads = intelligence.get("investigative_leads") or []
    rows = []
    for index, lead in enumerate(leads, start=1):
        rows.append({
            "Priority": lead.get("priority") or "Medium",
            "NextAction": lead.get("lead") or "Review the available evidence and investigation milestones.",
            "Evidence": lead.get("basis") or "Existing case intelligence indicates this review point.",
            "Order": index,
        })

    if not rows:
        signals = intelligence.get("signals") or {}
        rows.append({
            "Priority": "Medium",
            "NextAction": "Review the available evidence and investigation milestones.",
            "Evidence": (
                f"{signals.get('accused_count', 0)} accused, "
                f"{signals.get('related_case_count', 0)} related case(s), "
                f"{signals.get('legal_link_count', 0)} legal link(s)."
            ),
            "Order": 1,
        })

    return {
        "query_type": "analytics",
        "chart_type": "process_list",
        "title": "Recommended Next Actions",
        "labels": [r["NextAction"] for r in rows],
        "values": [1 for _ in rows],
        "records": rows,
        "total": len(rows),
        "contextual": True,
        "context_fir": active_fir,
        "source_queries": [lookup_query],
        "method": "Evidence-backed recommendations derived from the existing deterministic case-intelligence leads; no LLM inference.",
    }


def merge_contextual_filters(current_filters, state):
    """Apply previous filters only when the current query explicitly refers back to them."""
    current_filters = dict(current_filters or {})
    state = state or {}
    q = state.get("last_query_text", "").lower()
    return current_filters


def parse_common_fir_filters(text):
    q = re.sub(r"\s+", " ", text.lower().strip())
    filters = {}

    # Gravity / severity
    gravity = None
    for label, phrases in {
        "critical": ["critical gravity", "critical severity", "critical-gravity", "critical-severity"],
        "high": ["high gravity", "high severity", "high-gravity", "high-severity"],
        "medium": ["medium gravity", "medium severity", "medium-gravity", "medium-severity"],
        "low": ["low gravity", "low severity", "low-gravity", "low-severity"],
    }.items():
        if _contains_any(q, phrases):
            gravity = label
            break
    if not gravity:
        for phrase, label in {
            "ಹೆಚ್ಚಿನ ಗಂಭೀರತೆಯ": "high",
            "ಹೆಚ್ಚಿನ ಗಂಭೀರತೆ": "high",
            "ಅತಿ ಹೆಚ್ಚಿನ ಗಂಭೀರತೆಯ": "critical",
            "ಅತಿ ಗಂಭೀರತೆಯ": "critical",
            "ಮಧ್ಯಮ ಗಂಭೀರತೆಯ": "medium",
            "ಕಡಿಮೆ ಗಂಭೀರತೆಯ": "low",
        }.items():
            if phrase in text:
                gravity = label
                break
    if gravity:
        filters["gravity"] = gravity

    # Status -- avoid treating 'registered in Bengaluru' as status=Registered.
    for canonical, phrases in {
        "under investigation": ["under investigation", "status investigation", "status: investigation"],
        "registered": ["status registered", "status: registered", "registered status", "cases that are registered"],
        "chargesheet filed": ["chargesheet filed", "charge sheet filed", "status chargesheet filed", "status: chargesheet filed"],
        "trial": ["status trial", "status: trial", "cases in trial"],
        "closed": ["status closed", "status: closed", "closed cases"],
    }.items():
        if any(p in q for p in phrases):
            filters["status"] = canonical
            break

    # Crime type
    for crime in ["cyber crime", "cybercrime", "theft", "robbery", "fraud", "assault"]:
        if crime in q:
            filters["crime_type"] = "Cyber Crime" if crime == "cybercrime" else crime.title()
            break

    # English date parsing
    iso = _parse_iso_date(text)
    if iso:
        if re.search(r"\bafter\b", q):
            filters["date_from_exclusive"] = iso
        elif re.search(r"\bbefore\b", q):
            filters["date_to_exclusive"] = iso
        elif re.search(r"\bsince\b", q):
            filters["date_from"] = iso

    month_year = _parse_month_year(text)
    if month_year:
        month, year = month_year
        start = _month_start(year, month)
        if re.search(r"\bafter\b", q):
            ny, nm = _next_month(year, month)
            filters["date_from"] = _month_start(ny, nm)
        elif re.search(r"\bbefore\b", q):
            filters["date_to_exclusive"] = start
        elif re.search(r"\bsince\b", q):
            filters["date_from"] = start
        elif re.search(r"\b(?:during|in|for)\b", q):
            filters["date_from"] = start
            ny, nm = _next_month(year, month)
            filters["date_to_exclusive"] = _month_start(ny, nm)

    # Kannada date parsing
    kn_month = _parse_kannada_month_year(text)
    if kn_month:
        month, year = kn_month
        start = _month_start(year, month)
        if _contains_any(text, ["ನಂತರ", "ಆಮೇಲೆ"]):
            ny, nm = _next_month(year, month)
            filters["date_from"] = _month_start(ny, nm)
        elif _contains_any(text, ["ಮೊದಲು", "ಮುಂಚೆ"]):
            filters["date_to_exclusive"] = start
        elif _contains_any(text, ["ರಿಂದ", "ನಿಂದ"]):
            filters["date_from"] = start
        elif _contains_any(text, ["ನಲ್ಲಿ", "ನಲ್ಲಿನ"]):
            filters["date_from"] = start
            ny, nm = _next_month(year, month)
            filters["date_to_exclusive"] = _month_start(ny, nm)

    # English station/city
    station_match = re.search(r"\b(?:in|at|from)\s+([A-Za-z][A-Za-z .&'-]+?)(?=\s+(?:after|before|since|during|with|having|that|which|registered|reported|and|$)|[?.!,]|$)", text, flags=re.IGNORECASE)
    raw_station = station_match.group(1).strip() if station_match else None
    if not raw_station:
        city_match = re.search(r"\b(Bengaluru|Bangalore|Mysuru|Mysore|Mangaluru|Mangalore|Belagavi|Belgaum)\b(?=\s+(?:FIRs?|cases?|crimes?|incidents?|records?|police stations?|registered|reported|after|before|since|during|with|having|that|which|$))", text, flags=re.IGNORECASE)
        if city_match:
            raw_station = city_match.group(1).strip()

    # Kannada station/city
    if not raw_station:
        for phrase, canonical in sorted({
            "ಬೆಂಗಳೂರು ನಗರ": "bengaluru",
            "ಬೆಂಗಳೂರಿನಲ್ಲಿ": "bengaluru",
            "ಬೆಂಗಳೂರುದಲ್ಲಿ": "bengaluru",
            "ಬೆಂಗಳೂರಿನ": "bengaluru",
            "ಬೆಂಗಳೂರು": "bengaluru",
            "ಮೈಸೂರಿನಲ್ಲಿ": "mysuru",
            "ಮೈಸೂರಿನ": "mysuru",
            "ಮೈಸೂರು": "mysuru",
            "ಮಂಗಳೂರಿನಲ್ಲಿ": "mangaluru",
            "ಮಂಗಳೂರಿನ": "mangaluru",
            "ಮಂಗಳೂರು": "mangaluru",
            "ಬೆಳಗಾವಿಯಲ್ಲಿ": "belagavi",
            "ಬೆಳಗಾವಿಯ": "belagavi",
            "ಬೆಳಗಾವಿ": "belagavi",
        }.items(), key=lambda item: len(item[0]), reverse=True):
            if phrase in text:
                raw_station = canonical
                break

    if raw_station:
        aliases = {"bangalore": "bengaluru", "mysore": "mysuru", "mangalore": "mangaluru", "belgaum": "belagavi"}
        raw_station = aliases.get(raw_station.lower(), raw_station)
        if raw_station.lower() not in {"firs", "fir", "cases", "case", "the police station", "police station"}:
            filters["station_text"] = raw_station

    return filters


def build_deterministic_fir_search(app, text):
    filters = parse_common_fir_filters(text)
    if not filters:
        return None

    where = []
    params_values = []

    refs = load_reference_data(app)

    # Reference-driven entity resolution: detect any configured crime type / station /
    # status / gravity value in the query, not just a fixed demo vocabulary.
    q_raw = _normalize_query_text(text).lower()

    if "crime_type" not in filters:
        for row in refs.get("CrimeSubHead", []):
            value = str(row.get("CrimeHeadName") or "").strip()
            if value and value.lower() in q_raw:
                filters["crime_type"] = value
                break

    if "station_text" not in filters:
        station_candidates = []
        for row in refs.get("Unit", []):
            value = str(row.get("UnitName") or "").strip()
            if value and value.lower() in q_raw:
                station_candidates.append((len(value), value))
        for row in refs.get("District", []):
            value = str(row.get("DistrictName") or "").strip()
            if value and value.lower() in q_raw:
                station_candidates.append((len(value), value))
        if station_candidates:
            filters["station_text"] = max(station_candidates, key=lambda x: x[0])[1]

    if "status" not in filters:
        status_candidates = []
        for row in refs.get("CaseStatusMaster", []):
            value = str(row.get("CaseStatusName") or "").strip()
            if value and value.lower() in q_raw and "status" in q_raw:
                status_candidates.append((len(value), value))
        if status_candidates:
            filters["status"] = max(status_candidates, key=lambda x: x[0])[1]

    if "gravity" not in filters:
        gravity_candidates = []
        for row in refs.get("GravityOffence", []):
            value = str(row.get("LookupValue") or "").strip()
            if value and value.lower() in q_raw:
                gravity_candidates.append((len(value), value.lower()))
        if gravity_candidates:
            filters["gravity"] = max(gravity_candidates, key=lambda x: x[0])[1]

    if "gravity" in filters:
        gravity_rows = [
            r for r in refs.get("GravityOffence", [])
            if str(r.get("LookupValue") or "").strip().lower() == filters["gravity"]
        ]
        ids = [str(r["GravityOffenceID"]) for r in gravity_rows if r.get("GravityOffenceID") is not None]
        if ids:
            where.append("GravityOffenceID IN (" + ",".join(ids) + ")")
        else:
            return None

    if "status" in filters:
        status_ids = _resolve_reference_ids(app, "CaseStatusMaster", "CaseStatusID", "CaseStatusName", filters["status"])
        if status_ids:
            where.append("CaseStatusID IN (" + ",".join(status_ids) + ")")
        else:
            return None

    if "crime_type" in filters:
        crime_ids = _resolve_reference_ids(app, "CrimeSubHead", "CrimeSubHeadID", "CrimeHeadName", filters["crime_type"])
        if crime_ids:
            where.append("CrimeMinorHeadID IN (" + ",".join(crime_ids) + ")")
        else:
            return None

    if "station_text" in filters:
        station_ids = _resolve_reference_ids(app, "Unit", "UnitID", "UnitName", filters["station_text"])
        if not station_ids:
            # Also allow district/city wording through district master names.
            districts = _resolve_reference_ids(app, "District", "DistrictID", "DistrictName", filters["station_text"])
            if districts:
                station_ids = [
                    str(r["UnitID"])
                    for r in refs.get("Unit", [])
                    if r.get("UnitID") is not None and str(r.get("DistrictID")) in set(districts)
                ]
        if station_ids:
            where.append("PoliceStationID IN (" + ",".join(sorted(set(station_ids))) + ")")
        else:
            return None

    if "date_from" in filters:
        where.append(f"CrimeRegisteredDate >= '{filters['date_from']}'")
    if "date_from_exclusive" in filters:
        where.append(f"CrimeRegisteredDate > '{filters['date_from_exclusive']}'")
    if "date_to_exclusive" in filters:
        where.append(f"CrimeRegisteredDate < '{filters['date_to_exclusive']}'")

    if not where:
        return None

    query = """
SELECT CaseMasterID, CrimeNo, CaseNO, CrimeRegisteredDate,
PolicePersonID, PoliceStationID, CaseCategoryID, GravityOffenceID,
CrimeMajorHeadID, CrimeMinorHeadID, CaseStatusID, CourtID,
IncidentFromDate, IncidentToDate, InfoReceivedPSDate, latitude,
longitude, BriefFacts
FROM CaseMaster
""".strip()

    query += " WHERE " + " AND ".join(where)
    query += " ORDER BY CrimeRegisteredDate DESC LIMIT 50"
    return query, filters


def is_network_question(text):
    q = text.lower().strip()
    return any(
        p in q for p in [
            "network", "connected", "connection", "linked", "associated",
            "shared cases", "common cases", "repeat offender", "multiple cases",
            "appear in multiple cases", "cases involving", "case history",
            "ಸಂಪರ್ಕ", "ಸಂಬಂಧ", "ಜಾಲ", "ಲಿಂಕ್", "ಸಾಮಾನ್ಯ ಪ್ರಕರಣ",
            "ಬಹು ಪ್ರಕರಣ", "ಒಂದಕ್ಕಿಂತ ಹೆಚ್ಚು ಪ್ರಕರಣ", "ಪುನರಾವರ್ತಿತ ಆರೋಪಿ"
        ]
    )


def normalize_person_name(name):
    return re.sub(r"\s+", " ", str(name).strip().lower())


def is_target_network_question(text):
    q = text.lower().strip()
    target_phrases = [
        "who is connected to", "who is linked to", "who is associated with",
        "people connected to", "network of", "network for", "linked to",
        "associated with", "cases related to", "firs related to",
        "cases associated with", "cases linked with", "cases linked to",
        "firs linked to", "cases involving", "firs involving",
        "cases of", "firs of", "case history of",
        "how many cases", "how many firs", "which firs involve",
        "which cases involve", "show cases for", "show firs for",
        "show cases related to", "show firs related to",
        "ಯಾರೊಂದಿಗೆ", "ಯಾರು ಸಂಪರ್ಕ", "ಯಾರ ಜೊತೆ", "ಪ್ರಕರಣಗಳು", "ಪ್ರಕರಣಗಳ",
        "ಎಷ್ಟು ಪ್ರಕರಣ", "ಎಷ್ಟು fir", "ಯಾವ ಪ್ರಕರಣ", "ಸಂಪರ್ಕ ಹೊಂದಿರುವವರು"
    ]
    return any(p in q for p in target_phrases)


def extract_target_name(text):
    patterns = [
        r"who\s+is\s+(?:connected|linked|associated)\s+to\s+(.+?)[\?\.!]?$",
        r"people\s+(?:connected|linked)\s+to\s+(.+?)[\?\.!]?$",
        r"(?:connected|linked|associated)\s+to\s+(.+?)[\?\.!]?$",
        r"network\s+(?:of|for)\s+(.+?)[\?\.!]?$",
        r"cases?\s+(?:related\s+to|involving|linked\s+with|linked\s+to|associated\s+with|of)\s+(.+?)[\?\.!]?$",
        r"firs?\s+(?:related\s+to|involving|linked\s+with|linked\s+to|associated\s+with|of)\s+(.+?)[\?\.!]?$",
        r"how\s+many\s+(?:cases?|firs?)\s+(?:are\s+)?(?:linked\s+with|linked\s+to|involve)\s+(.+?)[\?\.!]?$",
        r"how\s+many\s+(?:cases?|firs?)\s+(?:is|are)\s+(.+?)\s+(?:involved\s+in|linked)\b[\?\.!]?$",
        r"(?:show|list)\s+(?:the\s+)?(?:cases?|firs?|case\s+history)\s+(?:for|of|related\s+to)\s+(.+?)[\?\.!]?$",
        r"case\s+history\s+(?:of|for)\s+(.+?)[\?\.!]?$",
        r"(.+?)\s+(?:जೊತೆ|ಸಂಪರ್ಕ|ಸಂಬಂಧ)\s+.*?(?:ಯಾರು|ಯಾವವರು|ಯಾವ ಪ್ರಕರಣ|ಎಷ್ಟು)[\?\.!]?$",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            candidate = m.group(1).strip(" \t?.,:;-")
            candidate = re.sub(r"^(?:with|to|of|for|related\s+to)\s+", "", candidate, flags=re.IGNORECASE).strip()
            if candidate:
                return _normalize_kannada_person_alias(candidate)
    return None


def extract_target_from_known_people(text, accused_rows):
    normalized_text = normalize_person_name(text)
    matches = []
    seen = set()
    for row in accused_rows:
        name = (row.get("AccusedName") or "").strip()
        if not name: continue
        key = normalize_person_name(name)
        if key and key in normalized_text and key not in seen:
            seen.add(key)
            matches.append(name)
    return max(matches, key=len) if matches else None


def has_followup_person_reference(text):
    q = _normalize_query_text(text).lower()
    return bool(re.search(r"\b(?:his|her|their|him|that person|that accused)\b", q)) or _query_contains_any(q, ["ಅವನ", "ಅವಳ", "ಅವರ"])


def build_person_case_history(accused_rows, case_index, target_name):
    """Deterministically return the cases for any person present in Accused."""
    normalized = normalize_person_name(target_name)
    grouped = {}
    for row in accused_rows or []:
        name = (row.get("AccusedName") or "").strip()
        if not name:
            continue
        norm = normalize_person_name(name)
        if norm != normalized and normalized not in norm and norm not in normalized:
            continue
        key = str(row.get("PersonID")) if row.get("PersonID") is not None else norm
        grouped.setdefault(key, {"name": name, "person_id": row.get("PersonID"), "cases": set()})["cases"].add(str(row.get("CaseMasterID")))

    if not grouped:
        return None
    person = max(grouped.values(), key=lambda x: len(x["cases"]))
    cases = []
    for cid in sorted(person["cases"], key=lambda x: int(x) if x.isdigit() else x):
        c = case_index.get(cid, {})
        cases.append({
            "CaseMasterID": cid,
            "FIR": c.get("CaseNO") or c.get("CrimeNo") or f"Case {cid}",
            "CrimeNo": c.get("CrimeNo"),
            "Date": c.get("CrimeRegisteredDate"),
            "BriefFacts": c.get("BriefFacts"),
            "StationName": c.get("StationName"),
            "CrimeType": c.get("CrimeType"),
            "Status": c.get("Status"),
            "Gravity": c.get("Gravity"),
        })
    return {
        "person": {"PersonID": person["person_id"], "AccusedName": person["name"], "CaseCount": len(cases)},
        "cases": cases,
    }


def build_network_analysis(accused_rows, case_index, target_name=None):
    """
    Deterministic person -> case -> person network analysis.

    Network evidence is intentionally bounded:
    - identity is matched by PersonID where available, otherwise normalized name
    - shared CaseMasterID is the only connection edge
    - current target's own cases are shown separately from connected people
    - connection strength = number of shared cases
    """
    people = {}
    cases = {}

    for row in accused_rows or []:
        case_id = row.get("CaseMasterID")
        name = (row.get("AccusedName") or "").strip()
        person_id = row.get("PersonID")
        if case_id is None or not name:
            continue

        normalized = normalize_person_name(name)
        key = f"id:{person_id}" if person_id is not None else f"name:{normalized}"

        person = people.setdefault(
            key,
            {
                "PersonID": person_id,
                "AccusedName": name,
                "NormalizedName": normalized,
                "CaseMasterIDs": set(),
            },
        )
        person["CaseMasterIDs"].add(str(case_id))
        cases.setdefault(str(case_id), set()).add(key)

    def case_view(cid):
        c = case_index.get(str(cid), {})
        return {
            "CaseMasterID": str(cid),
            "FIR": c.get("CaseNO") or c.get("CrimeNo") or f"Case {cid}",
            "CrimeNo": c.get("CrimeNo"),
            "Date": c.get("CrimeRegisteredDate"),
            "StationName": c.get("StationName"),
            "CrimeType": c.get("CrimeType"),
            "Status": c.get("Status"),
            "Gravity": c.get("Gravity"),
        }

    repeated = []
    for person in people.values():
        case_ids = sorted(
            person["CaseMasterIDs"],
            key=lambda x: int(x) if x.isdigit() else x,
        )
        if len(case_ids) < 2:
            continue

        repeated.append(
            {
                "PersonID": person["PersonID"],
                "AccusedName": person["AccusedName"],
                "CaseCount": len(case_ids),
                "Cases": [case_view(cid) for cid in case_ids],
            }
        )

    repeated.sort(
        key=lambda x: (-x["CaseCount"], (x["AccusedName"] or "").lower())
    )

    target_network = None
    if target_name:
        normalized_target = normalize_person_name(target_name)

        exact = [
            (k, p) for k, p in people.items()
            if p["NormalizedName"] == normalized_target
        ]
        partial = [
            (k, p) for k, p in people.items()
            if normalized_target in p["NormalizedName"]
            or p["NormalizedName"] in normalized_target
        ]

        target_candidates = exact or partial
        if target_candidates:
            target_key, target_person = target_candidates[0]

            target_case_ids = sorted(
                target_person["CaseMasterIDs"],
                key=lambda x: int(x) if x.isdigit() else x,
            )

            connections = []
            for other_key, other in people.items():
                if other_key == target_key:
                    continue

                shared_ids = sorted(
                    target_person["CaseMasterIDs"] & other["CaseMasterIDs"],
                    key=lambda x: int(x) if x.isdigit() else x,
                )
                if not shared_ids:
                    continue

                shared_cases = [case_view(cid) for cid in shared_ids]
                all_other_cases = sorted(
                    other["CaseMasterIDs"],
                    key=lambda x: int(x) if x.isdigit() else x,
                )

                station_names = sorted(
                    {
                        str(c.get("StationName"))
                        for c in shared_cases
                        if c.get("StationName")
                    }
                )
                crime_types = sorted(
                    {
                        str(c.get("CrimeType"))
                        for c in shared_cases
                        if c.get("CrimeType")
                    }
                )

                connections.append(
                    {
                        "PersonID": other["PersonID"],
                        "AccusedName": other["AccusedName"],
                        "ConnectionStrength": len(shared_ids),
                        "SharedCaseIDs": shared_ids,
                        "SharedCases": shared_cases,
                        "TotalCaseCount": len(all_other_cases),
                        "SharedStations": station_names,
                        "SharedCrimeTypes": crime_types,
                    }
                )

            connections.sort(
                key=lambda x: (
                    -int(x.get("ConnectionStrength") or 0),
                    (x.get("AccusedName") or "").lower(),
                )
            )

            target_cases = [case_view(cid) for cid in target_case_ids]

            target_network = {
                "target": {
                    "PersonID": target_person["PersonID"],
                    "AccusedName": target_person["AccusedName"],
                    "CaseCount": len(target_cases),
                    "Cases": target_cases,
                },
                "connections": connections,
                "network_summary": {
                    "target_case_count": len(target_cases),
                    "connected_people_count": len(connections),
                    "direct_shared_case_count": sum(
                        int(x.get("ConnectionStrength") or 0)
                        for x in connections
                    ),
                    "strongest_connection": (
                        connections[0]["ConnectionStrength"]
                        if connections else 0
                    ),
                },
            }

    # Build a compact graph for visualization.
    nodes = []
    edges = []

    for key, person in people.items():
        nodes.append(
            {
                "id": "person_" + key,
                "type": "person",
                "label": person["AccusedName"],
                "case_count": len(person["CaseMasterIDs"]),
            }
        )

    for cid, person_keys in cases.items():
        c = case_index.get(str(cid), {})
        nodes.append(
            {
                "id": "case_" + str(cid),
                "type": "case",
                "label": c.get("CaseNO") or c.get("CrimeNo") or f"Case {cid}",
            }
        )

        for pk in sorted(person_keys):
            edges.append(
                {
                    "source": "person_" + pk,
                    "target": "case_" + str(cid),
                    "relationship": "accused_in",
                }
            )

    return {
        "repeated_accused": repeated,
        "target_network": target_network,
        "graph": {
            "nodes": nodes,
            "edges": edges,
        },
    }


# ============================================================
# CRIME ANALYTICS
# ============================================================

def _aggregate_count(row, preferred_alias="CaseCount"):
    """Read an aggregate count defensively across Catalyst/ZCQL response shapes."""
    row = row or {}
    preferred = preferred_alias.lower()
    # 1) Prefer explicit count-like aliases/keys.
    candidates = []
    for key, value in row.items():
        k = str(key).strip().lower().replace(" ", "")
        if k == preferred or "count(" in k or k.endswith("count") or k == "count":
            candidates.append(value)
    # 2) If Catalyst returned a nested/alternate alias, inspect values.
    for value in candidates + list(row.values()):
        if isinstance(value, (dict, list, tuple)):
            continue
        try:
            number = int(value)
            if number >= 0:
                return number
        except (TypeError, ValueError):
            try:
                number = int(float(str(value).strip()))
                if number >= 0:
                    return number
            except (TypeError, ValueError):
                continue
    return 0


def _norm_label(value, fallback):
    text = " ".join(str(value or fallback).strip().split())
    return text or fallback


def _python_group(rows, group_field, label_map, fallback_prefix):
    """Fallback aggregation without COUNT/GROUP BY when Catalyst rejects aggregates."""
    agg = {}
    display_labels = {}
    for row in rows or []:
        key = row.get(group_field)
        label = _norm_label(label_map.get(str(key)), f"{fallback_prefix} {key}" if key is not None else f"Unknown {fallback_prefix.lower()}")
        norm = re.sub(r"\s+", " ", label).strip().casefold()
        display = display_labels.setdefault(norm, label)
        agg[norm] = agg.get(norm, 0) + 1
    return {display_labels[k]: v for k, v in agg.items()}



def _merge_aggregate_labels(items):
    merged = {}
    displays = {}
    for label, count in items:
        clean = _norm_label(label, "Unknown")
        norm = re.sub(r"\s+", " ", clean).strip().casefold()
        displays.setdefault(norm, clean)
        merged[norm] = merged.get(norm, 0) + int(count or 0)
    return sorted(((displays[k], v) for k, v in merged.items()), key=lambda x: (-x[1], x[0].casefold()))

def build_case_status_analytics(app):
    case_query = "SELECT CaseStatusID, COUNT(CaseMasterID) AS CaseCount FROM CaseMaster GROUP BY CaseStatusID"
    status_query = "SELECT CaseStatusID, CaseStatusName FROM CaseStatusMaster LIMIT 300"
    status_map = {}
    grouped_rows = []
    aggregate_failed = None
    try:
        grouped_rows = execute_zcql(app, case_query)
    except Exception as exc:
        aggregate_failed = str(exc)
    status_rows = execute_zcql(app, status_query)
    status_map = {str(r.get("CaseStatusID")): _norm_label(r.get("CaseStatusName"), "Unknown") for r in status_rows if r.get("CaseStatusID") is not None}

    aggregated = {}
    if grouped_rows:
        for row in grouped_rows:
            sid = row.get("CaseStatusID")
            label = _norm_label(status_map.get(str(sid)), f"Status {sid}" if sid is not None else "Unknown status")
            count = _aggregate_count(row)
            aggregated[label] = aggregated.get(label, 0) + count

    if not grouped_rows or sum(aggregated.values()) == 0:
        raw_query = "SELECT CaseMasterID, CaseStatusID FROM CaseMaster LIMIT 300"
        raw_rows = execute_zcql(app, raw_query)
        aggregated = _python_group(raw_rows, "CaseStatusID", status_map, "Status")
        source_queries = [raw_query, status_query]
        method = "Deterministic server-side retrieval followed by application-side status aggregation; aggregate ZCQL was unavailable or returned unusable counts."
    else:
        source_queries = [case_query, status_query]
        method = "Deterministic server-side aggregation of CaseMaster status IDs using CaseStatusMaster labels."

    ranked = _merge_aggregate_labels(aggregated.items())
    total = sum(x[1] for x in ranked)
    return {
        "query_type": "analytics", "chart_type": "bar", "title": "Case Status Distribution",
        "headline": "Current case lifecycle distribution across the available FIR records.",
        "labels": [x[0] for x in ranked], "values": [x[1] for x in ranked],
        "records": [{"Status": x[0], "CaseCount": x[1]} for x in ranked],
        "total": total, "unit_label": "FIR records", "method": method,
        "source_queries": source_queries,
    }


def build_crime_type_analytics(app):
    case_query = "SELECT CrimeMinorHeadID, COUNT(CaseMasterID) AS CaseCount FROM CaseMaster GROUP BY CrimeMinorHeadID"
    subhead_query = "SELECT CrimeSubHeadID, CrimeHeadName FROM CrimeSubHead LIMIT 300"
    grouped_rows = []
    try:
        grouped_rows = execute_zcql(app, case_query)
    except Exception:
        grouped_rows = []
    subhead_rows = execute_zcql(app, subhead_query)
    lookup = {str(r.get("CrimeSubHeadID")): _norm_label(r.get("CrimeHeadName"), "Unknown crime") for r in subhead_rows if r.get("CrimeSubHeadID") is not None}

    aggregated = {}
    if grouped_rows:
        for row in grouped_rows:
            mid = row.get("CrimeMinorHeadID")
            label = _norm_label(lookup.get(str(mid)), f"Crime type {mid}" if mid is not None else "Unknown crime")
            aggregated[label] = aggregated.get(label, 0) + _aggregate_count(row)

    if not grouped_rows or sum(aggregated.values()) == 0:
        raw_query = "SELECT CaseMasterID, CrimeMinorHeadID FROM CaseMaster LIMIT 300"
        raw_rows = execute_zcql(app, raw_query)
        aggregated = _python_group(raw_rows, "CrimeMinorHeadID", lookup, "Crime type")
        source_queries = [raw_query, subhead_query]
        method = "Deterministic retrieval followed by application-side crime-type aggregation; aggregate ZCQL was unavailable or returned unusable counts."
    else:
        source_queries = [case_query, subhead_query]
        method = "Deterministic server-side aggregation from CaseMaster, CrimeSubHead values."

    ranked = _merge_aggregate_labels(aggregated.items())
    total = sum(x[1] for x in ranked)
    return {
        "query_type": "analytics", "chart_type": "bar", "title": "FIRs by Crime Type",
        "labels": [x[0] for x in ranked], "values": [x[1] for x in ranked], "total": total,
        "records": [{"CrimeType": x[0], "CaseCount": x[1]} for x in ranked],
        "method": method, "source_queries": source_queries,
    }


def build_station_analytics(app):
    case_query = "SELECT PoliceStationID, COUNT(CaseMasterID) AS CaseCount FROM CaseMaster GROUP BY PoliceStationID"
    unit_query = "SELECT UnitID, UnitName FROM Unit LIMIT 300"
    grouped_rows = []
    try:
        grouped_rows = execute_zcql(app, case_query)
    except Exception:
        grouped_rows = []
    unit_rows = execute_zcql(app, unit_query)
    lookup = {str(r.get("UnitID")): _norm_label(r.get("UnitName"), f"Station {r.get('UnitID')}") for r in unit_rows if r.get("UnitID") is not None}

    aggregated = {}
    if grouped_rows:
        for row in grouped_rows:
            sid = row.get("PoliceStationID")
            label = _norm_label(lookup.get(str(sid)), f"Station {sid}" if sid is not None else "Unknown station")
            aggregated[label] = aggregated.get(label, 0) + _aggregate_count(row)

    if not grouped_rows or sum(aggregated.values()) == 0:
        raw_query = "SELECT CaseMasterID, PoliceStationID FROM CaseMaster LIMIT 300"
        raw_rows = execute_zcql(app, raw_query)
        aggregated = _python_group(raw_rows, "PoliceStationID", lookup, "Station")
        source_queries = [raw_query, unit_query]
        method = "Deterministic retrieval followed by application-side police-station aggregation; aggregate ZCQL was unavailable or returned unusable counts."
    else:
        source_queries = [case_query, unit_query]
        method = "Deterministic server-side aggregation from CaseMaster and Unit values."

    ranked = _merge_aggregate_labels(aggregated.items())
    total = sum(x[1] for x in ranked)
    return {
        "query_type": "analytics", "chart_type": "bar", "title": "FIRs by Police Station",
        "labels": [x[0] for x in ranked], "values": [x[1] for x in ranked], "total": total,
        "records": [{"StationName": x[0], "CaseCount": x[1]} for x in ranked],
        "method": method, "source_queries": source_queries,
    }

def build_monthly_trend_analytics(app):
    """
    Deterministic monthly FIR trend aggregation.

    Source of truth:
        CaseMaster.CrimeRegisteredDate

    Dates are grouped as YYYY-MM so the result is stable,
    sortable, and directly usable by a line chart.
    """

    case_query = """
        SELECT CaseMasterID, CrimeRegisteredDate
        FROM CaseMaster
        LIMIT 300
    """.strip()

    case_rows = execute_zcql(app, case_query)

    counts = {}

    for row in case_rows:
        raw_date = row.get("CrimeRegisteredDate")

        if raw_date is None:
            continue

        text = str(raw_date).strip()

        # Catalyst may return a date/datetime string.
        # The first seven characters are YYYY-MM for ISO-like dates.
        if len(text) >= 7 and re.match(r"^\d{4}-\d{2}", text):
            month_key = text[:7]
        else:
            continue

        counts[month_key] = counts.get(month_key, 0) + 1

    ranked = sorted(counts.items(), key=lambda item: item[0])

    labels = [item[0] for item in ranked]
    values = [item[1] for item in ranked]

    analytics_rows = [
        {
            "Month": label,
            "CaseCount": value
        }
        for label, value in ranked
    ]

    return {
        "query_type": "analytics",
        "chart_type": "line",
        "title": "Monthly FIR Trend",
        "labels": labels,
        "values": values,
        "total": sum(values),
        "records": analytics_rows,
        "source_queries": [case_query]
    }


def build_hotspot_analytics(app, location_filter=None):
    """Deterministic spatial hotspot aggregation with optional geographic scope."""
    case_query = """
        SELECT CaseMasterID, CrimeNo, CaseNO, CrimeRegisteredDate,
               latitude, longitude, PoliceStationID, CrimeMinorHeadID
        FROM CaseMaster
        LIMIT 300
    """.strip()
    unit_query = "SELECT UnitID, UnitName, DistrictID FROM Unit LIMIT 300"
    crime_query = "SELECT CrimeSubHeadID, CrimeHeadName FROM CrimeSubHead LIMIT 300"
    district_query = "SELECT DistrictID, DistrictName FROM District LIMIT 300"

    case_rows = execute_zcql(app, case_query)
    unit_rows = execute_zcql(app, unit_query)
    crime_rows = execute_zcql(app, crime_query)
    try:
        district_rows = execute_zcql(app, district_query)
    except Exception:
        district_rows = []

    station_lookup = {
        str(r.get("UnitID")): str(r.get("UnitName") or "")
        for r in unit_rows if r.get("UnitID") is not None
    }
    unit_district_lookup = {
        str(r.get("UnitID")): str(r.get("DistrictID"))
        for r in unit_rows if r.get("UnitID") is not None
    }
    district_lookup = {
        str(r.get("DistrictID")): str(r.get("DistrictName") or "")
        for r in district_rows if r.get("DistrictID") is not None
    }
    crime_lookup = {
        str(r.get("CrimeSubHeadID")): str(r.get("CrimeHeadName") or "")
        for r in crime_rows if r.get("CrimeSubHeadID") is not None
    }

    def matches_location(row):
        if not location_filter:
            return True
        wanted = str(location_filter).strip().lower()
        aliases = {"bengaluru": ("bengaluru", "bangalore")}
        tokens = aliases.get(wanted, (wanted,))
        sid = row.get("PoliceStationID")
        station = station_lookup.get(str(sid), "") if sid is not None else ""
        did = unit_district_lookup.get(str(sid), "") if sid is not None else ""
        district = district_lookup.get(str(did), "")
        haystack = f"{station} {district}".lower()
        return any(token in haystack for token in tokens)

    cells = {}
    filtered_case_count = 0

    for row in case_rows:
        if not matches_location(row):
            continue
        try:
            lat = float(row.get("latitude")); lon = float(row.get("longitude"))
        except (TypeError, ValueError):
            continue
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            continue

        filtered_case_count += 1
        key = (round(lat, 2), round(lon, 2))
        cell = cells.setdefault(key, {
            "Latitude": key[0], "Longitude": key[1], "CaseCount": 0,
            "FIRs": [], "Stations": set(), "CrimeTypes": set()
        })
        cell["CaseCount"] += 1
        fir = row.get("CaseNO") or row.get("CrimeNo") or row.get("CaseMasterID")
        if fir is not None and str(fir) not in cell["FIRs"]:
            cell["FIRs"].append(str(fir))
        crime_id = row.get("CrimeMinorHeadID")
        if crime_id is not None and crime_lookup.get(str(crime_id)):
            cell["CrimeTypes"].add(crime_lookup[str(crime_id)])
        sid = row.get("PoliceStationID")
        if sid is not None:
            cell["Stations"].add(station_lookup.get(str(sid), f"Station {sid}"))

    hotspot_rows = [{
        "Latitude": c["Latitude"], "Longitude": c["Longitude"],
        "CaseCount": c["CaseCount"], "FIRs": c["FIRs"],
        "Stations": sorted(c["Stations"]), "CrimeTypes": sorted(c["CrimeTypes"]),
        "PrimaryStation": sorted(c["Stations"])[0] if c["Stations"] else "Unknown station"
    } for c in cells.values() if c["CaseCount"] > 0]
    hotspot_rows.sort(key=lambda r: (-r["CaseCount"], r["Latitude"], r["Longitude"]))

    return {
        "query_type": "analytics", "chart_type": "map",
        "title": "Bengaluru Crime Hotspot Cells" if location_filter else "Crime Hotspot Cells",
        "labels": [f"{r['Latitude']:.2f}, {r['Longitude']:.2f}" for r in hotspot_rows],
        "values": [r["CaseCount"] for r in hotspot_rows],
        "total": filtered_case_count,
        "spatial_cell_count": len(hotspot_rows),
        "records": hotspot_rows,
        "grid_size_degrees": 0.01,
        "source_queries": [case_query, unit_query, crime_query, district_query],
        "method": (
            "Deterministic spatial aggregation of Bengaluru-linked CaseMaster records into approximate 0.01-degree cells, enriched with station and crime-type labels."
            if location_filter else
            "Deterministic aggregation of CaseMaster coordinates into approximate 0.01-degree cells, enriched with station and crime-type labels from KSP master tables."
        )
    }


def build_contextual_hotspot_analytics(app, session_state):
    """Return hotspot cells limited to the current investigation context.

    Reuses the existing deterministic hotspot engine rather than introducing
    another spatial implementation. The current FIR and active case IDs are
    resolved from server-side case data, then only cells containing those
    cases are returned.
    """
    state = session_state or {}
    active_ids = {str(x) for x in (state.get("active_case_ids") or []) if x is not None}
    active_fir = str(state.get("active_fir") or "").strip()

    # Resolve the current FIR to its CaseMasterID without trusting client data
    # for authorization. Client context is only a conversational hint.
    case_index = {}
    try:
        case_index = load_case_index(app)
    except Exception as exc:
        print("CONTEXTUAL HOTSPOT CASE INDEX FAILED:", exc)

    if active_fir:
        for cid, row in case_index.items():
            labels = {
                str(row.get("CaseNO") or "").strip(),
                str(row.get("CrimeNo") or "").strip(),
            }
            if active_fir in labels:
                active_ids.add(str(cid))
                break

    if not active_ids:
        raise ValueError("No active investigation case context is available for hotspot analysis.")

    target_labels = set()
    for cid in active_ids:
        row = case_index.get(str(cid), {})
        for value in (row.get("CaseNO"), row.get("CrimeNo")):
            if value is not None and str(value).strip():
                target_labels.add(str(value).strip())

    if active_fir:
        target_labels.add(active_fir)

    base = build_hotspot_analytics(app)
    filtered = []
    for row in base.get("records") or []:
        firs = {str(value).strip() for value in (row.get("FIRs") or []) if value is not None}
        if firs & target_labels:
            filtered.append(dict(row))

    total = sum(int(row.get("CaseCount") or 0) for row in filtered)
    return {
        **base,
        "title": "Investigation Hotspot Cells",
        "labels": [f"{row['Latitude']:.2f}, {row['Longitude']:.2f}" for row in filtered],
        "values": [int(row.get("CaseCount") or 0) for row in filtered],
        "total": total,
        "spatial_cell_count": len(filtered),
        "records": filtered,
        "contextual": True,
        "context_case_ids": sorted(active_ids),
        "context_firs": sorted(target_labels),
        "method": (
            "Deterministic hotspot analysis limited to the current investigation "
            "case and its active conversational case context, using the same "
            "approximate 0.01-degree spatial cells as the global hotspot engine."
        ),
    }


def build_early_warning_analytics(app):
    """
    Evidence-backed proactive signal engine.

    Signals are deterministic and explainable. They combine:
      1) repeat accused recurrence,
      2) repeated spatial concentration,
      3) crime-type concentration in the available period,
      4) cross-dimension signals where a repeat accused and a hotspot
         overlap in the same case history.

    This is an early-warning signal layer, not a predictive risk model.
    """

    case_query = """
        SELECT CaseMasterID, CrimeNo, CrimeMinorHeadID,
               CrimeRegisteredDate, latitude, longitude,
               PoliceStationID
        FROM CaseMaster
        LIMIT 300
    """.strip()

    subhead_query = """
        SELECT CrimeSubHeadID, CrimeHeadName
        FROM CrimeSubHead
        LIMIT 300
    """.strip()

    accused_query = """
        SELECT AccusedMasterID, CaseMasterID, AccusedName, PersonID
        FROM Accused
        LIMIT 300
    """.strip()

    unit_query = """
        SELECT UnitID, UnitName
        FROM Unit
        LIMIT 300
    """.strip()

    case_rows = execute_zcql(app, case_query)
    subhead_rows = execute_zcql(app, subhead_query)
    accused_rows = execute_zcql(app, accused_query)
    unit_rows = execute_zcql(app, unit_query)

    crime_lookup = {
        str(row.get("CrimeSubHeadID")): (
            row.get("CrimeHeadName") or "Unknown Crime"
        )
        for row in subhead_rows
        if row.get("CrimeSubHeadID") is not None
    }

    station_lookup = {
        str(row.get("UnitID")): (
            row.get("UnitName") or f"Station {row.get('UnitID')}"
        )
        for row in unit_rows
        if row.get("UnitID") is not None
    }

    # Index cases so every signal can carry concrete evidence.
    case_index = {}
    for row in case_rows:
        case_id = row.get("CaseMasterID")
        if case_id is not None:
            case_index[str(case_id)] = row

    # --------------------------------------------------------
    # Common case metadata.
    # --------------------------------------------------------

    valid_case_rows = []
    months = set()

    for row in case_rows:
        raw_date = row.get("CrimeRegisteredDate")
        if raw_date is None:
            continue

        text = str(raw_date).strip()
        if len(text) >= 7 and re.match(r"^\d{4}-\d{2}", text):
            month = text[:7]
            months.add(month)
            valid_case_rows.append((row, month))

    sorted_months = sorted(months)
    latest_month = sorted_months[-1] if sorted_months else None
    previous_month = sorted_months[-2] if len(sorted_months) >= 2 else None

    signals = []

    # --------------------------------------------------------
    # Signal 1: repeat accused recurrence.
    # --------------------------------------------------------

    person_cases = {}

    for row in accused_rows:
        case_id = row.get("CaseMasterID")
        if case_id is None:
            continue

        person_id = row.get("PersonID")
        name = (row.get("AccusedName") or "Unknown").strip()
        identity = (
            f"id:{person_id}"
            if person_id is not None
            else f"name:{name.lower()}"
        )

        record = person_cases.setdefault(
            identity,
            {"name": name, "cases": set()}
        )
        record["cases"].add(str(case_id))

    for record in person_cases.values():
        case_ids = sorted(record["cases"])
        case_count = len(case_ids)

        if case_count < 2:
            continue

        evidence_cases = []
        stations = set()
        crime_types = set()
        hotspot_keys = set()

        for cid in case_ids:
            case = case_index.get(cid, {})
            fir = case.get("CaseNO") or case.get("CrimeNo") or f"Case {cid}"
            crime_type = crime_lookup.get(
                str(case.get("CrimeMinorHeadID")),
                "Unknown Crime"
            )
            station = station_lookup.get(
                str(case.get("PoliceStationID")),
                "Unknown station"
            )

            evidence_cases.append(fir)
            stations.add(station)
            crime_types.add(crime_type)

            try:
                lat = round(float(case.get("latitude")), 2)
                lon = round(float(case.get("longitude")), 2)
                hotspot_keys.add((lat, lon))
            except (TypeError, ValueError):
                pass

        severity = "HIGH" if case_count >= 3 else "MEDIUM"

        signals.append({
            "type": "repeat_accused",
            "severity": severity,
            "title": f"Repeat offender recurrence: {record['name']}",
            "evidence": (
                f"{record['name']} appears in {case_count} FIRs "
                f"across {len(stations)} police station(s), covering "
                f"{len(crime_types)} crime type(s)."
            ),
            "metric": case_count,
            "dimension": record["name"],
            "cases": evidence_cases,
            "stations": sorted(stations),
            "crime_types": sorted(crime_types),
        })

        # ----------------------------------------------------
        # Fused signal: repeat accused + recurring hotspot.
        # ----------------------------------------------------

        if hotspot_keys:
            hotspot_case_counts = {}
            for cid in case_ids:
                case = case_index.get(cid, {})
                try:
                    key = (
                        round(float(case.get("latitude")), 2),
                        round(float(case.get("longitude")), 2)
                    )
                except (TypeError, ValueError):
                    continue
                hotspot_case_counts.setdefault(key, []).append(cid)

            for (lat, lon), hotspot_cases in hotspot_case_counts.items():
                if len(hotspot_cases) >= 2:
                    firs = [
                        case_index.get(cid, {}).get("CaseNO")
                        or case_index.get(cid, {}).get("CrimeNo")
                        or f"Case {cid}"
                        for cid in hotspot_cases
                    ]
                    signals.append({
                        "type": "repeat_offender_hotspot",
                        "severity": "HIGH",
                        "title": (
                            f"Repeat offender + hotspot overlap: {record['name']}"
                        ),
                        "evidence": (
                            f"{record['name']} appears in {len(hotspot_cases)} FIRs "
                            f"within the {lat:.2f}, {lon:.2f} spatial cell."
                        ),
                        "metric": len(hotspot_cases),
                        "dimension": f"{record['name']} @ {lat:.2f}, {lon:.2f}",
                        "latitude": lat,
                        "longitude": lon,
                        "cases": firs,
                    })

    # --------------------------------------------------------
    # Signal 2: repeated spatial concentration.
    # --------------------------------------------------------

    cells = {}

    for row, _month in valid_case_rows:
        try:
            lat = float(row.get("latitude"))
            lon = float(row.get("longitude"))
        except (TypeError, ValueError):
            continue

        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            continue

        key = (round(lat, 2), round(lon, 2))
        cell = cells.setdefault(
            key,
            {
                "case_ids": [],
                "stations": set(),
                "crime_types": set()
            }
        )
        cell["case_ids"].append(str(row.get("CaseMasterID")))
        cell["stations"].add(
            station_lookup.get(
                str(row.get("PoliceStationID")),
                "Unknown station"
            )
        )
        cell["crime_types"].add(
            crime_lookup.get(
                str(row.get("CrimeMinorHeadID")),
                "Unknown Crime"
            )
        )

    for (lat, lon), cell in cells.items():
        count = len(cell["case_ids"])
        if count < 2:
            continue

        severity = "HIGH" if count >= 3 else "MEDIUM"
        firs = [
            case_index.get(cid, {}).get("CaseNO")
            or case_index.get(cid, {}).get("CrimeNo")
            or f"Case {cid}"
            for cid in cell["case_ids"]
        ]

        signals.append({
            "type": "spatial_concentration",
            "severity": severity,
            "title": f"Repeated spatial concentration: {lat:.2f}, {lon:.2f}",
            "evidence": (
                f"{count} FIRs fall within the {lat:.2f}, {lon:.2f} "
                f"cell across {len(cell['stations'])} station(s)."
            ),
            "metric": count,
            "dimension": f"{lat:.2f}, {lon:.2f}",
            "latitude": lat,
            "longitude": lon,
            "cases": firs,
            "stations": sorted(cell["stations"]),
            "crime_types": sorted(cell["crime_types"]),
        })

    # --------------------------------------------------------
    # Signal 3: crime-type concentration.
    # --------------------------------------------------------

    crime_case_map = {}
    monthly_counts = {}

    for row, month in valid_case_rows:
        crime_type = crime_lookup.get(
            str(row.get("CrimeMinorHeadID")),
            "Unknown Crime"
        )
        cid = str(row.get("CaseMasterID"))
        crime_case_map.setdefault(crime_type, []).append(cid)
        monthly_counts.setdefault(crime_type, {}).setdefault(month, 0)
        monthly_counts[crime_type][month] += 1

    total_valid_cases = len(valid_case_rows)

    for crime_type, case_ids in crime_case_map.items():
        count = len(case_ids)
        if count < 2:
            continue

        month_counts = monthly_counts.get(crime_type, {})
        recent_count = month_counts.get(latest_month, 0) if latest_month else 0
        previous_count = month_counts.get(previous_month, 0) if previous_month else 0

        # Stronger when the type is both concentrated and present in the latest month.
        if recent_count > 0 and recent_count >= previous_count:
            severity = "MEDIUM"
            reason = (
                f"{count} FIRs overall; {recent_count} are in the latest "
                f"available month ({latest_month})."
            )
        elif total_valid_cases and count / total_valid_cases >= 0.25:
            severity = "MEDIUM"
            reason = (
                f"{count} of {total_valid_cases} FIRs ({count / total_valid_cases:.0%}) "
                "belong to this crime type."
            )
        else:
            continue

        firs = [
            case_index.get(cid, {}).get("CaseNO")
            or case_index.get(cid, {}).get("CrimeNo")
            or f"Case {cid}"
            for cid in case_ids
        ]

        signals.append({
            "type": "crime_type_concentration",
            "severity": severity,
            "title": f"Crime pattern concentration: {crime_type}",
            "evidence": reason,
            "metric": count,
            "dimension": crime_type,
            "cases": firs,
            "latest_month": latest_month,
            "previous_month": previous_month,
        })

    # --------------------------------------------------------
    # Ranking + de-duplication.
    # --------------------------------------------------------

    unique = {}
    for signal in signals:
        key = (
            signal.get("type"),
            signal.get("dimension"),
        )
        previous = unique.get(key)
        if previous is None or signal.get("metric", 0) > previous.get("metric", 0):
            unique[key] = signal

    signals = list(unique.values())

    # --------------------------------------------------------
    # Evidence + severity scoring.
    # --------------------------------------------------------
    # This is a prioritization score for investigation triage,
    # not a predictive offender/crime risk score.
    for index, signal in enumerate(signals, start=1):

        signal_type = signal.get("type")
        metric = int(signal.get("metric", 0) or 0)

        if signal_type == "repeat_offender_hotspot":
            score = min(100, 80 + max(0, metric - 2) * 8)
            severity = "HIGH"
            lead = "Review the linked FIRs for recurring activity in the same area."

        elif signal_type == "repeat_accused":
            if metric >= 4:
                score = 85
                severity = "HIGH"
            elif metric == 3:
                score = 72
                severity = "HIGH"
            else:
                score = 58
                severity = "MEDIUM"
            lead = "Review the person's case history and cross-case connections."

        elif signal_type == "spatial_concentration":
            score = min(90, 50 + metric * 15)
            severity = "HIGH" if metric >= 3 else "MEDIUM"
            lead = "Review the FIRs in this spatial cell for common patterns or repeat locations."

        elif signal_type == "crime_type_concentration":
            recent = int(signal.get("recent_count", 0) or 0)
            previous = int(signal.get("previous_count", 0) or 0)
            if recent > previous and recent > 0:
                score = min(90, 65 + recent * 8)
            else:
                score = min(75, 45 + metric * 7)
            severity = "HIGH" if recent > previous and recent >= 2 else "MEDIUM"
            lead = "Review recent FIRs for recurrence, location overlap, or common modus operandi."

        else:
            score = min(70, 40 + metric * 8)
            severity = signal.get("severity", "MEDIUM")
            lead = "Review the evidence behind this signal."

        signal["severity"] = severity
        signal["priority_score"] = score
        signal["signal_id"] = f"EW-{index:02d}"
        signal["evidence_cases"] = list(signal.get("cases", []))
        signal["recommended_lead"] = lead

        if signal_type == "repeat_offender_hotspot":
            signal["evidence_summary"] = (
                f"{signal.get('evidence', '')} "
                f"Related FIRs: {', '.join(signal.get('cases', []))}."
            )
        else:
            signal["evidence_summary"] = signal.get("evidence", "")

    severity_rank = {
        "HIGH": 0,
        "MEDIUM": 1,
        "LOW": 2,
    }

    signals.sort(
        key=lambda item: (
            -item.get("priority_score", 0),
            severity_rank.get(item.get("severity"), 9),
            -item.get("metric", 0),
            item.get("title", "").lower()
        )
    )

    # Keep the highest-value signals for the investigator view.
    signals = signals[:8]

    # Re-number after final ranking.
    for index, signal in enumerate(signals, start=1):
        signal["signal_id"] = f"EW-{index:02d}"

    headline = (
        f"{len(signals)} evidence-backed proactive signal(s) identified "
        f"from {len(case_rows)} available FIR record(s)."
        if signals
        else
        "No strong proactive signal was identified from the available FIR records."
    )

    return {
        "query_type": "early_warning",
        "chart_type": "signals",
        "title": "Proactive Crime Signals",
        "headline": headline,
        "latest_month": latest_month,
        "previous_month": previous_month,
        "signals": signals,
        "labels": [signal["title"] for signal in signals],
        "values": [signal["metric"] for signal in signals],
        "total": len(case_rows),
        "records": signals,
        "method": (
            "Deterministic evidence fusion over repeat-offender recurrence, "
            "spatial concentration, crime-type concentration, and cross-dimension "
            "overlap. This is an explainable early-warning signal layer, not a "
            "predictive risk score."
        ),
        "source_queries": [
            case_query,
            subhead_query,
            accused_query,
            unit_query,
        ],
    }



def classify_analytics_question(text: str) -> str | None:
    q = re.sub(r"\s+", " ", text.lower().strip())

    # Proactive / early-warning intelligence should bypass Gemini.
    early_warning_phrases = [
        "emerging crime patterns",
        "emerging crime pattern",
        "what crime patterns should investigators watch",
        "what patterns should investigators watch",
        "what should investigators watch",
        "early warning",
        "early-warning",
        "crime signals",
        "emerging crime signals",
        "proactive crime intelligence",
        "preventive crime intelligence",
        "which crime patterns are emerging",
        "which crime patterns are increasing",
        "what crimes are increasing",
        "which crimes are increasing",
        "increasing crime patterns",
        "repeat crime signals",
        "repeat offender warning",
    ]

    if any(phrase in q for phrase in early_warning_phrases):
        return "early_warning"

    status_phrases = [
        "case status",
        "case statuses",
        "status distribution",
        "firs by status",
        "cases by status",
        "how many cases are under investigation",
        "how many firs are under investigation",
        "how many cases are registered",
        "how many cases are in trial",
        "how many cases are chargesheeted",
        "investigation workload",
        "case lifecycle",
    ]

    if any(phrase in q for phrase in status_phrases):
        return "case_status"

    # Station analytics first because phrases such as
    # "which police stations have the most FIRs" should never
    # fall through to Gemini.
    station_phrases = [
        "which police stations have the most firs",
        "which police station has the most firs",
        "police stations have the most firs",
        "police station has the most firs",
        "stations with the most firs",
        "police stations with most firs",
        "firs by police station",
        "firs by station",
        "cases by police station",
        "cases by station",
        "station-wise firs",
        "station wise firs",
        "station wise crime",
        "crime by police station",
        "crime by station",
        "crime distribution by police station",
        "crime distribution by station",
        "distribution by police station",
        "distribution by station",
        "show crime distribution by police station",
        "show crime distribution by station",
        "most active police stations",
        "busiest police stations",
    ]

    if any(phrase in q for phrase in station_phrases):
        return "station"

    peak_month_phrases = [
        "which month had the most firs",
        "which month had the most fir",
        "which month has the most firs",
        "which month has the most fir",
        "month with the most firs",
        "month with the most fir",
        "month had the highest fir activity",
        "month has the highest fir activity",
        "which month had the highest number of firs",
        "which month had the highest number of cases",
        "which month had the most cases",
        "highest fir month",
        "most active month",
    ]

    if any(phrase in q for phrase in peak_month_phrases):
        return "monthly_peak"

    trend_phrases = [
        "fir trends by month",
        "fir trend by month",
        "monthly fir trends",
        "monthly crime trends",
        "crime trend by month",
        "crime trends by month",
        "crime trend over time",
        "crime trends over time",
        "monthly crime",
        "crime by month",
        "cases by month",
        "firs by month",
        "monthly distribution",
        "trend analysis",
        "show trends",
        "show trend",
        "month by month",
        "month-by-month",
        "how has crime changed month by month",
        "how has crime changed over the months",
        "how did crime change month by month",
        "crime change month by month",
        "changes in crime by month",
    ]

    if any(phrase in q for phrase in trend_phrases):
        return "monthly_trend"

    hotspot_phrases = [
        "crime hotspots",
        "crime hotspot",
        "where are the crime hotspots",
        "where are crimes concentrated",
        "where are firs concentrated",
        "where are cases concentrated",
        "highest crime concentration",
        "high crime concentration",
        "crime concentration by location",
        "crime concentration by area",
        "hotspot analysis",
        "spatial hotspots",
        "crime locations",
        "hotspot map",
        "show hotspot map",
        "show me hotspots",
        "show hotspots",
        "show me the hotspot",
        "show the hotspot",
        "show me hotspot",
        "where is the hotspot",
        "crime hotspot map",
        "where are hotspots",
        "hotspots with the highest fir activity",
        "highest fir activity hotspots",
        "highest fir activity",
        "which hotspots have the most firs",
        "which hotspots have the highest number of firs",
    ]

    if any(phrase in q for phrase in hotspot_phrases):
        if "bengaluru" in q or "bangalore" in q:
            return "hotspot_bengaluru"
        return "hotspot"

    # Cross-analysis patterns must be routed before generic crime-type / station analytics.
    cross_patterns = [
        ("crime_type_across_stations", [
            "which crime types are common across police stations",
            "which crime types are common across stations",
            "crime types common across police stations",
            "common crime types across police stations",
            "common crime types across stations",
            "crime types across police stations",
        ]),
        ("station_crime_patterns", [
            "which stations have repeated crime patterns",
            "which police stations have repeated crime patterns",
            "stations with repeated crime patterns",
            "repeated crime patterns by station",
            "recurring crime patterns at stations",
        ]),
        ("person_crime_station", [
            "are there people linked to the same crime type across different stations",
            "people linked to the same crime type across different stations",
            "people linked to same crime type across stations",
            "accused linked to the same crime type across different stations",
            "same crime type across different stations",
        ]),
        ("crime_location_recurrence", [
            "which crime type and location combinations recur",
            "which crime type and location combinations repeat",
            "recurring crime type and location combinations",
            "crime type location combinations recur",
            "recurring crime and location patterns",
        ]),
    ]
    for cross_type, phrases in cross_patterns:
        if any(phrase in q for phrase in phrases):
            return cross_type

    process_patterns = [
        ("missing_chargesheet", [
            "which cases have no chargesheet yet", "which cases have no chargesheet",
            "which cases have no charge sheet", "which cases have no charge-sheet",
            "which cases are missing a chargesheet", "which cases are missing a charge sheet",
            "which cases are missing a charge-sheet", "show cases without a chargesheet",
            "show cases without a charge sheet", "show firs without chargesheet",
            "show firs without charge sheet", "cases without chargesheet",
            "cases without a charge sheet", "no chargesheet yet", "no charge sheet yet",
            "missing chargesheet", "missing charge sheet"
        ]),
        ("missing_arrest", [
            "which cases have no arrest record", "which cases have no arrest records",
            "which cases are missing an arrest record", "show cases without arrest",
            "cases without arrest record", "no arrest record", "missing arrest record"
        ]),
        ("missing_legal", [
            "which firs are missing legal section records", "which cases are missing legal section records",
            "which cases have no legal sections", "which cases have no act or section records",
            "show cases without legal sections", "cases without legal sections", "missing legal sections"
        ]),
        ("investigation_gaps", [
            "which cases have investigation gaps", "show investigation gaps",
            "what investigation records are missing", "which cases are missing investigation records",
            "investigation gaps", "missing investigation records"
        ]),
        ("chargesheet_cases", ["which cases have a chargesheet", "which cases have chargesheets", "show cases with chargesheet", "show firs with chargesheet", "cases with chargesheet records"]),
        ("arrest_cases", ["which cases have arrest records", "which cases have arrest or surrender records", "show cases with arrest", "show cases with surrender", "which cases have arrest/surrender"]),
        ("legal_cases", ["which cases have legal sections", "which cases have act and section records", "which cases have act/section", "show cases with legal sections"]),
        ("process_overview", ["investigation process records", "how many cases have chargesheets", "how many cases have arrest records", "how many cases have legal sections", "investigation process status"]),
    ]
    for process_type, phrases in process_patterns:
        if any(phrase in q for phrase in phrases):
            return process_type


    crime_type_phrases = [
        "most common crime",
        "most common crimes",
        "common crime types",
        "crime types",
        "crime distribution",
        "crime breakdown",
        "crime by type",
        "number of crimes",
        "how many crimes",
        "crime count",
        "crime counts",
        "crime statistics",
        "crime stats",
        "crime analysis",
        "analyse crime",
        "analyze crime",
        "crime categories",
        "most frequent crime",
        "top crimes",
    ]

    if any(phrase in q for phrase in crime_type_phrases):
        return "crime_type"

    return None


def classify_sociological_question(text: str) -> str | None:
    q = re.sub(r"\s+", " ", text.lower().strip())

    # Cross-dimensional sociological questions must be detected BEFORE
    # the simpler age-only classifier. General phrases such as "crime types"
    # also exist in the generic analytics router, so we use a semantic
    # conjunction check rather than relying only on exact phrase matches.
    cross_tab_phrases = [
        "age groups across crime types",
        "age groups by crime type",
        "age group by crime type",
        "crime types across age groups",
        "crime type by age group",
        "crime type across age groups",
        "accused age and crime type",
        "age distribution by crime type",
        "crime distribution by age group",
    ]

    if any(phrase in q for phrase in cross_tab_phrases):
        return "accused_age_crime_type"

    # Handle natural-language variants such as:
    # "What crime types are most common across age groups?"
    # where other words occur between the key concepts.
    has_age_group = any(
        phrase in q
        for phrase in ["age group", "age groups", "age band", "age bands"]
    )
    has_crime_type = any(
        phrase in q
        for phrase in ["crime type", "crime types", "crime category", "crime categories"]
    )

    if has_age_group and has_crime_type:
        return "accused_age_crime_type"

    age_phrases = [
        "age distribution of accused",
        "age distribution among accused",
        "accused age distribution",
        "age groups of accused",
        "accused by age",
        "age of accused persons",
        "what age groups are most common among accused",
        "which age groups appear most often among accused",
        "demographic profile of accused",
    ]

    if any(phrase in q for phrase in age_phrases):
        return "accused_age"

    gender_phrases = [
        "gender distribution of accused",
        "gender distribution among accused",
        "accused gender distribution",
        "accused by gender",
        "gender of accused persons",
        "demographics by gender",
    ]

    if any(phrase in q for phrase in gender_phrases):
        return "accused_gender"

    return None


def build_accused_age_analytics(app):
    query = """
        SELECT AccusedMasterID, CaseMasterID, AccusedName, AgeYear, GenderID
        FROM Accused
        LIMIT 300
    """.strip()

    rows = execute_zcql(app, query)

    bands = {
        "18–24": 0,
        "25–34": 0,
        "35–44": 0,
        "45–54": 0,
        "55+": 0,
        "Unknown": 0,
    }

    for row in rows:
        raw_age = row.get("AgeYear")
        try:
            age = int(float(raw_age))
        except (TypeError, ValueError):
            bands["Unknown"] += 1
            continue

        if age < 18:
            bands["Unknown"] += 1
        elif age <= 24:
            bands["18–24"] += 1
        elif age <= 34:
            bands["25–34"] += 1
        elif age <= 44:
            bands["35–44"] += 1
        elif age <= 54:
            bands["45–54"] += 1
        else:
            bands["55+"] += 1

    ranked = [(label, count) for label, count in bands.items() if count > 0]
    order = {label: idx for idx, label in enumerate(bands.keys())}
    ranked.sort(key=lambda item: order[item[0]])

    return {
        "query_type": "analytics",
        "analytics_dimension": "sociological_age",
        "chart_type": "bar",
        "title": "Accused Age Distribution",
        "unit_label": "accused records",
        "labels": [label for label, _ in ranked],
        "values": [count for _, count in ranked],
        "total": len(rows),
        "records": [
            {"AgeGroup": label, "AccusedCount": count}
            for label, count in ranked
        ],
        "method": (
            "Deterministic grouping of Accused.AgeYear into broad age bands. "
            "This describes the available accused records; it does not imply causation or risk."
        ),
        "source_queries": [query],
    }


def build_accused_gender_analytics(app):
    query = """
        SELECT AccusedMasterID, CaseMasterID, AccusedName, GenderID
        FROM Accused
        LIMIT 300
    """.strip()

    rows = execute_zcql(app, query)

    counts = {}
    for row in rows:
        gender_id = row.get("GenderID")
        label = f"Gender {gender_id}" if gender_id is not None else "Unknown"
        counts[label] = counts.get(label, 0) + 1

    ranked = sorted(
        counts.items(),
        key=lambda item: (-item[1], item[0].lower())
    )

    return {
        "query_type": "analytics",
        "analytics_dimension": "sociological_gender",
        "chart_type": "bar",
        "title": "Accused Gender Distribution",
        "unit_label": "accused records",
        "labels": [label for label, _ in ranked],
        "values": [count for _, count in ranked],
        "total": len(rows),
        "records": [
            {"Gender": label, "AccusedCount": count}
            for label, count in ranked
        ],
        "method": (
            "Deterministic aggregation of Accused.GenderID. "
            "The available KSP schema exposes GenderID but no gender-name reference table is present in the current configured schema, "
            "so the stored gender identifiers are shown without interpreting their meaning."
        ),
        "source_queries": [query],
    }


def build_accused_age_crime_type_analytics(app):
    accused_query = """
        SELECT AccusedMasterID, CaseMasterID, AgeYear
        FROM Accused
        LIMIT 300
    """.strip()

    case_query = """
        SELECT CaseMasterID, CrimeMinorHeadID
        FROM CaseMaster
        LIMIT 300
    """.strip()

    subhead_query = """
        SELECT CrimeSubHeadID, CrimeHeadName
        FROM CrimeSubHead
        LIMIT 300
    """.strip()

    accused_rows = execute_zcql(app, accused_query)
    case_rows = execute_zcql(app, case_query)
    subhead_rows = execute_zcql(app, subhead_query)

    case_type = {
        str(row.get("CaseMasterID")): (
            row.get("CrimeMinorHeadID")
        )
        for row in case_rows
        if row.get("CaseMasterID") is not None
    }

    type_lookup = {
        str(row.get("CrimeSubHeadID")): (
            row.get("CrimeHeadName") or "Unknown"
        )
        for row in subhead_rows
        if row.get("CrimeSubHeadID") is not None
    }

    def age_band(raw_age):
        try:
            age = int(float(raw_age))
        except (TypeError, ValueError):
            return "Unknown"
        if age < 18:
            return "Unknown"
        if age <= 24:
            return "18–24"
        if age <= 34:
            return "25–34"
        if age <= 44:
            return "35–44"
        if age <= 54:
            return "45–54"
        return "55+"

    counts = {}

    for accused in accused_rows:
        case_id = accused.get("CaseMasterID")
        if case_id is None:
            continue

        minor_id = case_type.get(str(case_id))
        crime_type = type_lookup.get(str(minor_id), "Unknown")
        band = age_band(accused.get("AgeYear"))

        counts.setdefault(band, {})
        counts[band][crime_type] = (
            counts[band].get(crime_type, 0) + 1
        )

    age_order = [
        "18–24",
        "25–34",
        "35–44",
        "45–54",
        "55+",
        "Unknown",
    ]

    age_labels = [
        band for band in age_order
        if band in counts
    ]

    crime_labels = sorted(
        {crime for group in counts.values() for crime in group},
        key=lambda value: value.lower()
    )

    records = []
    matrix = {}

    for band in age_labels:
        matrix[band] = {}
        for crime in crime_labels:
            value = counts.get(band, {}).get(crime, 0)
            matrix[band][crime] = value
            if value:
                records.append({
                    "AgeGroup": band,
                    "CrimeType": crime,
                    "AccusedCount": value,
                })

    return {
        "query_type": "analytics",
        "analytics_dimension": "sociological_age_crime_type",
        "chart_type": "grouped_bar",
        "title": "Accused Age Group × Crime Type",
        "unit_label": "accused records",
        "labels": age_labels,
        "values": [
            sum(matrix[band].values())
            for band in age_labels
        ],
        "series": [
            {
                "name": crime,
                "values": [
                    matrix[band].get(crime, 0)
                    for band in age_labels
                ],
            }
            for crime in crime_labels
        ],
        "categories": crime_labels,
        "total": len(accused_rows),
        "records": records,
        "matrix": matrix,
        "method": (
            "Deterministic cross-tabulation of Accused.AgeYear age bands against "
            "the crime type resolved from CaseMaster.CrimeMinorHeadID and CrimeSubHead.CrimeHeadName. "
            "This is descriptive association analysis and does not imply causation or risk."
        ),
        "source_queries": [
            accused_query,
            case_query,
            subhead_query,
        ],
    }



def build_repeat_accused_hotspot(app):
    case_query = "SELECT CaseMasterID, CrimeNo, CaseNO, CrimeMinorHeadID, latitude, longitude, PoliceStationID FROM CaseMaster LIMIT 300"
    accused_query = ALL_ACCUSED_QUERY
    unit_query = "SELECT UnitID, UnitName FROM Unit LIMIT 300"
    subhead_query = "SELECT CrimeSubHeadID, CrimeHeadName FROM CrimeSubHead LIMIT 300"

    case_rows = execute_zcql(app, case_query)
    accused_rows = execute_zcql(app, accused_query)
    unit_rows = execute_zcql(app, unit_query)
    subhead_rows = execute_zcql(app, subhead_query)

    crime_lookup = {
        str(r.get("CrimeSubHeadID")): r.get("CrimeHeadName") or "Unknown Crime"
        for r in subhead_rows if r.get("CrimeSubHeadID") is not None
    }
    station_lookup = {
        str(r.get("UnitID")): r.get("UnitName") or f"Station {r.get('UnitID')}"
        for r in unit_rows if r.get("UnitID") is not None
    }
    case_index = {str(r.get("CaseMasterID")): r for r in case_rows if r.get("CaseMasterID") is not None}

    person_cases = {}
    person_labels = {}
    for row in accused_rows:
        cid = row.get("CaseMasterID")
        name = (row.get("AccusedName") or "").strip()
        if cid is None or not name: continue
        pid = row.get("PersonID")
        key = f"id:{pid}" if pid is not None else f"name:{normalize_person_name(name)}"
        person_cases.setdefault(key, set()).add(str(cid))
        person_labels[key] = name

    records = []
    for key, case_ids in person_cases.items():
        if len(case_ids) < 2: continue
        cells = {}
        for cid in case_ids:
            c = case_index.get(cid, {})
            try:
                cell_key = (round(float(c.get("latitude")), 2), round(float(c.get("longitude")), 2))
            except (TypeError, ValueError):
                continue
            cell = cells.setdefault(cell_key, {"cases": [], "stations": set(), "crimes": set()})
            cell["cases"].append(cid)
            sid = c.get("PoliceStationID")
            cell["stations"].add(station_lookup.get(str(sid), f"Station {sid}"))
            cell["crimes"].add(crime_lookup.get(str(c.get("CrimeMinorHeadID")), "Unknown Crime"))
        for (lat, lon), cell in cells.items():
            if len(cell["cases"]) < 2: continue
            firs = [case_index.get(cid, {}).get("CaseNO") or case_index.get(cid, {}).get("CrimeNo") or f"Case {cid}" for cid in cell["cases"]]
            records.append({
                "AccusedName": person_labels[key],
                "Latitude": lat, "Longitude": lon,
                "CaseCount": len(cell["cases"]), "FIRs": firs,
                "Stations": sorted(cell["stations"]),
                "CrimeTypes": sorted(cell["crimes"]),
            })
    records.sort(key=lambda r: (-r["CaseCount"], r["AccusedName"].lower(), r["Latitude"], r["Longitude"]))
    return {
        "query_type": "cross_intelligence",
        "chart_type": "hotspot_network",
        "title": "Repeat Accused × Crime Hotspots",
        "unit_label": "cross-dimension signals",
        "total": len(records), "records": records,
        "source_queries": [case_query, accused_query, subhead_query, unit_query],
        "method": "Deterministic intersection of repeated accused identities with recurring spatial cells derived from CaseMaster coordinates. This is evidence linkage, not a culpability or risk determination."
    }


def build_monthly_peak_analytics(app):
    """Deterministically find the month with the highest FIR count."""
    trend = build_monthly_trend_analytics(app)
    rows = trend.get("records") or []
    if not rows:
        return {
            "query_type": "analytics",
            "chart_type": "bar",
            "title": "Peak Month FIR Activity",
            "labels": [],
            "values": [],
            "total": 0,
            "records": [],
            "source_queries": trend.get("source_queries", []),
            "method": "Deterministic monthly aggregation followed by maximum-count selection."
        }

    peak = max(rows, key=lambda r: (int(r.get("CaseCount") or 0), str(r.get("Month") or "")))
    month = str(peak.get("Month") or "Unknown")
    count = int(peak.get("CaseCount") or 0)
    return {
        "query_type": "analytics",
        "chart_type": "bar",
        "title": "Peak Month FIR Activity",
        "labels": [month],
        "values": [count],
        "total": int(trend.get("total") or 0),
        "records": [{"Month": month, "CaseCount": count}],
        "peak_month": month,
        "peak_count": count,
        "source_queries": trend.get("source_queries", []),
        "method": "Deterministic monthly FIR aggregation followed by maximum-count selection; Gemini was not required."
    }



def _load_cross_case_rows(app):
    query = "SELECT CaseMasterID, CrimeMinorHeadID, PoliceStationID, latitude, longitude, CrimeRegisteredDate FROM CaseMaster LIMIT 300"
    return execute_zcql(app, query), query


def _safe_case_enrich_for_cross(app, rows):
    try:
        return enrich_case_rows(app, rows)
    except Exception as exc:
        print("CROSS ANALYSIS ENRICHMENT FAILED:", exc)
        return rows


def build_crime_type_across_stations_analytics(app):
    rows, case_query = _load_cross_case_rows(app)
    rows = _safe_case_enrich_for_cross(app, rows)
    grouped = {}
    for row in rows:
        crime = row.get("CrimeType") or row.get("CrimeGroup") or "Unknown crime"
        station = row.get("StationName") or "Unknown station"
        grouped.setdefault(crime, set()).add(station)

    ranked = sorted(
        ((crime, stations) for crime, stations in grouped.items() if len(stations) > 1),
        key=lambda x: (-len(x[1]), x[0].lower())
    )
    records = [
        {"CrimeType": crime, "StationCount": len(stations), "Stations": sorted(stations)}
        for crime, stations in ranked
    ]
    return {
        "query_type": "analytics",
        "chart_type": "bar",
        "title": "Crime Types Across Police Stations",
        "labels": [r["CrimeType"] for r in records],
        "values": [r["StationCount"] for r in records],
        "records": records,
        "total": len(rows),
        "method": "Deterministic cross-tabulation of crime types against police stations from CaseMaster and reference data.",
        "source_queries": [case_query, "SELECT UnitID, UnitName FROM Unit LIMIT 300", "SELECT CrimeSubHeadID, CrimeHeadID, CrimeHeadName FROM CrimeSubHead LIMIT 300"],
    }


def build_station_crime_patterns_analytics(app):
    rows, case_query = _load_cross_case_rows(app)
    rows = _safe_case_enrich_for_cross(app, rows)
    counts = {}
    for row in rows:
        station = row.get("StationName") or "Unknown station"
        crime = row.get("CrimeType") or row.get("CrimeGroup") or "Unknown crime"
        counts[(station, crime)] = counts.get((station, crime), 0) + 1
    ranked = sorted(
        ((station, crime, count) for (station, crime), count in counts.items() if count > 1),
        key=lambda x: (-x[2], x[0].lower(), x[1].lower())
    )
    records = [
        {"StationName": station, "CrimeType": crime, "CaseCount": count}
        for station, crime, count in ranked
    ]
    return {
        "query_type": "analytics",
        "chart_type": "station_pattern",
        "title": "Repeated Crime Patterns by Station",
        "labels": [f"{r['StationName']} · {r['CrimeType']}" for r in records],
        "values": [r["CaseCount"] for r in records],
        "records": records,
        "total": len(rows),
        "method": "Deterministic station-by-crime aggregation; only recurring combinations appearing in at least two FIRs are shown.",
        "source_queries": [case_query, "SELECT UnitID, UnitName FROM Unit LIMIT 300", "SELECT CrimeSubHeadID, CrimeHeadID, CrimeHeadName FROM CrimeSubHead LIMIT 300"],
    }


def build_person_crime_station_analytics(app):
    accused_rows = execute_zcql(app, ALL_ACCUSED_QUERY)
    case_rows, case_query = _load_cross_case_rows(app)
    case_rows = _safe_case_enrich_for_cross(app, case_rows)
    case_index = {str(r.get("CaseMasterID")): r for r in case_rows if r.get("CaseMasterID") is not None}

    person_cases = {}
    for row in accused_rows:
        name = (row.get("AccusedName") or "").strip()
        cid = row.get("CaseMasterID")
        if not name or cid is None:
            continue
        pid = row.get("PersonID")
        key = f"id:{pid}" if pid is not None else f"name:{normalize_person_name(name)}"
        person_cases.setdefault(key, {"name": name, "case_ids": set()})["case_ids"].add(str(cid))

    records = []
    for person in person_cases.values():
        crime_stations = {}
        for cid in person["case_ids"]:
            case = case_index.get(cid, {})
            crime = case.get("CrimeType") or case.get("CrimeGroup")
            station = case.get("StationName")
            if crime and station:
                crime_stations.setdefault(crime, set()).add(station)
        for crime, stations in crime_stations.items():
            if len(stations) > 1:
                records.append({
                    "AccusedName": person["name"],
                    "CrimeType": crime,
                    "StationCount": len(stations),
                    "Stations": sorted(stations),
                })

    records.sort(key=lambda r: (-r["StationCount"], r["AccusedName"].lower(), r["CrimeType"].lower()))
    return {
        "query_type": "analytics",
        "chart_type": "person_crime_station",
        "title": "People Linked Across Crime Types and Stations",
        "labels": [f"{r['AccusedName']} · {r['CrimeType']}" for r in records],
        "values": [r["StationCount"] for r in records],
        "records": records,
        "total": len(accused_rows),
        "method": "Deterministic intersection of accused identities, crime types, and police stations across case records.",
        "source_queries": [ALL_ACCUSED_QUERY, case_query, "SELECT UnitID, UnitName FROM Unit LIMIT 300", "SELECT CrimeSubHeadID, CrimeHeadID, CrimeHeadName FROM CrimeSubHead LIMIT 300"],
    }


def build_crime_location_recurrence_analytics(app):
    rows, case_query = _load_cross_case_rows(app)
    rows = _safe_case_enrich_for_cross(app, rows)
    groups = {}
    for row in rows:
        try:
            lat = round(float(row.get("latitude")), 2)
            lon = round(float(row.get("longitude")), 2)
        except (TypeError, ValueError):
            continue
        crime = row.get("CrimeType") or row.get("CrimeGroup") or "Unknown crime"
        key = (crime, lat, lon)
        groups.setdefault(key, []).append(row)
    ranked = sorted(
        groups.items(), key=lambda item: (-len(item[1]), item[0][0].lower(), item[0][1], item[0][2])
    )
    records = []
    for (crime, lat, lon), items in ranked:
        if len(items) < 2:
            continue
        records.append({
            "CrimeType": crime,
            "Latitude": lat,
            "Longitude": lon,
            "CaseCount": len(items),
            "FIRs": [r.get("CaseNO") or r.get("CrimeNo") or f"Case {r.get('CaseMasterID')}" for r in items],
        })
    return {
        "query_type": "analytics",
        "chart_type": "bar",
        "title": "Recurring Crime Type + Location Combinations",
        "labels": [f"{r['CrimeType']} · {r['Latitude']:.2f}, {r['Longitude']:.2f}" for r in records],
        "values": [r["CaseCount"] for r in records],
        "records": records,
        "total": len(rows),
        "method": "Deterministic grouping of crime type and approximate 0.01-degree location cells; recurring combinations only.",
        "source_queries": [case_query, "SELECT CrimeSubHeadID, CrimeHeadID, CrimeHeadName FROM CrimeSubHead LIMIT 300"],
    }


def build_process_intelligence_analytics(app, mode="overview"):
    case_query = "SELECT CaseMasterID, CaseNO, CrimeNo, CrimeRegisteredDate, CaseStatusID FROM CaseMaster LIMIT 300"
    chargesheet_query = "SELECT CSID, CaseMasterID, csdate, cstype FROM ChargesheetDetails LIMIT 300"
    arrest_query = "SELECT ArrestSurrenderID, CaseMasterID, ArrestSurrenderDate, ArrestSurrenderTypeID, AccusedMasterID FROM ArrestSurrender LIMIT 300"
    legal_query = "SELECT CaseMasterID, ActID, SectionID FROM ActSectionAssociation LIMIT 300"
    status_query = "SELECT CaseStatusID, CaseStatusName FROM CaseStatusMaster LIMIT 300"

    cases = execute_zcql(app, case_query)
    chargesheets = execute_zcql(app, chargesheet_query)
    arrests = execute_zcql(app, arrest_query)
    legal = execute_zcql(app, legal_query)

    case_index = {str(r.get("CaseMasterID")): r for r in cases if r.get("CaseMasterID") is not None}
    cs_by_case = {}
    for r in chargesheets:
        cid = r.get("CaseMasterID")
        if cid is not None:
            cs_by_case.setdefault(str(cid), []).append(r)
    arrest_by_case = {}
    for r in arrests:
        cid = r.get("CaseMasterID")
        if cid is not None:
            arrest_by_case.setdefault(str(cid), []).append(r)
    legal_by_case = {}
    for r in legal:
        cid = r.get("CaseMasterID")
        if cid is not None:
            legal_by_case.setdefault(str(cid), []).append(r)

    def case_label(cid):
        row = case_index.get(str(cid), {})
        return row.get("CaseNO") or row.get("CrimeNo") or f"Case {cid}"

    def case_record(cid):
        row = case_index.get(str(cid), {})
        return {
            "FIR": case_label(cid),
            "Date": row.get("CrimeRegisteredDate"),
            "Status": row.get("CaseStatusID"),
        }

    case_ids = list(case_index.keys())

    if mode in {"missing_chargesheet", "missing_arrest", "missing_legal", "investigation_gaps"}:
        status_rows = execute_zcql(app, status_query)
        status_name_by_id = {str(r.get("CaseStatusID")): str(r.get("CaseStatusName") or "") for r in status_rows}
        missing_chargesheet = [cid for cid in case_ids if cid not in cs_by_case]
        missing_arrest = [cid for cid in case_ids if cid not in arrest_by_case]
        missing_legal = [cid for cid in case_ids if cid not in legal_by_case]
        under_investigation = [cid for cid in case_ids if "under investigation" in status_name_by_id.get(str(case_index[cid].get("CaseStatusID")), "").lower()]

        if mode == "missing_chargesheet":
            selected = missing_chargesheet
            title = "Cases Without Chargesheet"
            reason = "No matching CaseMasterID was found in ChargesheetDetails."
        elif mode == "missing_arrest":
            selected = missing_arrest
            title = "Cases Without Arrest / Surrender Record"
            reason = "No matching CaseMasterID was found in ArrestSurrender."
        elif mode == "missing_legal":
            selected = missing_legal
            title = "Cases Missing Act / Section Records"
            reason = "No matching CaseMasterID was found in ActSectionAssociation."
        else:
            selected = sorted(set(under_investigation) & set(missing_chargesheet))
            title = "Investigation Gaps"
            reason = "Under-investigation cases with no ChargesheetDetails record."

        rows = [
            {
                **case_record(cid),
                "Gap": reason,
            }
            for cid in selected
        ]
        rows.sort(key=lambda r: (str(r.get("Date") or ""), r["FIR"]), reverse=True)
        return {
            "query_type": "analytics",
            "chart_type": "process_list",
            "title": title,
            "labels": [r["FIR"] for r in rows],
            "values": [1 for _ in rows],
            "records": rows,
            "total": len(cases),
            "matched_count": len(rows),
            "method": "Deterministic CaseMasterID linkage against KSP investigation-process records; no LLM fallback.",
            "source_queries": [case_query, chargesheet_query, arrest_query, legal_query, status_query],
        }

    if mode == "chargesheet_cases":
        rows = []
        for cid, entries in cs_by_case.items():
            if cid in case_index:
                c = case_index[cid]
                rows.append({"FIR": case_label(cid), "Date": c.get("CrimeRegisteredDate"), "ChargesheetCount": len(entries), "ChargesheetDate": entries[-1].get("csdate")})
        rows.sort(key=lambda r: (str(r.get("ChargesheetDate") or ""), r["FIR"]), reverse=True)
        return {"query_type":"analytics","chart_type":"process_list","title":"Cases with Chargesheet Records","labels":[r["FIR"] for r in rows],"values":[r["ChargesheetCount"] for r in rows],"records":rows,"total":len(cases),"method":"Deterministic matching of CaseMasterID values against ChargesheetDetails.","source_queries":[case_query, chargesheet_query]}

    if mode == "arrest_cases":
        rows=[]
        for cid, entries in arrest_by_case.items():
            if cid in case_index:
                rows.append({"FIR": case_label(cid), "Date": case_index[cid].get("CrimeRegisteredDate"), "ArrestSurrenderCount": len(entries), "LatestArrestSurrenderDate": max((e.get("ArrestSurrenderDate") for e in entries if e.get("ArrestSurrenderDate")), default=None)})
        rows.sort(key=lambda r: (str(r.get("LatestArrestSurrenderDate") or ""), r["FIR"]), reverse=True)
        return {"query_type":"analytics","chart_type":"process_list","title":"Cases with Arrest / Surrender Records","labels":[r["FIR"] for r in rows],"values":[r["ArrestSurrenderCount"] for r in rows],"records":rows,"total":len(cases),"method":"Deterministic matching of CaseMasterID values against ArrestSurrender records.","source_queries":[case_query, arrest_query]}

    if mode == "legal_cases":
        rows=[]
        for cid, entries in legal_by_case.items():
            if cid in case_index:
                rows.append({"FIR": case_label(cid), "LegalLinkCount": len(entries), "Date": case_index[cid].get("CrimeRegisteredDate")})
        rows.sort(key=lambda r: (-r["LegalLinkCount"], r["FIR"]))
        return {"query_type":"analytics","chart_type":"process_list","title":"Cases with Act / Section Records","labels":[r["FIR"] for r in rows],"values":[r["LegalLinkCount"] for r in rows],"records":rows,"total":len(cases),"method":"Deterministic matching of CaseMasterID values against ActSectionAssociation records.","source_queries":[case_query, legal_query]}

    summary = {"chargesheet_cases": len(cs_by_case), "arrest_surrender_cases": len(arrest_by_case), "legal_linked_cases": len(legal_by_case), "total_cases": len(cases)}
    rows = [{"Process":"Chargesheet", "CaseCount":summary["chargesheet_cases"]},{"Process":"Arrest / Surrender", "CaseCount":summary["arrest_surrender_cases"]},{"Process":"Act / Section", "CaseCount":summary["legal_linked_cases"]}]
    return {"query_type":"analytics","chart_type":"bar","title":"Investigation Process Records","labels":[r["Process"] for r in rows],"values":[r["CaseCount"] for r in rows],"records":rows,"total":len(cases),"summary":summary,"method":"Deterministic CaseMasterID linkage across chargesheet, arrest/surrender, and Act/Section records.","source_queries":[case_query, chargesheet_query, arrest_query, legal_query]}

def build_analytics(app, analytics_type: str):
    if analytics_type == "case_status":
        return build_case_status_analytics(app)

    if analytics_type == "station":
        return build_station_analytics(app)

    if analytics_type == "crime_type":
        return build_crime_type_analytics(app)

    if analytics_type == "monthly_trend":
        return build_monthly_trend_analytics(app)

    if analytics_type == "monthly_peak":
        return build_monthly_peak_analytics(app)

    if analytics_type == "hotspot":
        return build_hotspot_analytics(app)

    if analytics_type == "hotspot_bengaluru":
        return build_hotspot_analytics(app, location_filter="bengaluru")

    if analytics_type == "early_warning":
        return build_early_warning_analytics(app)

    if analytics_type == "accused_age":
        return build_accused_age_analytics(app)

    if analytics_type == "accused_gender":
        return build_accused_gender_analytics(app)

    if analytics_type == "accused_age_crime_type":
        return build_accused_age_crime_type_analytics(app)

    if analytics_type == "crime_type_across_stations":
        return build_crime_type_across_stations_analytics(app)

    if analytics_type == "station_crime_patterns":
        return build_station_crime_patterns_analytics(app)

    if analytics_type == "person_crime_station":
        return build_person_crime_station_analytics(app)

    if analytics_type == "crime_location_recurrence":
        return build_crime_location_recurrence_analytics(app)

    if analytics_type == "missing_chargesheet":
        return build_process_intelligence_analytics(app, "missing_chargesheet")

    if analytics_type == "missing_arrest":
        return build_process_intelligence_analytics(app, "missing_arrest")

    if analytics_type == "missing_legal":
        return build_process_intelligence_analytics(app, "missing_legal")

    if analytics_type == "investigation_gaps":
        return build_process_intelligence_analytics(app, "investigation_gaps")

    if analytics_type == "chargesheet_cases":
        return build_process_intelligence_analytics(app, "chargesheet_cases")

    if analytics_type == "arrest_cases":
        return build_process_intelligence_analytics(app, "arrest_cases")

    if analytics_type == "legal_cases":
        return build_process_intelligence_analytics(app, "legal_cases")

    if analytics_type == "process_overview":
        return build_process_intelligence_analytics(app, "overview")

    raise ValueError(
        f"Unsupported analytics type: {analytics_type}"
    )



def build_explainability(query_type, generated_sql="", analytics=None, intelligence=None, network=None, result_count=0):
    """Build a concise, auditable evidence trail without exposing model chain-of-thought."""
    analytics = analytics or {}
    intelligence = intelligence or {}
    network = network or {}

    source_tables = []
    evidence_basis = ""
    method = ""
    limitations = []

    if query_type == "analytics":
        source_by_type = {
            "crime_type": ["CaseMaster", "CrimeSubHead"],
            "station": ["CaseMaster", "Unit"],
            "case_status": ["CaseMaster", "CaseStatusMaster"],
            "monthly_trend": ["CaseMaster"],
            "monthly_peak": ["CaseMaster"],
            "missing_chargesheet": ["CaseMaster", "ChargesheetDetails", "CaseStatusMaster"],
            "missing_arrest": ["CaseMaster", "ArrestSurrender"],
            "missing_legal": ["CaseMaster", "ActSectionAssociation"],
            "investigation_gaps": ["CaseMaster", "ChargesheetDetails", "CaseStatusMaster"],
            "chargesheet_cases": ["CaseMaster", "ChargesheetDetails"],
            "arrest_cases": ["CaseMaster", "ArrestSurrender"],
            "legal_cases": ["CaseMaster", "ActSectionAssociation"],
            "process_overview": ["CaseMaster", "ChargesheetDetails", "ArrestSurrender", "ActSectionAssociation"],
            "hotspot": ["CaseMaster", "Unit"],
            "chargesheet_cases": ["CaseMaster", "ChargesheetDetails"],
            "arrest_cases": ["CaseMaster", "ArrestSurrender"],
            "legal_cases": ["CaseMaster", "ActSectionAssociation"],
            "process_overview": ["CaseMaster", "ChargesheetDetails", "ArrestSurrender", "ActSectionAssociation"],
            "hotspot_bengaluru": ["CaseMaster", "Unit", "District"],
            "early_warning": ["CaseMaster", "CrimeSubHead", "Accused", "Unit"],
            "accused_age": ["Accused"],
            "accused_gender": ["Accused"],
            "accused_age_crime_type": ["Accused", "CaseMaster", "CrimeSubHead"],
        }
        analytics_type = ""
        title = str(analytics.get("title", "")).lower()
        chart_type = analytics.get("chart_type")
        if "crime type" in title:
            analytics_type = "crime_type"
        elif "police station" in title:
            analytics_type = "station"
        elif "case status" in title:
            analytics_type = "case_status"
        elif "peak month" in title:
            analytics_type = "monthly_peak"
        elif "monthly" in title:
            analytics_type = "monthly_trend"
        elif "hotspot" in title:
            analytics_type = "hotspot"
        elif "proactive" in title:
            analytics_type = "early_warning"
        elif "age distribution" in title:
            analytics_type = "accused_age"
        elif "gender distribution" in title:
            analytics_type = "accused_gender"
        elif "age group" in title and "crime type" in title:
            analytics_type = "accused_age_crime_type"

        source_tables = source_by_type.get(analytics_type, [])
        evidence_basis = analytics.get("method") or f"Deterministic aggregation from {', '.join(source_tables) or 'Catalyst Data Store'} values."
        method = "Deterministic server-side aggregation; Gemini was not required for this analytical path."
        if analytics_type in {"hotspot", "hotspot_bengaluru"}:
            limitations.append("Spatial results are approximate 0.01-degree cells, not statistically validated hotspot boundaries.")
        if analytics_type == "early_warning":
            limitations.append("Signals are evidence-based triage indicators, not predictive risk scores.")

    elif query_type == "case_investigation":
        keys = ["accused", "victims", "complainants", "legal", "chargesheets", "arrests", "related_cases", "relationship_evidence"]
        source_map = {
            "accused": "Accused", "victims": "Victim", "complainants": "ComplainantDetails",
            "legal": "ActSectionAssociation", "chargesheets": "ChargesheetDetails", "arrests": "ArrestSurrender",
            "related_cases": "CaseMaster", "relationship_evidence": "Accused"
        }
        source_tables = ["CaseMaster"] + [source_map[k] for k in keys if intelligence.get(k)]
        source_tables = list(dict.fromkeys(source_tables))
        evidence_basis = "Case record plus related KSP tables and cross-case identity matches."
        method = "Deterministic case retrieval, reference-data enrichment, and cross-case relationship analysis."
        if not intelligence.get("victims"):
            limitations.append("No victim records were available for this case.")
        if not intelligence.get("complainants"):
            limitations.append("No complainant records were available for this case.")

    elif query_type == "criminal_network":
        source_tables = ["Accused", "CaseMaster"]
        evidence_basis = "Shared CaseMasterID relationships between accused identities; PersonID is preferred and normalized name is a fallback."
        method = "Deterministic person-to-case-to-person relationship traversal."
        if network.get("graph"):
            limitations.append("Relationship strength reflects shared case count, not a claim of criminal culpability or causation.")

    elif query_type == "case_search":
        source_tables = ["CaseMaster"]
        evidence_basis = "FIR fields enriched with KSP reference/master tables."
        method = "Deterministic CaseMaster retrieval followed by reference-data enrichment."

    elif query_type == "gemini_zcql":
        # Keep this transparent without exposing hidden model reasoning.
        source_tables = re.findall(
            r"\b(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_]*)",
            generated_sql or "",
            flags=re.IGNORECASE,
        )
        source_tables = list(dict.fromkeys(source_tables))
        evidence_basis = "The generated read-only ZCQL query was executed against the Catalyst Data Store."
        method = "Gemini generated the SQL candidate; Vaani validated it for SELECT-only safety and JOIN limits before execution."
        limitations.append("Natural-language interpretation depends on the generated ZCQL query; the executed SQL is shown above for verification.")

    else:
        source_tables = []
        evidence_basis = "No result-producing data path was completed."
        method = "No executable intelligence path was completed."

    return {
        "source_tables": source_tables,
        "evidence_basis": evidence_basis,
        "method": method,
        "records_considered": analytics.get("total", result_count) if query_type == "analytics" else result_count,
        "limitations": limitations,
        "generated_query_available": bool(generated_sql),
    }


def get_request_identity(app):
    """Resolve the Catalyst-authenticated user for this request.

    In local catalyst serve sessions without Authentication enabled,
    Catalyst may return no end-user. We preserve local development while
    allowing production to enforce authenticated access via VAANI_ENFORCE_AUTH.
    """
    identity = {
        "authenticated": False,
        "user_id": None,
        "email": None,
        "role": "Unauthenticated",
        "status": "UNKNOWN",
    }

    try:
        current_user = app.authentication().get_current_user()
    except Exception as exc:
        print("AUTH LOOKUP FAILED:", exc)
        return identity

    if not current_user:
        return identity

    role_details = current_user.get("role_details") or {}
    role_name = role_details.get("role_name") or current_user.get("role_name") or "App User"

    identity.update({
        "authenticated": True,
        "user_id": str(current_user.get("user_id")) if current_user.get("user_id") is not None else None,
        "email": current_user.get("email_id"),
        "role": role_name,
        "status": current_user.get("status", "ACTIVE"),
    })
    return identity


def authorize_request(identity):
    """Apply application-level authentication/role policy.

    Catalyst role permissions should remain the primary data-plane control;
    this guard adds an explicit application-level gate for Vaani endpoints.
    """
    if not VAANI_ENFORCE_AUTH:
        return True, None

    if not identity.get("authenticated"):
        return False, "Authentication is required to access Vaani intelligence. Sign in through Catalyst Authentication before querying the database."

    if identity.get("status") not in (None, "ACTIVE"):
        return False, "The current Catalyst user account is not active."

    role = identity.get("role") or ""
    if VAANI_ALLOWED_ROLES and role not in VAANI_ALLOWED_ROLES:
        return False, f"Role '{role}' is not authorized to use this application."

    return True, None


def audit_preflight(app, identity, session_id, query_text, outcome="authorized"):
    """Create a durable audit-start event before touching protected data.

    In enforced production mode, a failed audit write blocks the data operation.
    This prevents a request from succeeding silently when the audit trail is unavailable.
    """
    if not VAANI_ENFORCE_AUTH or not VAANI_AUDIT_REQUIRED:
        return {"recorded": True, "row_id": None}

    return audit_request(
        app, identity, session_id, query_text, "request_start", 0, outcome
    )


def audit_request(app, identity, session_id, query_text, query_type, result_count, outcome):
    """Persist an application audit event.

    Operational queries use the authenticated USER scope when auth is enforced.
    Audit logging uses a separate ADMIN-scoped SDK instance so operational roles
    can remain read-only on the crime tables while the application appends audit
    records. The audit table must be permissioned accordingly in Catalyst.
    """
    row = {
        "RequestID": str(int(time.time() * 1000)),
        "UserID": identity.get("user_id") or "anonymous",
        "UserEmail": identity.get("email") or "",
        "UserRole": identity.get("role") or "Unauthenticated",
        "SessionID": session_id,
        "QueryText": (query_text or "")[:500],
        "QueryType": query_type or "unknown",
        "ResultCount": int(result_count or 0),
        "Outcome": outcome or "completed",
        "EventTime": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    try:
        # Audit is the only path that intentionally uses an admin-scoped SDK.
        audit_app = zcatalyst_sdk.initialize(scope="admin")
        table_service = audit_app.datastore().table(AUDIT_TABLE_NAME)
        inserted = table_service.insert_row(row)
        if isinstance(inserted, list) and inserted:
            inserted = inserted[0]
        return {
            "recorded": True,
            "row_id": inserted.get("ROWID") if isinstance(inserted, dict) else None,
        }
    except Exception as exc:
        print("AUDIT LOG NOT RECORDED:", exc)
        return {
            "recorded": False,
            "row_id": None,
            "error": str(exc)[:240],
        }



def is_contextual_case_reference(text: str, state: dict | None = None) -> bool:
    """Detect follow-up questions that refer to the previous result set."""
    q = _normalize_query_text(text).lower()
    state = state or {}
    has_reference = _query_contains_any(q, [
        "those cases", "these cases", "those firs", "these firs",
        "those records", "these records", "the above cases", "the above firs",
        "the previous cases", "the previous firs", "same cases", "same firs",
        "among them", "from them", "which of them", "which of those",
        "ಇವುಗಳಲ್ಲಿ", "ಅವುಗಳಲ್ಲಿ", "ಮೇಲಿನ ಪ್ರಕರಣಗಳು", "ಹಿಂದಿನ ಪ್ರಕರಣಗಳು",
        "ಆ FIR", "ಆ FIRಗಳು", "ಈ FIR", "ಈ FIRಗಳು", "ಅವುಗಳ", "ಇವುಗಳ"
    ])
    return bool(has_reference and state.get("active_case_ids"))


def build_contextual_case_search(app, text: str, state: dict | None):
    """Build a deterministic CaseMaster query over the previous result set."""
    state = state or {}
    case_ids = [str(x) for x in (state.get("active_case_ids") or []) if x is not None]
    if not case_ids:
        return None

    filters = parse_common_fir_filters(text)
    refs = load_reference_data(app)
    where = ["CaseMasterID IN (" + ",".join(case_ids) + ")"]

    # Resolve the same common filters used by normal FIR search, but constrain
    # them to the previous result set. This prevents context from leaking into
    # unrelated future queries.
    if "gravity" in filters:
        rows = [
            r for r in refs.get("GravityOffence", [])
            if str(r.get("LookupValue") or "").strip().lower() == str(filters["gravity"]).lower()
        ]
        ids = [str(r["GravityOffenceID"]) for r in rows if r.get("GravityOffenceID") is not None]
        if ids:
            where.append("GravityOffenceID IN (" + ",".join(ids) + ")")

    if "status" in filters:
        ids = _resolve_reference_ids(
            app, "CaseStatusMaster", "CaseStatusID", "CaseStatusName", filters["status"]
        )
        if ids:
            where.append("CaseStatusID IN (" + ",".join(ids) + ")")

    if "crime_type" in filters:
        rows = [
            r for r in refs.get("CrimeSubHead", [])
            if str(r.get("CrimeHeadName") or "").strip().lower() == str(filters["crime_type"]).lower()
        ]
        ids = [str(r["CrimeSubHeadID"]) for r in rows if r.get("CrimeSubHeadID") is not None]
        if ids:
            where.append("CrimeMinorHeadID IN (" + ",".join(ids) + ")")

    if "station_text" in filters:
        station = str(filters["station_text"]).strip().lower()
        station_ids = []
        for row in refs.get("Unit", []):
            value = str(row.get("UnitName") or "").strip().lower()
            if value == station or station in value or value in station:
                if row.get("UnitID") is not None:
                    station_ids.append(str(row["UnitID"]))
        if station_ids:
            where.append("PoliceStationID IN (" + ",".join(sorted(set(station_ids))) + ")")

    if "date_from_exclusive" in filters:
        where.append(f"CrimeRegisteredDate > '{filters['date_from_exclusive']}'")
    elif "date_from" in filters:
        where.append(f"CrimeRegisteredDate >= '{filters['date_from']}'")

    if "date_to_exclusive" in filters:
        where.append(f"CrimeRegisteredDate < '{filters['date_to_exclusive']}'")

    base_case_select = ALL_FIRS_QUERY.rsplit("\nLIMIT 50", 1)[0]
    query = f"{base_case_select} WHERE {' AND '.join(where)} ORDER BY CrimeRegisteredDate DESC LIMIT 50"
    return query, filters


def build_investigator_brief(response):
    """Create a concise police-facing brief from verified response data.

    This is presentation metadata only: it never creates a new investigative
    conclusion that is not already supported by the deterministic result.
    """
    query_type = response.get("query_type") or ""
    explanation = response.get("explanation") or ""
    result_count = int(response.get("result_count") or 0)
    actions = []
    headline = explanation
    details = ""

    if query_type == "criminal_network":
        network = response.get("network") or {}
        target_network = network.get("target_network") or {}
        target = target_network.get("target") or {}
        name = target.get("AccusedName") or "the selected person"
        case_count = int(target.get("CaseCount") or len(target.get("Cases") or []) or 0)
        connections = target_network.get("connections") or []
        headline = f"{name}: {case_count} case(s), {len(connections)} connected person(s)."
        details = "Relationship evidence is based on shared KSP case identifiers."
        if target:
            actions = [
                {"label": "Review connections", "query": f"Who is connected to {name}?"},
                {"label": "Review case history", "query": f"Show me {name}'s cases"},
            ]
            if case_count:
                actions.append({"label": "Check Bengaluru overlap", "query": "Which of those cases are in Bengaluru?"})
        else:
            actions = [{"label": "Search another person", "query": "Show repeated accused activity"}]

    elif query_type == "case_investigation":
        case = response.get("case") or {}
        fir = case.get("CaseNO") or case.get("CrimeNo") or "the case"
        intel = response.get("intelligence") or {}
        related = len(intel.get("related_cases") or [])
        accused = len(intel.get("accused") or [])
        headline = f"{fir}: case record with {accused} accused record(s) and {related} related case(s)."
        details = "Review relationship evidence and investigation milestones before acting on a lead."
        actions = [
            {"label": "View related cases", "query": f"Show cases related to {fir}"},
            {"label": "Check network", "query": "Who is connected to the accused?"},
        ]

    elif query_type == "cross_intelligence":
        analytics = response.get("analytics") or {}
        records = analytics.get("records") or []
        headline = f"{len(records)} cross-dimension signal(s) found."
        details = "Signals link repeated accused identities with recurring spatial cells; they are evidence links, not culpability findings."
        actions = [
            {"label": "Open hotspot analysis", "query": "Where are the crime hotspots?"},
            {"label": "Review early warnings", "query": "What emerging crime patterns should investigators watch?"},
        ]
        if records:
            first = records[0]
            person = first.get("AccusedName")
            if person:
                actions.insert(0, {"label": "Open person network", "query": f"Who is connected to {person}?"})

    elif query_type == "analytics":
        analytics = response.get("analytics") or {}
        title = analytics.get("title") or "Crime analytics"
        total = analytics.get("total", result_count)
        headline = f"{title}: {total} record(s) analyzed."
        details = analytics.get("method") or "Deterministic analysis over the available KSP Data Store records."
        actions = [
            {"label": "Find repeat accused", "query": "What emerging crime patterns should investigators watch?"},
            {"label": "Investigate hotspots", "query": "Where are the crime hotspots?"},
        ]

    elif query_type == "case_search":
        headline = f"{result_count} FIR record(s) matched the request."
        details = explanation
        if result_count:
            actions = [
                {"label": "Find repeat accused", "query": "Which accused persons appear repeatedly?"},
                {"label": "See hotspots", "query": "Where are the crime hotspots?"},
            ]

    elif query_type in {"gemini_error", "gemini_unavailable", "rejected", "auth_error", "governance_blocked", "deterministic_error"}:
        headline = explanation or "The request could not be completed."
        details = "No unsupported intelligence conclusion was produced."
        actions = []

    else:
        headline = explanation or f"{result_count} record(s) returned."
        details = ""

    return {
        "headline": headline,
        "details": details,
        "actions": actions[:3],
    }


def finalize_response(basicio, context, app, response, identity, session_id, query_text, outcome="completed"):
    """Attach governance metadata, persist an audit event, then write the response."""
    audit = audit_request(
        app,
        identity,
        session_id,
        query_text,
        response.get("query_type"),
        response.get("result_count", 0),
        outcome,
    )

    response["governance"] = {
        "authenticated": bool(identity.get("authenticated")),
        "role": identity.get("role"),
        "user_id": identity.get("user_id"),
        "audit_recorded": audit.get("recorded", False),
        "audit_row_id": audit.get("row_id"),
        "auth_enforced": VAANI_ENFORCE_AUTH,
        "data_scope": "user" if VAANI_ENFORCE_AUTH else "admin-dev",
    }
    response["conversation_context"] = get_conversation_state(session_id)
    response["investigator_brief"] = build_investigator_brief(response)

    basicio.write(json.dumps(response, ensure_ascii=False, default=str))
    context.close()
    return


def handler(context, basicio):
    # Production: initialize the SDK in USER scope so Catalyst Data Store/ZCQL
    # honors the authenticated end-user's role permissions.
    # Local development keeps ADMIN scope unless authentication is explicitly enforced.
    sdk_scope = "user" if VAANI_ENFORCE_AUTH else "admin"
    app = zcatalyst_sdk.initialize(scope=sdk_scope)

    query_text = (basicio.get_argument("text") or "").strip()
    session_id = basicio.get_argument("session_id") or "default"

    # Client carries a compact, non-authoritative conversation context so
    # follow-up references survive Catalyst function restarts. It never grants access.
    client_context = basicio.get_argument("context") or ""
    if client_context:
        try:
            incoming = json.loads(client_context)
            if isinstance(incoming, dict):
                update_conversation_state(session_id, **{
                    key: incoming.get(key) for key in [
                        "active_person", "active_fir", "active_case_ids",
                        "active_filters", "last_intent", "last_query_type"
                    ] if key in incoming
                })
        except Exception:
            pass

    identity = get_request_identity(app)
    authorized, auth_error = authorize_request(identity)

    if not authorized:
        response = {
            "input_text": query_text,
            "generated_sql": "",
            "explanation": auth_error,
            "results": [],
            "result_count": 0,
            "query_type": "auth_error",
            "explainability": {
                "source_tables": [],
                "evidence_basis": "Request rejected by application authentication/authorization policy.",
                "method": "Catalyst Authentication user and role validation.",
                "records_considered": 0,
                "limitations": [],
                "generated_query_available": False,
            },
        }
        finalize_response(basicio, context, app, response, identity, session_id, query_text, "denied")
        return

    # Production audit gate: do not execute any protected query unless the audit
    # trail is writable. This keeps governance fail-closed.
    if VAANI_ENFORCE_AUTH and VAANI_AUDIT_REQUIRED:
        preflight = audit_preflight(app, identity, session_id, query_text)
        if not preflight.get("recorded"):
            response = {
                "input_text": query_text,
                "generated_sql": "",
                "explanation": "Vaani cannot execute this request because the required audit trail is unavailable. No protected data query was executed.",
                "results": [],
                "result_count": 0,
                "query_type": "governance_blocked",
                "explainability": {
                    "source_tables": [],
                    "evidence_basis": "Request blocked because the mandatory audit trail could not be written.",
                    "method": "Fail-closed governance preflight before protected data access.",
                    "records_considered": 0,
                    "limitations": ["Configure the VaaniAuditLog table and permissions for the deployed roles."],
                    "generated_query_available": False,
                },
                "governance": {
                    "authenticated": bool(identity.get("authenticated")),
                    "role": identity.get("role"),
                    "auth_enforced": True,
                    "audit_recorded": False,
                    "data_scope": "user",
                },
            }
            basicio.write(json.dumps(response, ensure_ascii=False, default=str))
            context.close()
            return

    if not query_text:
        response = {"input_text": "", "generated_sql": "", "explanation": "Please enter a question.", "results": [], "result_count": 0, "query_type": "empty"}
        finalize_response(basicio, context, app, response, identity, session_id, query_text, "completed")
        return

    # Load accused records once before canonical person/network routing.
    # This must happen before pairwise intent resolution.
    try:
        accused_rows_direct = execute_zcql(app, ALL_ACCUSED_QUERY)
    except Exception as exc:
        print("PERSON RESOLUTION DATA LOAD FAILED:", exc)
        accused_rows_direct = []

    # --------------------------------------------------------
    # DETERMINISTIC PAIRWISE SHARED-CASE FAST PATH
    # --------------------------------------------------------
    pairwise_intent = classify_canonical_intent(
        query_text,
        get_conversation_state(session_id),
        accused_rows_direct,
    )
    if pairwise_intent["intent"] == "PERSON_PAIR_SHARED_CASES":
        person_a = pairwise_intent["entities"]["person_a"]
        person_b = pairwise_intent["entities"]["person_b"]

        def person_case_ids(name):
            target = normalize_person_name(name)
            ids = set()
            for row in accused_rows_direct:
                row_name = normalize_person_name(row.get("AccusedName") or "")
                if row_name == target:
                    if row.get("CaseMasterID") is not None:
                        ids.add(str(row.get("CaseMasterID")))
            return ids

        a_ids = person_case_ids(person_a)
        b_ids = person_case_ids(person_b)
        shared_ids = sorted(
            a_ids & b_ids,
            key=lambda x: int(x) if x.isdigit() else x,
        )

        case_index = load_case_index(app)
        # Pairwise path must use the same reference-data enrichment as the
        # existing FIR/case-investigation paths. load_case_index returns raw
        # CaseMaster rows, so enrich the shared case rows before rendering.
        shared_case_rows = [
            case_index[str(cid)]
            for cid in shared_ids
            if str(cid) in case_index
        ]
        try:
            shared_case_rows = enrich_case_rows(app, shared_case_rows)
        except Exception as exc:
            print("PAIRWISE CASE ENRICHMENT FAILED:", exc)

        shared_case_index = {
            str(row.get("CaseMasterID")): row
            for row in shared_case_rows
            if row.get("CaseMasterID") is not None
        }

        shared_cases = []
        for cid in shared_ids:
            c = shared_case_index.get(str(cid), case_index.get(str(cid), {}))
            shared_cases.append({
                "CaseMasterID": str(cid),
                "FIR": c.get("CaseNO") or c.get("CrimeNo") or f"Case {cid}",
                "CrimeNo": c.get("CrimeNo"),
                "Date": c.get("CrimeRegisteredDate"),
                "StationName": c.get("StationName"),
                "CrimeType": c.get("CrimeType"),
            })

        response = {
            "input_text": query_text,
            "generated_sql": ALL_ACCUSED_QUERY,
            "explanation": f"{person_a} and {person_b} share {len(shared_cases)} case(s).",
            "results": shared_cases,
            "result_count": len(shared_cases),
            "query_type": "criminal_network",
            "network": {
                "pairwise": {
                    "person_a": person_a,
                    "person_b": person_b,
                    "shared_case_count": len(shared_cases),
                    "shared_cases": shared_cases,
                }
            },
            "explainability": {
                "source_tables": ["Accused", "CaseMaster"],
                "evidence_basis": "Intersection of CaseMasterID values for two verified accused identities.",
                "method": "Deterministic pairwise case-set intersection.",
                "records_considered": len(accused_rows_direct),
                "records_label": "SOURCE ACCUSED RECORDS",
                "limitations": ["Shared case membership does not establish culpability or causation."],
                "generated_query_available": True,
            },
        }
        update_conversation_state(
            session_id,
            active_person=person_a,
            active_case_ids=shared_ids,
            last_intent="PERSON_PAIR_SHARED_CASES",
            last_query_type="criminal_network",
        )
        finalize_response(basicio, context, app, response, identity, session_id, query_text, "completed")
        return

    # --------------------------------------------------------
    # DETERMINISTIC PERSON / NETWORK FAST PATH
    # --------------------------------------------------------
    # Resolve any person directly from the actual Accused table before Gemini.
    direct_intent = classify_canonical_intent(
        query_text,
        get_conversation_state(session_id),
        accused_rows_direct,
    )

    if direct_intent["intent"] in {"PERSON_CASE_HISTORY", "PERSON_NETWORK"}:
        try:
            target_name = direct_intent["entities"].get("person")
            case_index = load_case_index(app)

            # Global network analytics: no target person means "show repeated/multi-case people".
            if not target_name and direct_intent["intent"] == "PERSON_NETWORK":
                analysis = build_network_analysis(
                    accused_rows_direct, case_index, None
                )
                analysis["source_record_count"] = len(accused_rows_direct)
                results = analysis.get("repeated_accused", [])
                update_conversation_state(
                    session_id,
                    active_person=None,
                    active_case_ids=[],
                    last_intent="PERSON_NETWORK",
                    last_query_type="criminal_network",
                )
                response = {
                    "input_text": query_text,
                    "generated_sql": ALL_ACCUSED_QUERY,
                    "explanation": f"Found {len(results)} people appearing in multiple cases.",
                    "results": results,
                    "result_count": len(results),
                    "query_type": "criminal_network",
                    "network": analysis,
                    "explainability": {
                        "source_tables": ["Accused", "CaseMaster"],
                        "evidence_basis": "Repeated accused identities across multiple CaseMasterID values; PersonID preferred and normalized name fallback.",
                        "method": "Deterministic person-to-case aggregation.",
                        "records_considered": len(accused_rows_direct),
                        "records_label": "SOURCE ACCUSED RECORDS",
                        "limitations": ["Repeated appearance in case records does not establish culpability."],
                        "generated_query_available": True,
                    },
                }
                finalize_response(basicio, context, app, response, identity, session_id, query_text, "completed")
                return

            if not target_name:
                response = {
                    "input_text": query_text,
                    "generated_sql": "",
                    "explanation": "I could not resolve the person from the available accused records.",
                    "results": [],
                    "result_count": 0,
                    "query_type": "criminal_network",
                    "network": {"repeated_accused": [], "target_network": None, "graph": {"nodes": [], "edges": []}},
                }
                response["explainability"] = build_explainability(
                    "criminal_network", "", result_count=0
                )
                finalize_response(basicio, context, app, response, identity, session_id, query_text, "failed")
                return

            analysis = build_network_analysis(
                accused_rows_direct, case_index, target_name
            )
            analysis["source_record_count"] = len(accused_rows_direct)

            if not analysis.get("target_network"):
                response = {
                    "input_text": query_text,
                    "generated_sql": ALL_ACCUSED_QUERY,
                    "explanation": f"No accused record found for {target_name}.",
                    "results": [],
                    "result_count": 0,
                    "query_type": "criminal_network",
                    "network": analysis,
                    "explainability": {
                        "source_tables": ["Accused", "CaseMaster"],
                        "evidence_basis": "Person was verified against the Accused table, but no case relationship could be resolved.",
                        "method": "Deterministic person-to-case traversal.",
                        "records_considered": len(accused_rows_direct),
                        "records_label": "SOURCE ACCUSED RECORDS",
                        "limitations": ["No matching accused relationship was found."],
                        "generated_query_available": True,
                    },
                }
                finalize_response(basicio, context, app, response, identity, session_id, query_text, "completed")
                return

            target_net = analysis["target_network"]
            if direct_intent["intent"] == "PERSON_CASE_HISTORY":
                results = target_net.get("target", {}).get("Cases", [])
                explanation = (
                    f"Found {len(results)} case(s) involving "
                    f"{target_net.get('target', {}).get('AccusedName', target_name)}."
                )
                last_intent = "PERSON_CASE_HISTORY"
            else:
                results = target_net.get("connections", [])
                explanation = f"Found the relationship network for {target_net.get('target', {}).get('AccusedName', target_name)}."
                last_intent = "PERSON_NETWORK"

            update_conversation_state(
                session_id,
                active_person=target_net.get("target", {}).get("AccusedName", target_name),
                active_case_ids=[
                    x.get("CaseMasterID") for x in target_net.get("target", {}).get("Cases", [])
                ],
                last_intent=last_intent,
                last_query_type="criminal_network",
            )

            response = {
                "input_text": query_text,
                "generated_sql": ALL_ACCUSED_QUERY,
                "explanation": explanation,
                "results": results,
                "result_count": len(results),
                "query_type": "criminal_network",
                "network": analysis,
                "explainability": {
                    "source_tables": ["Accused", "CaseMaster"],
                    "evidence_basis": "Shared CaseMasterID relationships between accused identities; PersonID is preferred and normalized name is a fallback.",
                    "method": "Deterministic person-to-case-to-person relationship traversal.",
                    "records_considered": len(accused_rows_direct),
                    "records_label": "SOURCE ACCUSED RECORDS",
                    "limitations": ["Relationship strength reflects shared case count, not a claim of criminal culpability or causation."],
                    "generated_query_available": True,
                },
            }
            finalize_response(basicio, context, app, response, identity, session_id, query_text, "completed")
            return
        except Exception as exc:
            print("DIRECT PERSON PATH FAILED:", exc)
            # Do not let a person-targeted request fall into arbitrary Gemini SQL.
            response = {
                "input_text": query_text,
                "generated_sql": "",
                "explanation": "Vaani could not complete the deterministic person analysis. No database query was delegated to the language engine.",
                "results": [],
                "result_count": 0,
                "query_type": "deterministic_error",
                "explainability": {
                    "source_tables": ["Accused", "CaseMaster"],
                    "evidence_basis": "Deterministic person analysis failed before any LLM fallback.",
                    "method": "Fail-closed deterministic intelligence path.",
                    "records_considered": len(accused_rows_direct),
                    "limitations": [str(exc)[:240]],
                    "generated_query_available": False,
                },
            }
            finalize_response(basicio, context, app, response, identity, session_id, query_text, "failed")
            return

    # --------------------------------------------------------
    # CONTEXTUAL FOLLOW-UP CASE FILTERS
    # --------------------------------------------------------
    state = get_conversation_state(session_id)
    if is_contextual_case_reference(query_text, state):
        contextual = build_contextual_case_search(app, query_text, state)
        if contextual:
            query, parsed_filters = contextual
            try:
                rows = enrich_case_rows(app, execute_zcql(app, query))
                update_conversation_state(
                    session_id,
                    active_case_ids=[x.get("CaseMasterID") for x in rows if x.get("CaseMasterID") is not None],
                    active_filters=parsed_filters,
                    last_intent="FIR_SEARCH",
                    last_query_type="case_search",
                )
                response = {
                    "input_text": query_text,
                    "generated_sql": query,
                    "explanation": "Applied your follow-up filter to the cases from the previous result.",
                    "results": rows,
                    "result_count": len(rows),
                    "query_type": "case_search",
                    "filter_mode": "contextual_deterministic",
                    "filters": parsed_filters,
                    "contextual": True,
                    "explainability": build_explainability("case_search", query, result_count=len(rows)),
                }
            except Exception as exc:
                response = {
                    "input_text": query_text,
                    "generated_sql": query,
                    "explanation": "Follow-up case filtering failed: " + str(exc),
                    "results": [], "result_count": 0,
                    "query_type": "deterministic_error",
                    "explainability": {
                        "source_tables": ["CaseMaster"],
                        "evidence_basis": "Follow-up was constrained to the previous result set.",
                        "method": "Deterministic contextual filtering; no LLM fallback.",
                        "records_considered": len(state.get("active_case_ids") or []),
                        "limitations": [str(exc)[:240]],
                        "generated_query_available": True,
                    },
                }
            finalize_response(basicio, context, app, response, identity, session_id, query_text, "completed" if response.get("result_count", 0) >= 0 and response.get("query_type") != "deterministic_error" else "failed")
            return

    # --------------------------------------------------------
    # CASE INTELLIGENCE FAST PATH
    # --------------------------------------------------------
    if is_investigation_question(query_text):
        fir = extract_fir(query_text)
        case, lookup_query = get_case_by_fir(app, fir)
        if not case:
            response = {"input_text": query_text, "generated_sql": lookup_query, "explanation": f"No case was found for {fir}.", "results": [], "result_count": 0, "query_type": "case_investigation"}
            finalize_response(basicio, context, app, response, identity, session_id, query_text); return
        try:
            intelligence = build_case_intelligence(app, case)
            summary = build_case_summary(case, intelligence)
            results = [case]
            update_conversation_state(session_id, active_fir=fir, last_intent="CASE_INVESTIGATION", last_query_type="case_investigation")
            response = {
                "input_text": query_text,
                "generated_sql": lookup_query,
                "explanation": summary,
                "results": results,
                "result_count": 1,
                "query_type": "case_investigation",
                "case": case,
                "intelligence": intelligence,
                "investigation_workspace": build_investigation_workspace(case, intelligence),
                "connected_investigation": build_connected_investigation(app, case, intelligence),
                "explainability": build_explainability(
                    "case_investigation",
                    lookup_query,
                    intelligence=intelligence,
                    result_count=1,
                ),
            }
        except Exception as exc:
            response = {"input_text": query_text, "generated_sql": lookup_query, "explanation": "Case intelligence failed: " + str(exc), "results": [], "result_count": 0, "query_type": "case_investigation"}
        finalize_response(basicio, context, app, response, identity, session_id, query_text); return

    # --------------------------------------------------------
    # RECENT FIRs FAST PATH
    # --------------------------------------------------------
    if is_recent_firs_question(query_text):
        query = RECENT_FIRS_QUERY
        update_conversation_state(session_id, last_intent="RECENT_FIRS", last_query_type="case_search")
        try:
            rows = enrich_case_rows(app, execute_zcql(app, query))
            explanation = "Retrieved the most recently registered FIRs directly from the KSP CaseMaster table."
        except Exception as exc:
            rows = []
            explanation = "Recent FIR query failed: " + str(exc)
        update_conversation_state(
            session_id,
            active_case_ids=[x.get("CaseMasterID") for x in rows if x.get("CaseMasterID") is not None],
            last_intent="RECENT_FIRS",
            last_query_type="case_search",
        )
        save_memory(session_id, query_text, query)
        response = {
            "input_text": query_text,
            "generated_sql": query,
            "explanation": explanation,
            "results": rows,
            "result_count": len(rows),
            "query_type": "case_search",
            "explainability": build_explainability(
                "case_search", query, result_count=len(rows)
            ),
        }
        finalize_response(basicio, context, app, response, identity, session_id, query_text)
        return

    # --------------------------------------------------------
    # CONTEXTUAL HOTSPOT FOLLOW-UP
    # --------------------------------------------------------
    # Short hotspot drill-downs after an investigation stay inside the active
    # case context and never fall through to Gemini.
    if direct_intent.get("intent") == "CONTEXTUAL_HOTSPOT":
        state = get_conversation_state(session_id)
        try:
            analytics = build_contextual_hotspot_analytics(app, state)
            results = analytics.get("records") or []
            response = {
                "input_text": query_text,
                "generated_sql": "\n\n".join(analytics.get("source_queries", [])),
                "explanation": "Computed hotspot cells for the active investigation context directly from KSP CaseMaster coordinates without relying on Gemini.",
                "results": results,
                "result_count": len(results),
                "query_type": "analytics",
                "analytics": analytics,
                "contextual": True,
                "filter_mode": "contextual_deterministic",
                "explainability": build_explainability(
                    "analytics",
                    "\n\n".join(analytics.get("source_queries", [])),
                    analytics=analytics,
                    result_count=len(results),
                ),
            }
            update_conversation_state(
                session_id,
                last_intent="CONTEXTUAL_HOTSPOT",
                last_query_type="analytics",
                last_query_text=query_text,
            )
            finalize_response(basicio, context, app, response, identity, session_id, query_text, "completed")
            return
        except Exception as exc:
            print("CONTEXTUAL HOTSPOT FAILED:", exc)
            response = {
                "input_text": query_text,
                "generated_sql": "",
                "explanation": "Vaani could not compute the hotspot for the active investigation context.",
                "results": [],
                "result_count": 0,
                "query_type": "deterministic_error",
                "explainability": {
                    "source_tables": ["CaseMaster"],
                    "evidence_basis": "Contextual hotspot analysis failed before any language-engine fallback.",
                    "method": "Fail-closed contextual deterministic hotspot path.",
                    "records_considered": len(state.get("active_case_ids") or []),
                    "limitations": [str(exc)[:240]],
                    "generated_query_available": False,
                },
            }
            finalize_response(basicio, context, app, response, identity, session_id, query_text, "failed")
            return

    # --------------------------------------------------------
    # CONTEXTUAL INVESTIGATION GAPS
    # --------------------------------------------------------
    if direct_intent.get("intent") == "CONTEXTUAL_INVESTIGATION_GAPS":
        state = get_conversation_state(session_id)
        try:
            analytics = build_contextual_investigation_gaps(app, state)
            results = analytics.get("records") or []
            response = {
                "input_text": query_text,
                "generated_sql": "\n\n".join(analytics.get("source_queries", [])),
                "explanation": "Found investigation gaps for the active case context through deterministic CaseMasterID linkage; Gemini was not required.",
                "results": results,
                "result_count": len(results),
                "query_type": "analytics",
                "analytics": analytics,
                "contextual": True,
                "filter_mode": "contextual_deterministic",
                "explainability": build_explainability(
                    "analytics",
                    "\n\n".join(analytics.get("source_queries", [])),
                    analytics=analytics,
                    result_count=len(results),
                ),
            }
            update_conversation_state(session_id, last_intent="CONTEXTUAL_INVESTIGATION_GAPS", last_query_type="analytics", last_query_text=query_text)
            finalize_response(basicio, context, app, response, identity, session_id, query_text, "completed")
            return
        except Exception as exc:
            print("CONTEXTUAL INVESTIGATION GAPS FAILED:", exc)
            response = {
                "input_text": query_text,
                "generated_sql": "",
                "explanation": "Vaani could not compute the investigation gaps for the active case context.",
                "results": [],
                "result_count": 0,
                "query_type": "deterministic_error",
                "explainability": {
                    "source_tables": ["CaseMaster", "ChargesheetDetails", "CaseStatusMaster"],
                    "evidence_basis": "Contextual investigation-gap analysis failed before any language-engine fallback.",
                    "method": "Fail-closed contextual deterministic process analysis.",
                    "records_considered": len(state.get("active_case_ids") or []),
                    "limitations": [str(exc)[:240]],
                    "generated_query_available": False,
                },
            }
            finalize_response(basicio, context, app, response, identity, session_id, query_text, "failed")
            return

    # --------------------------------------------------------
    # INVESTIGATIVE NEXT ACTIONS
    # --------------------------------------------------------
    if direct_intent.get("intent") == "INVESTIGATIVE_NEXT_ACTION":
        state = get_conversation_state(session_id)
        try:
            analytics = build_investigative_next_actions(app, state)
            results = analytics.get("records") or []
            response = {
                "input_text": query_text,
                "generated_sql": "\n\n".join(analytics.get("source_queries", [])),
                "explanation": "Recommended next investigative actions from the active case evidence; no language-model inference was required.",
                "results": results,
                "result_count": len(results),
                "query_type": "analytics",
                "analytics": analytics,
                "contextual": True,
                "filter_mode": "contextual_deterministic",
                "explainability": build_explainability(
                    "analytics",
                    "\n\n".join(analytics.get("source_queries", [])),
                    analytics=analytics,
                    result_count=len(results),
                ),
            }
            update_conversation_state(session_id, last_intent="INVESTIGATIVE_NEXT_ACTION", last_query_type="analytics", last_query_text=query_text)
            finalize_response(basicio, context, app, response, identity, session_id, query_text, "completed")
            return
        except Exception as exc:
            print("INVESTIGATIVE NEXT ACTIONS FAILED:", exc)
            response = {
                "input_text": query_text,
                "generated_sql": "",
                "explanation": "Vaani could not determine evidence-backed next actions for the active investigation.",
                "results": [],
                "result_count": 0,
                "query_type": "deterministic_error",
                "explainability": {
                    "source_tables": ["CaseMaster", "Accused", "ChargesheetDetails", "ArrestSurrender", "ActSectionAssociation"],
                    "evidence_basis": "Existing deterministic case-intelligence leads could not be assembled.",
                    "method": "Fail-closed next-action guidance; no LLM fallback.",
                    "records_considered": len(state.get("active_case_ids") or []),
                    "limitations": [str(exc)[:240]],
                    "generated_query_available": False,
                },
            }
            finalize_response(basicio, context, app, response, identity, session_id, query_text, "failed")
            return

    # --------------------------------------------------------
    # ANALYTICS FAST PATH
    # --------------------------------------------------------
    # Must run before generic FIR filters so aggregation/count questions
    # cannot be mistaken for record retrieval.
    if direct_intent.get("intent") == "ANALYTICS":
        analytics_type = direct_intent.get("entities", {}).get("analytics_type")
        try:
            # A new global analytics question must not inherit stale FIR/person context.
            update_conversation_state(
                session_id,
                active_person=None,
                active_fir=None,
                active_case_ids=[],
                active_filters={},
                last_intent=(analytics_type or "analytics").upper(),
                last_query_type="analytics",
                last_query_text=query_text,
            )
            analytics = build_analytics(app, analytics_type)
            results = analytics.get("records") or []
            explanations = {
                "crime_type": "Computed crime-type distribution directly from the KSP Data Store without relying on Gemini.",
                "station": "Computed FIR distribution by police station directly from the KSP Data Store without relying on Gemini.",
                "case_status": "Computed case lifecycle distribution directly from CaseMaster and CaseStatusMaster without relying on Gemini.",
                "monthly_trend": "Computed monthly FIR trends directly from the KSP Data Store without relying on Gemini.",
                "monthly_peak": "Computed the highest-FIR month deterministically from the KSP Data Store without relying on Gemini.",
                "missing_chargesheet": "Found cases with no ChargesheetDetails record through deterministic CaseMasterID linkage.",
                "missing_arrest": "Found cases with no ArrestSurrender record through deterministic CaseMasterID linkage.",
                "missing_legal": "Found cases with no ActSectionAssociation record through deterministic CaseMasterID linkage.",
                "investigation_gaps": "Found under-investigation cases with no ChargesheetDetails record through deterministic linkage.",
                "chargesheet_cases": "Found cases with ChargesheetDetails records deterministically.",
                "arrest_cases": "Found cases with ArrestSurrender records deterministically.",
                "legal_cases": "Found cases with ActSectionAssociation records deterministically.",
                "process_overview": "Computed investigation-process coverage deterministically from KSP process tables.",
                "hotspot": "Computed spatial crime concentration cells directly from CaseMaster coordinates without relying on Gemini.",
                "early_warning": "Computed evidence-backed proactive crime signals directly from the KSP Data Store without relying on Gemini.",
                "accused_age": "Computed accused age distribution directly from the KSP Data Store without relying on Gemini.",
                "accused_gender": "Computed accused gender distribution directly from the KSP Data Store without relying on Gemini.",
                "accused_age_crime_type": "Computed the descriptive relationship between accused age groups and crime types directly from the KSP Data Store without relying on Gemini.",
            }
            response = {
                "input_text": query_text,
                "generated_sql": "\n\n".join(analytics.get("source_queries", [])),
                "explanation": explanations.get(analytics_type, "Computed crime analytics directly from the KSP Data Store."),
                "results": results,
                "result_count": len(results),
                "query_type": "analytics",
                "analytics": analytics,
                "explainability": build_explainability(
                    "analytics",
                    "\n\n".join(analytics.get("source_queries", [])),
                    analytics=analytics,
                    result_count=len(results),
                ),
            }
            finalize_response(basicio, context, app, response, identity, session_id, query_text)
            return
        except Exception as exc:
            print("ANALYTICS FAST PATH FAILED:", exc)
            response = {
                "input_text": query_text,
                "generated_sql": "",
                "explanation": "Crime analytics failed: " + str(exc),
                "results": [],
                "result_count": 0,
                "query_type": "analytics",
                "analytics": {
                    "chart_type": "bar",
                    "title": "Crime Analytics",
                    "labels": [],
                    "values": [],
                    "records": [],
                    "total": 0,
                },
                "explainability": {
                    "source_tables": [],
                    "evidence_basis": "Deterministic analytics execution failed.",
                    "method": "Fail-closed analytics path; no LLM fallback.",
                    "records_considered": 0,
                    "limitations": [str(exc)[:240]],
                    "generated_query_available": False,
                },
            }
            finalize_response(basicio, context, app, response, identity, session_id, query_text, "failed")
            return

    # --------------------------------------------------------
    # DETERMINISTIC COMMON FIR FILTERS
    # --------------------------------------------------------
    # Routine investigator filters should not depend on Gemini.
    deterministic_fir = build_deterministic_fir_search(app, query_text)
    if deterministic_fir:
        query, parsed_filters = deterministic_fir
        update_conversation_state(session_id, active_filters=parsed_filters, last_intent="FIR_SEARCH", last_query_type="case_search")
        try:
            rows = enrich_case_rows(app, execute_zcql(app, query))
            explanation = "Applied deterministic FIR filters directly against the KSP CaseMaster data."
            outcome = "completed"
        except Exception as exc:
            rows = []
            explanation = "Deterministic FIR search failed: " + str(exc)
            outcome = "failed"
        save_memory(session_id, query_text, query)
        response = {
            "input_text": query_text,
            "generated_sql": query,
            "explanation": explanation,
            "results": rows,
            "result_count": len(rows),
            "query_type": "case_search",
            "filter_mode": "deterministic",
            "filters": parsed_filters,
            "explainability": build_explainability(
                "case_search", query, result_count=len(rows)
            ),
        }
        finalize_response(basicio, context, app, response, identity, session_id, query_text, outcome)
        return

    # --------------------------------------------------------
    # CANONICAL INTENT RESOLUTION FOR CROSS-DIMENSION PATHS
    # --------------------------------------------------------
    # Resolve the canonical request before any cross-dimension dispatch.
    # The previous build referenced `canonical` before assigning it, which
    # caused a 500 for valid cross-intelligence queries.
    try:
        accused_rows_for_resolution = execute_zcql(app, ALL_ACCUSED_QUERY)
    except Exception:
        accused_rows_for_resolution = []

    update_conversation_state(session_id, last_query_text=query_text)
    canonical = classify_canonical_intent(
        query_text,
        get_conversation_state(session_id),
        accused_rows_for_resolution,
    )

    # --------------------------------------------------------
    # CROSS-DIMENSION INTELLIGENCE
    # --------------------------------------------------------
    if canonical["intent"] == "REPEAT_ACCUSED_HOTSPOT":
        try:
            analytics = build_repeat_accused_hotspot(app)
            response = {
                "input_text": query_text,
                "generated_sql": "\n\n".join(analytics["source_queries"]),
                "explanation": "Computed repeat-accused and hotspot overlap directly from KSP records without relying on Gemini.",
                "results": analytics["records"], "result_count": len(analytics["records"]),
                "query_type": "cross_intelligence", "analytics": analytics,
                "explainability": {
                    "source_tables": ["CaseMaster", "Accused", "CrimeSubHead", "Unit"],
                    "evidence_basis": analytics["method"],
                    "method": "Deterministic cross-dimension aggregation; Gemini was not required.",
                    "records_considered": len(analytics["records"]),
                    "records_label": "CROSS-DIMENSION SIGNALS",
                    "limitations": ["Spatial cells are approximate 0.01-degree cells.", "Shared activity does not establish culpability."],
                    "generated_query_available": True
                }
            }
            finalize_response(basicio, context, app, response, identity, session_id, query_text)
            return
        except Exception as exc:
            print("CROSS INTELLIGENCE FAILED:", exc)

    # --------------------------------------------------------
    # CRIME ANALYTICS FAST PATH
    # --------------------------------------------------------
    analytics_type = classify_sociological_question(query_text)

    if not analytics_type:
        analytics_type = classify_analytics_question(
            query_text
        )

    if analytics_type:
        try:
            update_conversation_state(session_id, last_intent=analytics_type.upper(), last_query_type="analytics")
            analytics = build_analytics(
                app,
                analytics_type
            )

            results = analytics["records"]

            explanations = {
                "crime_type":
                    "Computed crime-type distribution directly from the KSP Data Store without relying on Gemini.",
                "station":
                    "Computed FIR distribution by police station directly from the KSP Data Store without relying on Gemini.",
                "case_status":
                    "Computed case lifecycle distribution directly from CaseMaster and CaseStatusMaster without relying on Gemini.",
                "monthly_trend":
                    "Computed monthly FIR trends directly from the KSP Data Store without relying on Gemini.",
                "monthly_peak":
                    "Computed the highest-FIR month deterministically from the KSP Data Store without relying on Gemini.",
                "hotspot":
                    "Computed spatial crime concentration cells directly from CaseMaster coordinates without relying on Gemini.",
                "early_warning":
                    "Computed evidence-backed proactive crime signals directly from the KSP Data Store without relying on Gemini.",
                "accused_age":
                    "Computed accused age distribution directly from the KSP Data Store without relying on Gemini.",
                "accused_gender":
                    "Computed accused gender distribution directly from the KSP Data Store without relying on Gemini.",
                "accused_age_crime_type":
                    "Computed the descriptive relationship between accused age groups and crime types directly from the KSP Data Store without relying on Gemini.",
                "crime_type_across_stations":
                    "Computed crime-type recurrence across police stations directly from the KSP Data Store without relying on Gemini.",
                "station_crime_patterns":
                    "Computed recurring station-and-crime combinations directly from the KSP Data Store without relying on Gemini.",
                "person_crime_station":
                    "Computed accused links that recur across the same crime type in multiple police stations directly from the KSP Data Store.",
                "crime_location_recurrence":
                    "Computed recurring crime-type and spatial-cell combinations directly from the KSP Data Store without relying on Gemini."
            }

            response = {
                "input_text": query_text,
                "generated_sql": "\n\n".join(
                    analytics["source_queries"]
                ),
                "explanation": explanations.get(
                    analytics_type,
                    "Computed crime analytics directly from the KSP Data Store."
                ),
                "results": results,
                "result_count": len(results),
                "query_type": "analytics",
                "analytics": analytics,
                "explainability": build_explainability(
                    "analytics",
                    "\n\n".join(analytics["source_queries"]),
                    analytics=analytics,
                    result_count=len(results),
                ),
            }

        except Exception as exc:

            response = {
                "input_text": query_text,
                "generated_sql": "",
                "explanation":
                    "Crime analytics failed: "
                    + str(exc),
                "results": [],
                "result_count": 0,
                "query_type": "analytics",
                "analytics": {
                    "chart_type": (
                        "line" if analytics_type == "monthly_trend"
                        else "map" if analytics_type in {"hotspot", "hotspot_bengaluru"}
                        else "signals" if analytics_type == "early_warning"
                        else "station_pattern" if analytics_type == "station_crime_patterns"
                        else "person_crime_station" if analytics_type == "person_crime_station"
                        else "bar"
                    ),
                    "title": (
                        "Monthly FIR Trend" if analytics_type == "monthly_trend"
                        else "Crime Hotspot Cells" if analytics_type in {"hotspot", "hotspot_bengaluru"}
                        else "Proactive Crime Signals" if analytics_type == "early_warning"
                        else "Repeated Crime Patterns by Station" if analytics_type == "station_crime_patterns"
                        else "People Linked Across Crime Types and Stations" if analytics_type == "person_crime_station"
                        else "Crime Analytics"
                    ),
                    "labels": [],
                    "values": [],
                    "records": [],
                    "total": 0
                },
                "explainability": build_explainability(
                    "analytics",
                    "",
                    analytics={"title": "Crime Analytics", "chart_type": "bar"},
                    result_count=0,
                ),
            }

        finalize_response(
            basicio, context, app, response, identity, session_id, query_text
        )
        return

    # --------------------------------------------------------
    # ALL FIRs
    # --------------------------------------------------------
    if is_all_firs_question(query_text):
        query = ALL_FIRS_QUERY
        update_conversation_state(session_id, last_intent="ALL_FIRS", last_query_type="case_search")
        try:
            rows = enrich_case_rows(app, execute_zcql(app, query))
            update_conversation_state(
                session_id,
                active_case_ids=[x.get("CaseMasterID") for x in rows if x.get("CaseMasterID") is not None],
            )
            explanation = "Retrieved and enriched FIR records from the KSP CaseMaster table."
        except Exception as exc:
            rows = []; explanation = "CaseMaster query failed: " + str(exc)
        save_memory(session_id, query_text, query)
        response = {
            "input_text": query_text,
            "generated_sql": query,
            "explanation": explanation,
            "results": rows,
            "result_count": len(rows),
            "query_type": "case_search",
            "explainability": build_explainability(
                "case_search", query, result_count=len(rows)
            ),
        }
        finalize_response(basicio, context, app, response, identity, session_id, query_text); return

    # --------------------------------------------------------
    # GENERIC CANONICAL INTENT RESOLUTION
    # --------------------------------------------------------
    # `canonical` was resolved above for the cross-dimension dispatch and is
    # reused here so every request has exactly one canonical interpretation.

    # --------------------------------------------------------
    # PERSON-CASE HISTORY / NETWORK
    # --------------------------------------------------------
    if canonical["intent"] in {"PERSON_CASE_HISTORY", "PERSON_NETWORK"}:
        accused_query = ALL_ACCUSED_QUERY
        try:
            accused_rows = accused_rows_for_resolution
            case_index = load_case_index(app)
            target_name = canonical["entities"].get("person")

            if not target_name:
                results = []
                analysis = {"repeated_accused": [], "target_network": None, "graph": {"nodes": [], "edges": []}, "source_record_count": len(accused_rows)}
                explanation = "I could not resolve the person in this question from the available accused records."
            elif canonical["intent"] == "PERSON_CASE_HISTORY":
                history = build_person_case_history(accused_rows, case_index, target_name)
                if not history:
                    results = []
                    explanation = f"No accused record found for {target_name}."
                    analysis = {"repeated_accused": [], "target_network": None, "graph": {"nodes": [], "edges": []}, "source_record_count": len(accused_rows)}
                else:
                    results = history["cases"]
                    analysis = build_network_analysis(accused_rows, case_index, target_name)
                    analysis["source_record_count"] = len(accused_rows)
                    analysis["person_case_history"] = history
                    explanation = f"Found {history['person']['CaseCount']} case(s) involving {history['person']['AccusedName']}."
                    update_conversation_state(
                        session_id,
                        active_person=history["person"]["AccusedName"],
                        active_case_ids=[x["CaseMasterID"] for x in history["cases"]],
                        last_intent="PERSON_CASE_HISTORY",
                        last_query_type="criminal_network",
                    )
            else:
                analysis = build_network_analysis(accused_rows, case_index, target_name)
                analysis["source_record_count"] = len(accused_rows)
                if analysis["target_network"]:
                    results = analysis["target_network"]["connections"]
                    explanation = f"Found the relationship network for {target_name}."
                    update_conversation_state(
                        session_id,
                        active_person=analysis["target_network"]["target"]["AccusedName"],
                        active_case_ids=[x["CaseMasterID"] for x in analysis["target_network"]["target"]["Cases"]],
                        last_intent="PERSON_NETWORK",
                        last_query_type="criminal_network",
                    )
                else:
                    results = []
                    explanation = f"No accused record found for {target_name}."
        except Exception as exc:
            analysis = {"repeated_accused": [], "target_network": None, "graph": {"nodes": [], "edges": []}, "source_record_count": len(accused_rows_for_resolution)}
            results = []
            explanation = "Network analysis failed: " + str(exc)
        response = {
            "input_text": query_text,
            "generated_sql": accused_query,
            "explanation": explanation,
            "results": results,
            "result_count": len(results),
            "query_type": "criminal_network",
            "network": analysis,
            "explainability": {"source_tables": ["Accused", "CaseMaster"], "evidence_basis": "Shared CaseMasterID relationships between accused identities; PersonID is preferred and normalized name is a fallback.", "method": "Deterministic person-to-case-to-person relationship traversal.", "records_considered": analysis.get("source_record_count", len(accused_rows)), "records_label": "SOURCE ACCUSED RECORDS", "limitations": ["Relationship strength reflects shared case count, not a claim of criminal culpability or causation."], "generated_query_available": True},
        }
        finalize_response(basicio, context, app, response, identity, session_id, query_text); return

    # --------------------------------------------------------
    # GEMINI
    # --------------------------------------------------------
    memory = get_memory(session_id)
    generated_query = ask_gemini(query_text, memory)
    if not generated_query or generated_query.startswith("-- GEMINI"):
        is_transient = generated_query.startswith("-- GEMINI_TRANSIENT_ERROR")
        is_auth_error = generated_query.startswith("-- GEMINI_AUTH_ERROR")

        if is_auth_error:
            safe_explanation = (
                "Vaani's language engine credentials are currently unavailable. "
                "No database query was executed. Deterministic FIR, network, "
                "investigation, and analytics features remain available."
            )
        elif is_transient:
            safe_explanation = (
                "Vaani's language engine is temporarily unavailable. "
                "Please retry this open-ended query. "
                "Deterministic FIR, network, investigation, and analytics features remain available."
            )
        else:
            safe_explanation = (
                "Vaani could not translate this open-ended request. "
                "No database query was executed."
            )

        response = {
            "input_text": query_text,
            "generated_sql": "",
            "explanation": safe_explanation,
            "results": [],
            "result_count": 0,
            "query_type": "gemini_unavailable" if is_transient else "gemini_error",
            "explainability": {
                "source_tables": [],
                "evidence_basis": (
                    "Gemini credentials were unavailable; no generated query was executed."
                    if is_auth_error
                    else "Gemini was temporarily unavailable; no generated query was executed."
                    if is_transient
                    else "Gemini query generation failed; no generated query was executed."
                ),
                "method": "Bounded Gemini retry policy for open-ended requests.",
                "records_considered": 0,
                "limitations": [
                    "This request could not be translated to ZCQL during the current attempt."
                ],
                "generated_query_available": False,
            },
        }
        finalize_response(basicio, context, app, response, identity, session_id, query_text, "failed")
        return
    query = generated_query.strip().replace("```sql", "").replace("```", "").rstrip(";").strip()
    if not re.match(r"^SELECT\s", query, flags=re.IGNORECASE):
        response = {
            "input_text": query_text,
            "generated_sql": "",
            "explanation": "Vaani rejected an invalid language-engine query before database execution.",
            "results": [],
            "result_count": 0,
            "query_type": "rejected",
            "explainability": {
                "source_tables": [],
                "evidence_basis": "The language engine did not return a valid SELECT statement.",
                "method": "Fail-closed query validation.",
                "records_considered": 0,
                "limitations": ["No database query was executed."],
                "generated_query_available": False,
            },
        }
        finalize_response(basicio, context, app, response, identity, session_id, query_text, "failed")
        return
    if not is_safe_query(query):
        response = {
            "input_text": query_text,
            "generated_sql": query,
            "explanation": "The generated query was rejected because it violates the ZCQL safety rules.",
            "results": [],
            "result_count": 0,
            "query_type": "rejected",
            "explainability": build_explainability("gemini_zcql", query, result_count=0),
        }
        finalize_response(basicio, context, app, response, identity, session_id, query_text); return
    try:
        rows = execute_zcql(app, query)
        if any("CaseMasterID" in r for r in rows):
            rows = enrich_case_rows(app, rows)
        explanation = "Interpreted your question and executed a ZCQL query against the KSP Data Store."
        save_memory(session_id, query_text, query)
    except Exception as exc:
        rows = []; explanation = "ZCQL execution failed: " + str(exc)
    response = {
        "input_text": query_text,
        "generated_sql": query,
        "explanation": explanation,
        "results": rows,
        "result_count": len(rows),
        "query_type": "gemini_zcql",
        "explainability": build_explainability(
            "gemini_zcql", query, result_count=len(rows)
        ),
    }
    finalize_response(basicio, context, app, response, identity, session_id, query_text)