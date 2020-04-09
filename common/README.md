# API
Recommender's Reddit API secret is 

# Git-subrepo
git submodules aren't well supported, so we use git-subrepo instead. git-subrepo keeps a full copy
of the subrepo in the main repo, which makes it work automatically when pulling or cloning (no need
for --recurse-submodules).

git subrepo clone <repo> <dirname>
git subrepo pull <dirname>

To push changes in the container repo back to this, simply do a:
git subrepo push <dirname>

It will take the relevant commits from the container repo and push the isolated changes to the subrepo.
etc etc.

# Testing
Testing has 2 general purposes:
1) Ensure robustness of the application
2) Increasing developer velocity

In large organizations with apps used by numerous user (e.g. Google, Amazon, FB, etc.) the former
of these is generally important. In smaller organizations and startups which don't have a ton of
user, tests are more important for the latter goal.

Depending on which of these goals your focus is, your testing style varies substantially. If your
focus is primarily robustness, then it may stand to reason to take a very heavy-handed approach to
testing in which every API contract is tested as thoroughly as possible. You may also wanted
coverage tests run on presubmit which require tests for new code.

If your focus is velocity, then tests should make it easy for a developer to validate there changes
with minimal effort. For example, it may require spinning up a bunch of services and hooking
everything together for an e2e manual test which can be time-consuming and requires a broader
context* of knowledge. A test which can be run automatically and avoids needing to know the entire
system is therefore highly useful as it decreases the context the developer needs to maintain to
make changes.

For example, to test a new Source, one could setup an e2e dev environment to manually test - or, one
could instead validate that the Source sends valid data to the right endpoint.

When velocity is the focus (as is the case at present), a few more general considerations:
1) Tests shouldn't be slow or hard to run
2) Tests should test at a high-enough level that a developer should be able to submit code which
   with high-confidence after only running the tests.

# Performance

## IndexSet, OrderedSet, set
Bolton's (presumably pure-python) setutils.IndexedSet is about 3x slower than the Cython OrderedSet
which is about 5x slower than the native set:

In [14]: from boltons import setutils
In [18]: %timeit indexed_set = setutils.IndexedSet(list(range(1000)))
265 µs ± 10.1 µs per loop (mean ± std. dev. of 7 runs, 1000 loops each)

In [21]: %timeit indexed_set = orderedset.OrderedSet(list(range(1000)))
95.6 µs ± 294 ns per loop (mean ± std. dev. of 7 runs, 10000 loops each)

In [22]: %timeit indexed_set = set(list(range(1000)))
19.2 µs ± 143 ns per loop (mean ± std. dev. of 7 runs, 100000 loops each)

# Data storage
## Initial
In the beginning, data was stored in an HDFStore using panda DataFrames. Suffice to say this didn't
work great.

DataFrames make for efficient tabular storage which is good for data anaylsis and plugs into things
like Tensorflow and other data anylsis frameworks easily - but it's messy to work with across a
bunch of threads and isn't great for serving either.

## Databases
So, we need someway[s] to store data and retrieve it. In particular (approx. order of importance):
* Concurrency - should be able to be feeding new data in from many sources
* Highly stable - don't want to keep losing data if the programs pulling data crash
* Well-supported - prefer non-custom solution that I don't spend weeks building and supporting
* Fast-serving - not willing to have multi-second lookups
* Flexible data model - grabbing content from all over with different metadata - want to be able to
  store that metadata in a structured way
* Queryable - I need to be able to support some degree of queries - e.g. 20 most-recent from askmen.
  ** It's possible this is a separate data store
* Efficient - don't take up endless space
* Need to store processed and raw data - not clear if necessary or desireable to separate these
* Should be able to update data over time easily - e.g. run new models and append new signals.

Concurrency is supported by essentially all databases beyond SQLite. No new-startup DB's for
stability. Fast-serving make me think of Redis in particular - although, any NoSQL database could be
fast-enough to start.

Flexible data model definitely suggests NoSQL. I think it essentially depends on how many data
sources ultimately get on-boarded. I think a key is to make it as easy-as-possible to onboard new
data - so, I don't really want to be constantly expanding table definitions or worrying about rigid
structuring.

Queryable. This is where things get messy - I know this is generally the big 'win' of SQL. I don't
think I need complex queries though - at least, not for this data. SQL for storing interactions
could be worthwhile to make analysis easier. The general queries I'd expect would probably center
around simple select statements with multiple where attributes and limits and light sorting. e.g.:

  Select * where askmen or various_signals sort by recency * popularity limit 100.

I think generally, serving is just going to naturally need to evolve pretty independently from
how I store things. I.e. an optimal API would boil to get_best_for_user(user_id, limit=100) and
'best' would potentially be a complex function of various signals, what the user's seen recently,
grouping, etc.

Some options:
* Redis - increasing popularity, in-memory, schemaless
* Google Cloud Datastore - optimized for GCP. Apparently being replaced with Cloud Firestore.
* $0.18-11/GB/month. $0.11/100k writes. $0.036/100k
* Couchbase * MongoDB * etc.

https://www.trustradius.com/nosql-databases

In the short term as of 3/28/20, I'm opting to use Firestore because it's free for a good amount of
use, fast, and very easy to use.

## Git setup

git submodule add <repo> <dirname>
git pull --recurse-submodules

## Serving
https://www.splunk.com/en_us/blog/it/gcp-serverless-comparison.html

My inclination is to build a stateful server - however, in retrospect, this doesn't scale (go figure,
one of these random things I actually remember from my System design interview prep...)

So, I have a few options:
1) Start stateful and thus use GCE/GKE
2) Immediately start stateless - in which case I can leverage Cloud Run or Cloud Functions for
   serving.

Stateful just goes against standard best-practices and seems likely to be harder to debug...
Perhaps I want something like:
<Preprocessor/Ranker/Filter> | Redis/Memcache | Cloud Function (Endpoints - e.g. /posts)

Benefit of Redis being scalability - short-term, I could just pull from the Preprocessor...

Benefit of separate Endpoints: 
* Autoscaling to requests without overloading preprocessor
* Separate request/ingestion load scaling
* Decoupling crashes/dev/etc.

Flip-side: If every endpoint is essentially forwarding requests to the Preprocessor.. Is it really
saving anything?
* Maybe keep together in the short-term to reduce complexity?


## GCP Integration Points
### Cloud Scheduler
Used to publish to news_pull_topic periodically - which triggers the news_pull Cloud Function to run.

### Cloud Functions
Used to pull data. 

### Cloud Logger
Logging.

### Cloud Source
Uses external github repo; allows code viewing and more importantly, deploying from branches.

## Cheat sheet
### General
gcloud config list
gcloud alpha cloud-shell {ssh|scp}

### Pub/Sub
Create a pub/sub topic: 
gcloud pubsub topics create <cron-topic>

Create a subscription to a topic:
gcloud pubsub subscriptions create <cron-sub> --topic <cron-topic>

Pull from that subscription
gcloud pubsub subscriptions pull <cron-sub> --limit 5

### Cloud functions
Note: Cloud Functions don't always pull immediately from the code... 99% time works, but occassionally doesn't.

gcloud functions deploy --retry news_pull
gcloud functions call news_pull --data='{}'


### Cloud Scheduler


