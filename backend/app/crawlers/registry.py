from __future__ import annotations
from app.crawlers.adapters.cryptojobslist import CryptoJobsListAdapter
from app.crawlers.adapters.dejob import DeJobAdapter
from app.crawlers.adapters.linkedin import LinkedInAdapter
from app.crawlers.adapters.abetterweb3 import ABetterWeb3Adapter
from app.crawlers.adapters.web3career import Web3CareerAdapter
from app.crawlers.adapters.wellfound import WellfoundAdapter

ADAPTERS = {
    "linkedin": LinkedInAdapter,
    "cryptojobslist": CryptoJobsListAdapter,
    "web3career": Web3CareerAdapter,
    "wellfound": WellfoundAdapter,
    "dejob": DeJobAdapter,
    "abetterweb3": ABetterWeb3Adapter,
}
