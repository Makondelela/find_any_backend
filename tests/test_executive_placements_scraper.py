import sys
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scrapers"))

from executive_placements_scraper import ExecutivePlacementsScraper


class ExecutivePlacementsScraperTests(unittest.TestCase):
    def test_parses_listing_fields_and_detail_url(self):
        html = """
        <div class="entry" id="entry1" onclick="showJob(1,1234567);">
          <strong><span>Junior Software Developer</span></strong><br>
          Johannesburg<br>
          <span>2 days ago</span><br><br>
          Salary: R300 000 Annually<br><br>
          Build and maintain software applications.<br><br>
          <a class="navsOrange" href="/Jobs/J/Junior-Software-Developer-1234567-Job-Search-date.asp?sid=seo">Details</a>
          <a href="/cvs.asp?jobID=1234567">Upload CV &amp; Apply</a>
        </div>
        """

        jobs = ExecutivePlacementsScraper.parse_cards(BeautifulSoup(html, "html.parser"), "software developer")

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["title"], "Junior Software Developer")
        self.assertEqual(jobs[0]["location"], "Johannesburg")
        self.assertEqual(jobs[0]["posted"], "2 days ago")
        self.assertEqual(jobs[0]["salary"], "R300 000 Annually")
        self.assertEqual(jobs[0]["job_id"], "1234567")
        self.assertEqual(
            jobs[0]["url"],
            "https://www.executiveplacements.com/Jobs/J/Junior-Software-Developer-1234567-Job-Search-date.asp?sid=seo",
        )
        self.assertEqual(jobs[0]["source"], "Executive Placements")

    def test_build_url_encodes_keyword(self):
        self.assertEqual(
            ExecutivePlacementsScraper.build_url("software developer"),
            "https://www.executiveplacements.com/jobList.asp?kwds=software+developer",
        )

    def test_total_pages_uses_numbered_links_without_result_count(self):
        html = """
        <a href="javascript:document.forms['jobSearch'].start.value=1">1</a>
        <a href="javascript:document.forms['jobSearch'].start.value=2">2</a>
        <a href="javascript:document.forms['jobSearch'].start.value=3">3</a>
        """

        pages = ExecutivePlacementsScraper.total_pages(BeautifulSoup(html, "html.parser"))

        self.assertEqual(pages, 3)

    def test_integration_keywords_are_added_without_duplicates(self):
        keywords = ExecutivePlacementsScraper.get_keywords(["Software Developer", "integration"])

        self.assertEqual(keywords, ["Software Developer", "integration", "Integration Developer", "Integration Engineer"])


if __name__ == "__main__":
    unittest.main()