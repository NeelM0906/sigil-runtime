"""
Split Test Framework for Webinar Marketing Machine
===================================================
A/B testing infrastructure for landing pages, email sequences,
ad creative, webinar titles, and registration flows.

Zone Actions #62-67 Implementation
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List, Any, Callable
from datetime import datetime, timedelta
import random
import hashlib
import json
import uuid


# =============================================================================
# ENUMS & CONFIGURATION
# =============================================================================

class Company(Enum):
    ACT_I = "act-i"
    UNBLINDED = "unblinded"
    CALLAGY_RECOVERY = "callagy-recovery"


class TestType(Enum):
    LANDING_PAGE = "landing_page"
    EMAIL_SEQUENCE = "email_sequence"
    AD_CREATIVE = "ad_creative"
    WEBINAR_TITLE = "webinar_title"
    REGISTRATION_FLOW = "registration_flow"
    OFFER_STACK = "offer_stack"
    PRICING = "pricing"


class MetricType(Enum):
    # Top of funnel
    CLICK_THROUGH_RATE = "ctr"
    REGISTRATION_RATE = "registration_rate"
    COST_PER_REGISTRATION = "cpr"
    
    # Middle of funnel
    SHOW_UP_RATE = "show_up_rate"
    WATCH_TIME_PERCENT = "watch_time_pct"
    ENGAGEMENT_SCORE = "engagement_score"
    
    # Bottom of funnel (CONVERSION FOCUS)
    OFFER_CLICK_RATE = "offer_click_rate"
    APPLICATION_RATE = "application_rate"
    CLOSE_RATE = "close_rate"
    REVENUE_PER_REGISTRANT = "rpr"
    LIFETIME_VALUE = "ltv"
    
    # Composite
    CONVERSION_VALUE = "conversion_value"


class SignificanceLevel(Enum):
    LOW = 0.10      # 90% confidence
    MEDIUM = 0.05   # 95% confidence
    HIGH = 0.01     # 99% confidence


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class Variant:
    """A single variant in a split test."""
    id: str
    name: str
    description: str
    content: Dict[str, Any]
    weight: float = 0.5  # Traffic allocation
    is_control: bool = False
    
    # Metrics tracking
    impressions: int = 0
    registrations: int = 0
    show_ups: int = 0
    conversions: int = 0
    revenue: float = 0.0
    
    def add_impression(self):
        self.impressions += 1
    
    def add_registration(self):
        self.registrations += 1
    
    def add_show_up(self):
        self.show_ups += 1
    
    def add_conversion(self, revenue: float = 0.0):
        self.conversions += 1
        self.revenue += revenue
    
    @property
    def registration_rate(self) -> float:
        return self.registrations / self.impressions if self.impressions > 0 else 0.0
    
    @property
    def show_up_rate(self) -> float:
        return self.show_ups / self.registrations if self.registrations > 0 else 0.0
    
    @property
    def conversion_rate(self) -> float:
        return self.conversions / self.show_ups if self.show_ups > 0 else 0.0
    
    @property
    def revenue_per_registrant(self) -> float:
        return self.revenue / self.registrations if self.registrations > 0 else 0.0


@dataclass
class SplitTest:
    """A complete split test configuration."""
    id: str
    name: str
    company: Company
    test_type: TestType
    variants: List[Variant]
    primary_metric: MetricType
    secondary_metrics: List[MetricType] = field(default_factory=list)
    
    # Test configuration
    min_sample_size: int = 100
    significance_level: SignificanceLevel = SignificanceLevel.MEDIUM
    
    # Status
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    winner: Optional[str] = None
    
    def assign_variant(self, user_id: str) -> Variant:
        """
        Deterministically assign a user to a variant.
        Uses consistent hashing so same user always sees same variant.
        """
        # Create deterministic hash from test_id + user_id
        hash_input = f"{self.id}:{user_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        normalized = (hash_value % 10000) / 10000  # 0.0 to 1.0
        
        # Walk through variants by weight
        cumulative = 0.0
        for variant in self.variants:
            cumulative += variant.weight
            if normalized < cumulative:
                variant.add_impression()
                return variant
        
        # Fallback to last variant
        self.variants[-1].add_impression()
        return self.variants[-1]
    
    def get_results(self) -> Dict[str, Any]:
        """Get current test results."""
        results = {
            "test_id": self.id,
            "test_name": self.name,
            "primary_metric": self.primary_metric.value,
            "variants": [],
            "winner": self.winner,
            "is_significant": False,
            "sample_size_reached": False
        }
        
        total_samples = sum(v.impressions for v in self.variants)
        results["sample_size_reached"] = total_samples >= self.min_sample_size * len(self.variants)
        
        for variant in self.variants:
            variant_data = {
                "id": variant.id,
                "name": variant.name,
                "is_control": variant.is_control,
                "impressions": variant.impressions,
                "registrations": variant.registrations,
                "show_ups": variant.show_ups,
                "conversions": variant.conversions,
                "revenue": variant.revenue,
                "registration_rate": variant.registration_rate,
                "show_up_rate": variant.show_up_rate,
                "conversion_rate": variant.conversion_rate,
                "revenue_per_registrant": variant.revenue_per_registrant
            }
            results["variants"].append(variant_data)
        
        # Simple significance check (would use proper stats in production)
        if results["sample_size_reached"] and len(self.variants) == 2:
            v1, v2 = self.variants
            if self.primary_metric == MetricType.REGISTRATION_RATE:
                diff = abs(v1.registration_rate - v2.registration_rate)
                results["is_significant"] = diff > 0.05  # Simplified
            elif self.primary_metric == MetricType.REVENUE_PER_REGISTRANT:
                if v1.revenue_per_registrant > 0:
                    diff = abs(v1.revenue_per_registrant - v2.revenue_per_registrant) / v1.revenue_per_registrant
                    results["is_significant"] = diff > 0.10
        
        return results


@dataclass
class RegistrationFlow:
    """Configuration for a registration flow variant."""
    id: str
    name: str
    steps: List[Dict[str, Any]]
    
    # Flow options
    ask_phone: bool = True
    ask_company: bool = True
    show_social_proof: bool = True
    show_countdown: bool = True
    show_bonus_preview: bool = True


@dataclass
class EmailSequenceVariant:
    """A variant of an email sequence."""
    id: str
    name: str
    emails: List[Dict[str, Any]]
    
    # Sequence options
    send_times: List[str]  # ISO format times
    personalization_level: str = "high"  # low, medium, high
    urgency_tone: str = "medium"  # low, medium, high, aggressive


# =============================================================================
# TEST FACTORIES
# =============================================================================

class TestFactory:
    """Factory for creating pre-configured split tests."""
    
    @staticmethod
    def create_landing_page_test(
        company: Company,
        name: str,
        headlines: List[str],
        subheadlines: List[str],
        ctas: List[str]
    ) -> SplitTest:
        """Create a landing page split test."""
        variants = []
        
        # Generate variants from combinations (simplified: just headline variants)
        for i, headline in enumerate(headlines):
            variant = Variant(
                id=f"lp-{company.value}-{i}",
                name=f"Headline Variant {chr(65+i)}",  # A, B, C...
                description=headline[:50] + "...",
                content={
                    "headline": headline,
                    "subheadline": subheadlines[i % len(subheadlines)],
                    "cta": ctas[i % len(ctas)]
                },
                weight=1.0 / len(headlines),
                is_control=(i == 0)
            )
            variants.append(variant)
        
        return SplitTest(
            id=f"test-lp-{company.value}-{uuid.uuid4().hex[:8]}",
            name=name,
            company=company,
            test_type=TestType.LANDING_PAGE,
            variants=variants,
            primary_metric=MetricType.REGISTRATION_RATE,
            secondary_metrics=[MetricType.REVENUE_PER_REGISTRANT]
        )
    
    @staticmethod
    def create_webinar_title_test(
        company: Company,
        titles: List[str]
    ) -> SplitTest:
        """Create a webinar title split test."""
        variants = [
            Variant(
                id=f"title-{company.value}-{i}",
                name=f"Title {chr(65+i)}",
                description=title[:60],
                content={"title": title},
                weight=1.0 / len(titles),
                is_control=(i == 0)
            )
            for i, title in enumerate(titles)
        ]
        
        return SplitTest(
            id=f"test-title-{company.value}-{uuid.uuid4().hex[:8]}",
            name=f"{company.value} Webinar Title Test",
            company=company,
            test_type=TestType.WEBINAR_TITLE,
            variants=variants,
            primary_metric=MetricType.REGISTRATION_RATE,
            secondary_metrics=[MetricType.SHOW_UP_RATE, MetricType.REVENUE_PER_REGISTRANT]
        )
    
    @staticmethod
    def create_email_sequence_test(
        company: Company,
        sequence_variants: List[EmailSequenceVariant]
    ) -> SplitTest:
        """Create an email sequence split test."""
        variants = [
            Variant(
                id=seq.id,
                name=seq.name,
                description=f"{len(seq.emails)} emails, {seq.urgency_tone} urgency",
                content={
                    "emails": seq.emails,
                    "send_times": seq.send_times,
                    "personalization": seq.personalization_level,
                    "urgency": seq.urgency_tone
                },
                weight=1.0 / len(sequence_variants),
                is_control=(i == 0)
            )
            for i, seq in enumerate(sequence_variants)
        ]
        
        return SplitTest(
            id=f"test-email-{company.value}-{uuid.uuid4().hex[:8]}",
            name=f"{company.value} Email Sequence Test",
            company=company,
            test_type=TestType.EMAIL_SEQUENCE,
            variants=variants,
            primary_metric=MetricType.SHOW_UP_RATE,
            secondary_metrics=[MetricType.REGISTRATION_RATE, MetricType.CONVERSION_VALUE]
        )


# =============================================================================
# PRE-CONFIGURED TESTS FOR EACH COMPANY
# =============================================================================

def create_act_i_tests() -> List[SplitTest]:
    """Create all split tests for ACT-I webinar."""
    tests = []
    
    # Landing Page Test
    tests.append(TestFactory.create_landing_page_test(
        company=Company.ACT_I,
        name="ACT-I Landing Page Headlines",
        headlines=[
            "How AI is Winning Cases Other Lawyers Lose",
            "The AI Advantage: How Smart Firms Are 10X-ing Case Outcomes",
            "Case Study: $42M Verdict Using AI-Powered Trial Prep"
        ],
        subheadlines=[
            "Join the free webinar revealing the exact AI tools used in landmark victories",
            "Discover the legal AI revolution before your competitors do",
            "See the step-by-step process that's changing litigation forever"
        ],
        ctas=[
            "Reserve My Seat",
            "Watch the Free Training",
            "Get Instant Access"
        ]
    ))
    
    # Webinar Title Test
    tests.append(TestFactory.create_webinar_title_test(
        company=Company.ACT_I,
        titles=[
            "The AI Advantage: How Smart Firms Are 10X-ing Case Outcomes",
            "Case Study: $42M Verdict Using AI-Powered Trial Prep",
            "Why 87% of Attorneys Will Be Obsolete in 5 Years (Unless...)"
        ]
    ))
    
    return tests


def create_unblinded_tests() -> List[SplitTest]:
    """Create all split tests for Unblinded webinar."""
    tests = []
    
    # Landing Page Test
    tests.append(TestFactory.create_landing_page_test(
        company=Company.UNBLINDED,
        name="Unblinded Landing Page Headlines",
        headlines=[
            "See What's Really Holding You Back",
            "The Unblinded Method: Why Top Performers Stay Stuck",
            "3 Invisible Barriers Destroying Your Potential"
        ],
        subheadlines=[
            "A breakthrough assessment that reveals your hidden blind spots",
            "The same method used by 500+ executives to shatter their ceilings",
            "Take the live assessment and discover what's been invisible to you"
        ],
        ctas=[
            "Start My Assessment",
            "Join the Free Workshop",
            "Reveal My Blind Spots"
        ]
    ))
    
    # Webinar Title Test
    tests.append(TestFactory.create_webinar_title_test(
        company=Company.UNBLINDED,
        titles=[
            "The Unblinded Method: Why Top Performers Stay Stuck",
            "3 Invisible Barriers Destroying Your Potential (Live Assessment)",
            "From Burnout to Breakthrough: The Unblinded Protocol"
        ]
    ))
    
    return tests


def create_callagy_recovery_tests() -> List[SplitTest]:
    """Create all split tests for Callagy Recovery webinar."""
    tests = []
    
    # Landing Page Test
    tests.append(TestFactory.create_landing_page_test(
        company=Company.CALLAGY_RECOVERY,
        name="Callagy Recovery Landing Page Headlines",
        headlines=[
            "Double Your Practice Revenue Without More Patients",
            "The $2.3M Secret: How One PT Clinic Doubled Revenue in 90 Days",
            "Stop Leaving Money on the Table: Insurance Billing Mastery"
        ],
        subheadlines=[
            "Discover the revenue leaks draining your practice profits",
            "The exact system used by 200+ clinics to unlock hidden revenue",
            "A free audit framework that typically finds $50K+ in lost revenue"
        ],
        ctas=[
            "Audit My Practice Revenue",
            "Show Me the System",
            "Find My Hidden Revenue"
        ]
    ))
    
    # Webinar Title Test
    tests.append(TestFactory.create_webinar_title_test(
        company=Company.CALLAGY_RECOVERY,
        titles=[
            "The $2.3M Secret: How One PT Clinic Doubled Revenue in 90 Days",
            "Insurance Billing Mastery: Stop Leaving Money on the Table",
            "The Callagy Recovery System: Predictable Practice Growth"
        ]
    ))
    
    return tests


# =============================================================================
# SPLIT TEST MANAGER
# =============================================================================

class SplitTestManager:
    """Central manager for all split tests."""
    
    def __init__(self):
        self.tests: Dict[str, SplitTest] = {}
        self.user_assignments: Dict[str, Dict[str, str]] = {}  # user_id -> {test_id: variant_id}
    
    def add_test(self, test: SplitTest):
        """Add a test to the manager."""
        self.tests[test.id] = test
    
    def get_test(self, test_id: str) -> Optional[SplitTest]:
        """Get a test by ID."""
        return self.tests.get(test_id)
    
    def get_tests_by_company(self, company: Company) -> List[SplitTest]:
        """Get all tests for a specific company."""
        return [t for t in self.tests.values() if t.company == company]
    
    def get_tests_by_type(self, test_type: TestType) -> List[SplitTest]:
        """Get all tests of a specific type."""
        return [t for t in self.tests.values() if t.test_type == test_type]
    
    def assign_user_to_tests(self, user_id: str, company: Company) -> Dict[str, Variant]:
        """Assign a user to all active tests for a company."""
        assignments = {}
        company_tests = [t for t in self.get_tests_by_company(company) if t.is_active]
        
        for test in company_tests:
            variant = test.assign_variant(user_id)
            assignments[test.id] = variant
            
            # Store assignment
            if user_id not in self.user_assignments:
                self.user_assignments[user_id] = {}
            self.user_assignments[user_id][test.id] = variant.id
        
        return assignments
    
    def record_conversion(self, user_id: str, revenue: float = 0.0):
        """Record a conversion for a user across all their assigned tests."""
        if user_id not in self.user_assignments:
            return
        
        for test_id, variant_id in self.user_assignments[user_id].items():
            test = self.tests.get(test_id)
            if test:
                for variant in test.variants:
                    if variant.id == variant_id:
                        variant.add_conversion(revenue)
                        break
    
    def get_all_results(self) -> Dict[str, Any]:
        """Get results for all tests."""
        return {
            "generated_at": datetime.now().isoformat(),
            "total_tests": len(self.tests),
            "active_tests": len([t for t in self.tests.values() if t.is_active]),
            "tests": [test.get_results() for test in self.tests.values()]
        }
    
    def export_results(self, filepath: str):
        """Export results to JSON file."""
        results = self.get_all_results()
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)


# =============================================================================
# CONVERSION TRACKING
# =============================================================================

@dataclass
class ConversionEvent:
    """A conversion event to track."""
    id: str
    user_id: str
    event_type: str
    revenue: float
    timestamp: datetime
    metadata: Dict[str, Any]
    test_assignments: Dict[str, str]  # test_id -> variant_id


class ConversionTracker:
    """Track and analyze conversions."""
    
    def __init__(self, manager: SplitTestManager):
        self.manager = manager
        self.events: List[ConversionEvent] = []
    
    def track_registration(self, user_id: str, company: Company, source: str = "organic"):
        """Track a registration event."""
        # Get user's test assignments
        assignments = self.manager.assign_user_to_tests(user_id, company)
        
        # Record registration on each variant
        for variant in assignments.values():
            variant.add_registration()
        
        event = ConversionEvent(
            id=str(uuid.uuid4()),
            user_id=user_id,
            event_type="registration",
            revenue=0.0,
            timestamp=datetime.now(),
            metadata={"company": company.value, "source": source},
            test_assignments={t: v.id for t, v in assignments.items()}
        )
        self.events.append(event)
        return event
    
    def track_show_up(self, user_id: str):
        """Track a webinar attendance event."""
        if user_id not in self.manager.user_assignments:
            return None
        
        for test_id, variant_id in self.manager.user_assignments[user_id].items():
            test = self.manager.get_test(test_id)
            if test:
                for variant in test.variants:
                    if variant.id == variant_id:
                        variant.add_show_up()
                        break
        
        event = ConversionEvent(
            id=str(uuid.uuid4()),
            user_id=user_id,
            event_type="show_up",
            revenue=0.0,
            timestamp=datetime.now(),
            metadata={},
            test_assignments=self.manager.user_assignments.get(user_id, {})
        )
        self.events.append(event)
        return event
    
    def track_purchase(self, user_id: str, revenue: float, product: str):
        """Track a purchase conversion."""
        self.manager.record_conversion(user_id, revenue)
        
        event = ConversionEvent(
            id=str(uuid.uuid4()),
            user_id=user_id,
            event_type="purchase",
            revenue=revenue,
            timestamp=datetime.now(),
            metadata={"product": product},
            test_assignments=self.manager.user_assignments.get(user_id, {})
        )
        self.events.append(event)
        return event
    
    def get_funnel_metrics(self, company: Company) -> Dict[str, Any]:
        """Get funnel metrics for a company."""
        company_events = [e for e in self.events if e.metadata.get("company") == company.value]
        
        registrations = len([e for e in company_events if e.event_type == "registration"])
        show_ups = len([e for e in self.events if e.event_type == "show_up"])
        purchases = len([e for e in self.events if e.event_type == "purchase"])
        total_revenue = sum(e.revenue for e in self.events if e.event_type == "purchase")
        
        return {
            "company": company.value,
            "registrations": registrations,
            "show_ups": show_ups,
            "purchases": purchases,
            "total_revenue": total_revenue,
            "show_up_rate": show_ups / registrations if registrations > 0 else 0,
            "conversion_rate": purchases / show_ups if show_ups > 0 else 0,
            "revenue_per_registrant": total_revenue / registrations if registrations > 0 else 0
        }


# =============================================================================
# MAIN INITIALIZATION
# =============================================================================

def initialize_webinar_tests() -> SplitTestManager:
    """Initialize all webinar split tests."""
    manager = SplitTestManager()
    
    # Add ACT-I tests
    for test in create_act_i_tests():
        manager.add_test(test)
    
    # Add Unblinded tests
    for test in create_unblinded_tests():
        manager.add_test(test)
    
    # Add Callagy Recovery tests
    for test in create_callagy_recovery_tests():
        manager.add_test(test)
    
    return manager


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Initialize the test manager
    manager = initialize_webinar_tests()
    tracker = ConversionTracker(manager)
    
    print("=" * 60)
    print("WEBINAR SPLIT TEST FRAMEWORK")
    print("=" * 60)
    print(f"\nTotal tests configured: {len(manager.tests)}")
    
    for company in Company:
        tests = manager.get_tests_by_company(company)
        print(f"\n{company.value.upper()}:")
        for test in tests:
            print(f"  - {test.name}")
            for variant in test.variants:
                print(f"    • {variant.name}: {variant.description}")
    
    # Simulate some traffic
    print("\n" + "=" * 60)
    print("SIMULATING TRAFFIC...")
    print("=" * 60)
    
    import random
    random.seed(42)
    
    for i in range(100):
        user_id = f"user_{i:04d}"
        company = random.choice(list(Company))
        
        # Register
        tracker.track_registration(user_id, company, source="facebook_ad")
        
        # Some show up (40%)
        if random.random() < 0.4:
            tracker.track_show_up(user_id)
            
            # Some convert (20% of attendees)
            if random.random() < 0.2:
                revenue = random.uniform(2000, 25000)
                tracker.track_purchase(user_id, revenue, f"{company.value}_program")
    
    # Print results
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    
    results = manager.get_all_results()
    for test_result in results["tests"]:
        print(f"\n{test_result['test_name']}:")
        print(f"  Primary Metric: {test_result['primary_metric']}")
        for v in test_result["variants"]:
            print(f"  {v['name']}: {v['impressions']} impr, {v['registration_rate']:.1%} reg, "
                  f"${v['revenue_per_registrant']:.2f} RPR")
    
    # Funnel metrics
    print("\n" + "=" * 60)
    print("FUNNEL METRICS BY COMPANY")
    print("=" * 60)
    
    for company in Company:
        metrics = tracker.get_funnel_metrics(company)
        print(f"\n{company.value.upper()}:")
        print(f"  Registrations: {metrics['registrations']}")
        print(f"  Show-up Rate: {metrics['show_up_rate']:.1%}")
        print(f"  Conversion Rate: {metrics['conversion_rate']:.1%}")
        print(f"  Revenue/Registrant: ${metrics['revenue_per_registrant']:.2f}")
