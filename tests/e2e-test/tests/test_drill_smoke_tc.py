"""
KM Generic Drill-down Smoke Test Module (Stage B).

Covers the high-value drill workflow:
1. Click a Trending Topics row -> drawer opens at L1 with time trend chart
2. Click a time bucket bar -> L2 call list visible
3. Click the first call row -> L3 transcript visible
4. URL hash contains the drill stack (sharable)
5. Esc x3 closes the drawer entirely

Mirrors the Page Object pattern used by test_telecom_smoke_tc.py.
"""
import logging

from pages.HomePage import HomePage
from pages.DrillPage import DrillPage
from pages.KMGenericPage import KMGenericPage

logger = logging.getLogger(__name__)


def test_drill_topic_trend_to_transcript(login_logout, request):
    """KM Generic Drill-down Smoke Test:
    1. Open KM Generic URL
    2. Click a Trending Topics row -> drawer opens at L1
    3. Validate breadcrumb shows the topic and bucket toggle is visible
    4. Click the first bar in the trend chart -> L2 call list visible
    5. Click the first call row -> L3 transcript visible
    6. URL hash contains the drill stack
    7. Press Esc 3 times -> drawer fully closed
    """
    request.node._nodeid = (
        "DRILL-01 - KM Generic - Telecom - "
        "Validate drill from Trending Topics row -> trend -> calls -> transcript"
    )

    page = login_logout
    km_page = KMGenericPage(page)
    drill_page = DrillPage(page)

    logger.info("Step 1: Open KM Generic URL")
    km_page.open_url()
    km_page.validate_dashboard_ui()

    logger.info("Step 2: Click a Trending Topics row to open the drill drawer")
    topic = drill_page.open_via_trending_topic_row(index=0)
    logger.info(f"Drilled into topic: {topic!r}")

    logger.info("Step 3: Validate drawer + breadcrumb + bucket toggle")
    drill_page.assert_drawer_open()
    drill_page.assert_breadcrumb_contains("topic:")
    drill_page.assert_breadcrumb_contains(topic)

    logger.info("Step 4: Click the first bucket bar -> L2 call list")
    drill_page.drill_into_first_time_bucket()

    logger.info("Step 5: Click the first call row -> L3 transcript")
    drill_page.drill_into_first_call()

    logger.info("Step 6: URL hash should contain the drill stack")
    drill_page.assert_url_has_drill_hash()

    logger.info("Step 7: Esc x3 closes the drawer")
    drill_page.press_escape(times=3)
    drill_page.assert_drawer_closed()
    drill_page.assert_url_has_no_drill_hash()


def test_drill_bucket_toggle_and_close_button(login_logout, request):
    """KM Generic Drill-down Smoke Test:
    1. Open KM Generic URL
    2. Drill via Trending Topics row
    3. Switch bucket from Week to Day and back
    4. Close via the X button -> drawer closed, no drill hash in URL
    """
    request.node._nodeid = (
        "DRILL-02 - KM Generic - Telecom - "
        "Validate drill bucket toggle and explicit close button"
    )

    page = login_logout
    km_page = KMGenericPage(page)
    drill_page = DrillPage(page)

    logger.info("Step 1: Open KM Generic URL")
    km_page.open_url()

    logger.info("Step 2: Drill via Trending Topics row")
    drill_page.open_via_trending_topic_row(index=0)
    drill_page.assert_drawer_open()

    logger.info("Step 3: Toggle Day bucket then back to Week")
    drill_page.select_day_bucket()
    drill_page.select_week_bucket()

    logger.info("Step 4: Close via the X button")
    drill_page.click_close()
    drill_page.assert_drawer_closed()
    drill_page.assert_url_has_no_drill_hash()
