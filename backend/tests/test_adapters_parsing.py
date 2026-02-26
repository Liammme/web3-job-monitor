from __future__ import annotations

from datetime import datetime

from bs4 import BeautifulSoup

from app.crawlers.adapters import cryptojobslist, cryptocurrencyjobs, linkedin, remote3, web3career, web3jobsai


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


def test_web3jobsai_adapter_extracts_listing(monkeypatch):
    html = """
    <article class='job-list' id='post-10'>
      <h2 class='job-title'><a href='https://web3jobs.ai/job/senior-solidity-engineer/'>Senior Solidity Engineer</a></h2>
      <div class='job-location'>Remote</div>
      <div class='job-deadline with-icon'>February 26, 2026</div>
      <div class='job-type'><a class='type-job'>Full Time</a></div>
      <div class='category-job'><a>Blockchain Development</a></div>
    </article>
    """
    monkeypatch.setattr(web3jobsai, "fetch_html", lambda *_args, **_kwargs: html)
    monkeypatch.setattr(web3jobsai, "soup_links", _soup_links_from_html)

    jobs = web3jobsai.Web3JobsAiAdapter().fetch()

    assert len(jobs) == 1
    assert jobs[0].source_job_id == "10"
    assert jobs[0].title == "Senior Solidity Engineer"
    assert jobs[0].location == "Remote"
    assert jobs[0].employment_type == "Full Time"
    assert isinstance(jobs[0].posted_at, datetime)


def test_cryptocurrencyjobs_adapter_extracts_listing(monkeypatch):
    html = """
    <div id='find-a-job'>
      <ul class='mt-6'>
        <li class='grid'>
          <h2><a href='/engineering/acme-senior-solidity-engineer/'>Senior Solidity Engineer</a></h2>
          <h3><a href='/startups/acme/'>Acme</a></h3>
          <div class='flex flex-row flex-wrap'>
            <ul><li><h4><a href='/remote/'>Remote - Global</a></h4></li></ul>
            <h4><a href='/engineering/'>Engineering</a></h4>
            <ul><li><h4><a href='/full-time/'>Full-Time</a></h4></li></ul>
          </div>
          <time datetime='2026-02-26T08:00:00'></time>
          <ul class='flex flex-wrap'>
            <li><a href='/defi/'>DeFi</a></li>
          </ul>
        </li>
      </ul>
    </div>
    """
    monkeypatch.setattr(cryptocurrencyjobs, "fetch_html", lambda *_args, **_kwargs: html)
    monkeypatch.setattr(cryptocurrencyjobs, "soup_links", _soup_links_from_html)

    jobs = cryptocurrencyjobs.CryptocurrencyJobsAdapter().fetch()

    assert len(jobs) == 1
    assert jobs[0].title == "Senior Solidity Engineer"
    assert jobs[0].company == "Acme"
    assert jobs[0].remote_type == "remote"
    assert jobs[0].employment_type == "Full-Time"
    assert jobs[0].source_job_id == "/engineering/acme-senior-solidity-engineer/"
    assert isinstance(jobs[0].posted_at, datetime)
