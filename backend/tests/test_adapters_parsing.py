from __future__ import annotations

from datetime import datetime
import html
import json

from bs4 import BeautifulSoup

from app.crawlers.adapters import (
    aijobsnet,
    cryptojobslist,
    cryptocurrencyjobs,
    linkedin,
    remote3,
    web3career,
    web3jobsai,
    workatstartup_ai,
)


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


def test_aijobsnet_adapter_extracts_listing(monkeypatch):
    html = """
    <ul id='job_list'>
      <li class='d-flex justify-content-between position-relative pb-2'>
        <div>
          <div><a href='/job/backend-engineer-ai-remote-us-8829/'>Backend Engineer, AI</a></div>
          <div><span>Python</span> | <span>LLM</span></div>
        </div>
        <div class='text-end'>
          <div>
            <span class='text-bg-warning px-1 rounded'>Senior-level</span>
            <span class='text-bg-secondary px-1 rounded'>Full Time</span>
          </div>
          <div>Remote - US</div>
          <div class='text-muted'>5h ago</div>
        </div>
      </li>
    </ul>
    """
    monkeypatch.setattr(aijobsnet, "fetch_html", lambda *_args, **_kwargs: html)
    monkeypatch.setattr(aijobsnet, "soup_links", _soup_links_from_html)

    jobs = aijobsnet.AIJobsNetAdapter().fetch()

    assert len(jobs) == 1
    assert jobs[0].title == "Backend Engineer, AI"
    assert jobs[0].remote_type == "remote"
    assert jobs[0].employment_type == "Full Time"
    assert jobs[0].source_job_id == "job/backend-engineer-ai-remote-us-8829"
    assert isinstance(jobs[0].posted_at, datetime)


def test_workatstartup_ai_adapter_extracts_listing(monkeypatch):
    html = """
    <div class='jobs-list'>
      <div>
        <div class='w-full bg-beige-lighter mb-2 rounded-md p-2 border border-gray-200 flex'>
          <a href='https://www.workatastartup.com/companies/mason' target='company'></a>
          <div class='ml-5 my-auto grow'>
            <div class='company-details text-lg'>
              <a href='https://www.workatastartup.com/companies/mason' target='company'>
                <span class='font-bold'>Mason (W16)</span>
                <span class='text-gray-300 text-sm block sm:inline ml-0 sm:ml-2 mt-1 sm:mt-0'>(about 11 hours ago)</span>
              </a>
            </div>
            <div class='flex-none sm:flex mt-2 flex-wrap'>
              <div class='job-name shrink text-blue-500'>
                <a class='font-bold captialize mr-5' data-jobid='30657' href='https://www.ycombinator.com/companies/mason/jobs/eO4bkD3xo-full-stack-software-engineer' target='job'>
                  Full Stack Software Engineer
                </a>
              </div>
              <p class='job-details my-auto break-normal'>
                <span class='capitalize text-sm font-thin'>fulltime</span>
                <span class='capitalize text-sm font-thin'>Seattle, WA</span>
                <span class='capitalize text-sm font-thin'>Full stack</span>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
    """
    monkeypatch.setattr(workatstartup_ai, "fetch_html", lambda *_args, **_kwargs: html)
    monkeypatch.setattr(workatstartup_ai, "soup_links", _soup_links_from_html)

    jobs = workatstartup_ai.WorkAtStartupAIAdapter().fetch()

    assert len(jobs) == 1
    assert jobs[0].title == "Full Stack Software Engineer"
    assert jobs[0].company == "Mason"
    assert jobs[0].employment_type == "fulltime"
    assert jobs[0].location == "Seattle, WA"
    assert jobs[0].source_job_id == "30657"
    assert isinstance(jobs[0].posted_at, datetime)


def test_workatstartup_ai_adapter_prefers_detail_jd(monkeypatch):
    listing_html = """
    <div class='jobs-list'>
      <div>
        <div>
          <a href='https://www.workatastartup.com/companies/ai-labs' target='company'></a>
          <div class='company-details text-lg'>
            <a href='https://www.workatastartup.com/companies/ai-labs' target='company'>
              <span class='font-bold'>AI Labs</span>
              <span class='text-gray-300'>(about 2 hours ago)</span>
            </a>
          </div>
          <div class='job-name'>
            <a data-jobid='9988' href='https://www.ycombinator.com/companies/ai-labs/jobs/abc-ai-platform-engineer' target='job'>
              Platform Engineer
            </a>
          </div>
          <p class='job-details'>
            <span>fulltime</span>
            <span>Remote</span>
          </p>
        </div>
      </div>
    </div>
    """
    data_page = {
        "props": {
            "job": {
                "companyName": "AI Labs",
                "companyUrl": "/companies/ai-labs",
                "description": "<p>Build large language model services and retrieval augmented generation pipelines.</p>",
            },
            "company": {"website": "https://ai-labs.example.com"},
        }
    }
    detail_html = (
        "<div id='WaasShowJobPage-react-component-x' "
        f"data-page='{html.escape(json.dumps(data_page), quote=True)}'></div>"
    )

    def _fake_fetch(url: str, *_args, **_kwargs):
        if "jobs?query=ai" in url:
            return listing_html
        return detail_html

    monkeypatch.setattr(workatstartup_ai, "fetch_html", _fake_fetch)
    monkeypatch.setattr(workatstartup_ai, "soup_links", _soup_links_from_html)

    jobs = workatstartup_ai.WorkAtStartupAIAdapter().fetch()

    assert len(jobs) == 1
    assert jobs[0].company == "AI Labs"
    assert jobs[0].raw_payload["company_url"] == "https://ai-labs.example.com"
    assert "large language model" in jobs[0].description.lower()
