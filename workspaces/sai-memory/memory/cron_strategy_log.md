# Cron Strategy: Perplexity Namespace Refresh
The ACT-I nodes are currently independently executing the 642 physical Perplexity endpoints across 214 total namespaces to baseline the initial matrix. 

**Once the first generation loop completes tonight, we will implement the following Cron rule set:**
1. A weekly refresh loop mapped to `saimemory`/`acti-judges`. 
2. **14-day staleness expiration** for pure technology & developer namespaces (AI/API/Dev) to ensure rapid tool shifts reflect in the UI boundaries. 
3. **30-day staleness expiration** for all other domains (Marketing/Sales/Ops etc). 

This logic will execute seamlessly in the background without needing manual triggering, consistently scraping the physical web to update failure models and market caps so the formula constraints scale autonomously.
