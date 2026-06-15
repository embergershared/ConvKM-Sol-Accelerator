"""
DrillPage Module
Page Object for the dashboard drill-down drawer (Stage B).
See plans/dashboard-drill-down.md for behavior reference.
"""
from base.base import BasePage
from playwright.sync_api import expect
import logging
import re

logger = logging.getLogger(__name__)


class DrillPage(BasePage):
    """Page Object for the drill drawer that appears on top of the dashboard."""

    # --- Dashboard chart marks (drill triggers) ---
    # The Trending Topics table renders rows whose first cell holds the topic
    # name. Click any row to drill into that topic.
    TRENDING_TOPIC_ROWS = (
        "div.tableContainer table tbody tr[role='button'], "
        "div.tableContainer table tbody tr"
    )

    # --- Drawer chrome ---
    DRAWER = "div[role='dialog']"
    BREADCRUMB = f"{DRAWER} nav[aria-label='breadcrumb'], {DRAWER} ol"
    BREADCRUMB_BUTTON = f"{DRAWER} button[role='link'], {DRAWER} nav button"
    BACK_BUTTON = f"{DRAWER} button[aria-label='Back']"
    CLOSE_BUTTON = f"{DRAWER} button[aria-label='Close drill']"
    RESIZE_HANDLE = f"{DRAWER} div.drill-resize-handle"
    RESET_LINK = f"{DRAWER} button:has-text('Reset drill')"
    AI_DISCLAIMER = f"{DRAWER} :text('AI-generated content may be incorrect')"

    # --- L1 controls / chart ---
    BUCKET_DAY = f"{DRAWER} input[type='radio'][value='day']"
    BUCKET_WEEK = f"{DRAWER} input[type='radio'][value='week']"
    TIMETREND_SVG = f"{DRAWER} svg.drill-timetrend-svg"
    TIMETREND_BAR = f"{DRAWER} svg.drill-timetrend-svg rect.bar"

    # --- L2 call list ---
    CALL_LIST = f"{DRAWER} table[aria-label='Drill call list']"
    CALL_LIST_ROWS = f"{DRAWER} table[aria-label='Drill call list'] tbody tr"
    PAGINATION_NEXT = f"{DRAWER} button:has-text('Next')"
    PAGINATION_PREV = f"{DRAWER} button:has-text('Prev')"

    # --- L3 transcript ---
    TRANSCRIPT_PRE = f"{DRAWER} pre.drill-transcript-pre"
    SUMMARY_HEADER = f"{DRAWER} :text('Summary')"
    TRANSCRIPT_HEADER = f"{DRAWER} :text('Transcript')"

    def __init__(self, page):
        super().__init__(page)
        self.page = page

    # ------------------------------------------------------------------
    # Opening the drawer
    # ------------------------------------------------------------------

    def open_via_trending_topic_row(self, index: int = 0):
        """Click the n-th row of the Trending Topics table to drill into that
        topic. Returns the topic name that was clicked, for breadcrumb
        assertions."""
        rows = self.page.locator(self.TRENDING_TOPIC_ROWS)
        rows.first.wait_for(state="visible", timeout=15000)
        row = rows.nth(index)
        # First column = topic name.
        topic = row.locator("td").nth(0).inner_text().strip()
        row.click()
        self._wait_for_drawer_open()
        return topic

    def _wait_for_drawer_open(self):
        self.page.locator(self.DRAWER).wait_for(state="visible", timeout=10000)

    # ------------------------------------------------------------------
    # Drawer state assertions
    # ------------------------------------------------------------------

    def assert_drawer_open(self):
        expect(self.page.locator(self.DRAWER)).to_be_visible()
        expect(self.page.locator(self.AI_DISCLAIMER)).to_be_visible()

    def assert_drawer_closed(self):
        expect(self.page.locator(self.DRAWER)).not_to_be_visible(timeout=5000)

    def assert_breadcrumb_contains(self, substring: str):
        breadcrumb = self.page.locator(self.BREADCRUMB).first
        breadcrumb.wait_for(state="visible", timeout=5000)
        text = breadcrumb.inner_text()
        assert substring in text, (
            f"Breadcrumb does not contain '{substring}'. Actual: '{text}'"
        )

    # ------------------------------------------------------------------
    # L1 -> L2 -> L3 navigation
    # ------------------------------------------------------------------

    def drill_into_first_time_bucket(self):
        """Click the first bar in the time-trend chart to drill to L2."""
        bars = self.page.locator(self.TIMETREND_BAR)
        bars.first.wait_for(state="visible", timeout=15000)
        # Wait for at least one bar with non-zero height to ensure data loaded.
        bars.first.click()
        self.page.locator(self.CALL_LIST).wait_for(state="visible", timeout=15000)

    def drill_into_first_call(self):
        """Click the first row in the call list to drill to L3."""
        rows = self.page.locator(self.CALL_LIST_ROWS)
        rows.first.wait_for(state="visible", timeout=15000)
        rows.first.click()
        self.page.locator(self.TRANSCRIPT_PRE).wait_for(
            state="visible", timeout=15000
        )

    # ------------------------------------------------------------------
    # Navigation back out
    # ------------------------------------------------------------------

    def press_escape(self, times: int = 1):
        for _ in range(times):
            self.page.keyboard.press("Escape")
            self.page.wait_for_timeout(250)

    def click_back(self):
        self.page.locator(self.BACK_BUTTON).click()
        self.page.wait_for_timeout(250)

    def click_close(self):
        self.page.locator(self.CLOSE_BUTTON).click()
        self.page.wait_for_timeout(500)

    # ------------------------------------------------------------------
    # Bucket toggle
    # ------------------------------------------------------------------

    def select_day_bucket(self):
        self.page.locator(self.BUCKET_DAY).check(force=True)
        self.page.wait_for_timeout(500)

    def select_week_bucket(self):
        self.page.locator(self.BUCKET_WEEK).check(force=True)
        self.page.wait_for_timeout(500)

    # ------------------------------------------------------------------
    # URL hash share / restore
    # ------------------------------------------------------------------

    def assert_url_has_drill_hash(self):
        hash_part = self.page.evaluate("() => window.location.hash")
        assert re.match(r"^#/drill/", hash_part), (
            f"Expected URL hash to start with '#/drill/', got: '{hash_part}'"
        )
        return hash_part

    def assert_url_has_no_drill_hash(self):
        hash_part = self.page.evaluate("() => window.location.hash")
        assert not hash_part.startswith("#/drill/"), (
            f"Expected no drill hash, got: '{hash_part}'"
        )
