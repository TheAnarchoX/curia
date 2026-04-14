"""Domain enumerations for the Curia political intelligence platform."""

from enum import StrEnum


class JurisdictionLevel(StrEnum):
    """Administrative level of a jurisdiction."""

    MUNICIPALITY = "municipality"
    PROVINCE = "province"
    NATIONAL = "national"
    WATER_AUTHORITY = "water_authority"
    OTHER = "other"


class InstitutionType(StrEnum):
    """Type of political institution."""

    COUNCIL = "council"
    COMMITTEE = "committee"
    CHAMBER = "chamber"
    SENATE = "senate"
    EXECUTIVE = "executive"
    OTHER = "other"


class GoverningBodyType(StrEnum):
    """Type of governing body within an institution."""

    COUNCIL = "council"
    COMMITTEE = "committee"
    SUBCOMMITTEE = "subcommittee"
    PLENARY = "plenary"
    OTHER = "other"


class MeetingStatus(StrEnum):
    """Lifecycle status of a meeting."""

    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    POSTPONED = "postponed"


class DocumentType(StrEnum):
    """Classification of a document."""

    MOTION = "motion"
    AMENDMENT = "amendment"
    QUESTION = "question"
    ANSWER = "answer"
    REPORT = "report"
    MINUTES = "minutes"
    POLICY_DOCUMENT = "policy_document"
    ATTACHMENT = "attachment"
    BILL = "bill"
    OTHER = "other"


class BillType(StrEnum):
    """Classification of a legislative bill."""

    GOVERNMENT = "government"
    PRIVATE_MEMBER = "private_member"
    BUDGET = "budget"
    TREATY_APPROVAL = "treaty_approval"
    CONSTITUTIONAL = "constitutional"
    OTHER = "other"


class BillStatus(StrEnum):
    """Lifecycle status of a legislative bill."""

    INTRODUCED = "introduced"
    COMMITTEE = "committee"
    PLENARY = "plenary"
    ADOPTED = "adopted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    ENACTED = "enacted"
    OTHER = "other"


class ElectionType(StrEnum):
    """Type of election event."""

    PARLIAMENTARY = "parliamentary"
    SENATE = "senate"
    PROVINCIAL = "provincial"
    MUNICIPAL = "municipal"
    WATER_AUTHORITY = "water_authority"
    EUROPEAN = "european"
    REFERENDUM = "referendum"
    OTHER = "other"


class PropositionStatus(StrEnum):
    """Status of a proposition (motion, amendment, question, promise)."""

    SUBMITTED = "submitted"
    DEBATED = "debated"
    ADOPTED = "adopted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    PENDING = "pending"
    OTHER = "other"


class VoteOutcome(StrEnum):
    """Outcome of a vote."""

    ADOPTED = "adopted"
    REJECTED = "rejected"
    TIED = "tied"
    NOT_VOTED = "not_voted"


class DecisionType(StrEnum):
    """Mechanism by which a decision was made."""

    VOTE = "vote"
    CONSENSUS = "consensus"
    PROCEDURAL = "procedural"
    OTHER = "other"


class ExtractionStatus(StrEnum):
    """Status of an extraction run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class IdentityMatchType(StrEnum):
    """Method used to match two identity candidates."""

    EXACT = "exact"
    NORMALIZED = "normalized"
    FUZZY = "fuzzy"
    MANUAL = "manual"
    REJECTED = "rejected"


class IdentityReviewStatus(StrEnum):
    """Review status of an identity resolution candidate."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class MetricValueType(StrEnum):
    """Data type of a metric value."""

    COUNT = "count"
    RATE = "rate"
    PERCENTAGE = "percentage"
    DURATION_SECONDS = "duration_seconds"
    SCORE = "score"
    INDEX = "index"


class MetricTimeGrain(StrEnum):
    """Temporal granularity for metric aggregation."""

    SESSION = "session"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    TERM = "term"
    ALL_TIME = "all_time"


class SourceType(StrEnum):
    """Type of external data source."""

    IBABS = "ibabs"
    DEBAT_DIRECT = "debat_direct"
    TWEEDE_KAMER_OPEN_DATA = "tweede_kamer_open_data"
    OTHER = "other"


class MandateRole(StrEnum):
    """Role held by a politician within a governing body."""

    MEMBER = "member"
    CHAIR = "chair"
    VICE_CHAIR = "vice_chair"
    SECRETARY = "secretary"
    ALDERMAN = "alderman"
    MAYOR = "mayor"
    MINISTER = "minister"
    STATE_SECRETARY = "state_secretary"
    COMMISSIONER = "commissioner"
    OTHER = "other"
