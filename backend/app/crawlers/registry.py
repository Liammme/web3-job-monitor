from __future__ import annotations
from app.crawlers.adapters.cryptojobslist import CryptoJobsListAdapter
from app.crawlers.adapters.linkedin import LinkedInAdapter
from app.crawlers.adapters.remote3 import Remote3Adapter
from app.crawlers.adapters.web3career import Web3CareerAdapter
from app.crawlers.adapters.wellfound import WellfoundAdapter

ADAPTERS = {
    "linkedin": LinkedInAdapter,
    "cryptojobslist": CryptoJobsListAdapter,
    "web3career": Web3CareerAdapter,
    "wellfound": WellfoundAdapter,
    "remote3": Remote3Adapter,
}
