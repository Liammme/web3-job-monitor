from __future__ import annotations

from bs4 import BeautifulSoup

from app.crawlers.adapters import cryptojobslist, linkedin, remote3, web3career


def _soup_links_from_html(html: str):
    soup = BeautifulSoup(html, "html.parser")
    return soup, soup.find_all("a")


def test_linkedin_adapter_extracts_company(monkeypatch):
    html = """
    <div class='base-card'>
      <a class='base-card__full-link' href='https://www.linkedin.com/jobs/view/head-of-web3-12345?trk=x'>open</a>
      <h3 class='base-search-card__title'>Head of Web3</h3>
      <h4 class='base-search-card__subtitle'><a href='/company/revenue3'>Revenue3</a></h4>
      <span class='job-search-card__location'>United States</span>
    </div>
    """
    monkeypatch.setattr(linkedin, "fetch_html", lambda *_args, **_kwargs: html)
    monkeypatch.setattr(linkedin, "soup_links", _soup_links_from_html)

    jobs = linkedin.LinkedInAdapter().fetch()

    assert len(jobs) == 1
    assert jobs[0].title == "Head of Web3"
    assert jobs[0].company == "Revenue3"
    assert jobs[0].source_job_id == "12345"


def test_cryptojobslist_adapter_extracts_company(monkeypatch):
    html = """
    <table class='job-preview-inline-table'>
      <tbody>
        <tr>
          <td><a href='/jobs/senior-solidity-engineer-at-acme'>Senior Solidity Engineer</a></td>
          <td><a href='/companies/acme'>Acme</a></td>
          <td>120k-180k</td>
          <td>📍 Remote</td>
        </tr>
      </tbody>
    </table>
    """
    monkeypatch.setattr(cryptojobslist, "fetch_html", lambda *_args, **_kwargs: html)
    monkeypatch.setattr(cryptojobslist, "soup_links", _soup_links_from_html)

    jobs = cryptojobslist.CryptoJobsListAdapter().fetch()

    assert len(jobs) == 1
    assert jobs[0].title == "Senior Solidity Engineer"
    assert jobs[0].company == "Acme"
    assert jobs[0].remote_type == "remote"


def test_web3career_adapter_extracts_jobposting(monkeypatch):
    html = """
    <script type='application/ld+json'>
    {
      "@type": "JobPosting",
      "title": "Protocol Engineer",
      "datePosted": "2026-02-26",
      "description": "Build core protocol",
      "jobLocationType": "TELECOMMUTE",
      "employmentType": "FULL_TIME",
      "hiringOrganization": {"name": "Binance", "url": "https://www.binance.com"}
    }
    </script>
    """
    monkeypatch.setattr(web3career, "fetch_html", lambda *_args, **_kwargs: html)
    monkeypatch.setattr(web3career, "soup_links", _soup_links_from_html)

    jobs = web3career.Web3CareerAdapter().fetch()

    assert len(jobs) == 1
    assert jobs[0].title == "Protocol Engineer"
    assert jobs[0].company == "Binance"
    assert jobs[0].remote_type == "remote"


def test_remote3_adapter_returns_empty():
    assert remote3.Remote3Adapter().fetch() == []
