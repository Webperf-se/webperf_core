# DNS test (Zonemaster)

Test number: **32**. Rating logic in `tests/zonemaster_dns.py`, severity profile in
`defaults/webperf-dns.profile.json`.

Runs [Zonemaster](https://zonemaster.net/) against the website's domain and rates the
quality of the DNS delegation.

## What is being tested? — and why it matters for the visitor

DNS is the first step of every visit: if the lookup fails, the visitor never reaches the
web server, however healthy it is. The guiding principle is *visitor consequence*, not
technical perfection. What we care about:

- **Reliability** — redundancy and diversity among name servers, so a single disruption
  does not take the whole site down (avoid a single point of failure).
- **Security** — that the visitor is steered to the right server (DNSSEC integrity, answer
  consistency).
- **Speed** — the DNS lookup is the very first delay in a page load.

Pure hygiene with no visitor impact (reverse DNS for name servers, SOA timers, syntax
pedantry) is deliberately weighted lightly.

## What it measures

Zonemaster groups ~90 test cases into nine modules: Address, Basic, Connectivity,
Consistency, DNSSEC, Delegation, Nameserver, Syntax and Zone. Every message has a severity
level: INFO, NOTICE, WARNING, ERROR or CRITICAL.

## How is the rating calculated? (1–5)

We **score per test case but report per module**, so the review stays short even when the
engine produces many messages.

- The worst level per test case is aggregated into one "criterion".
- A CRITICAL → 1.0 (the delegation is broken).
- `penalty = (2·errors + 1·warnings) / criteria_that_ran`
- `rating = 5 − 4 · min(1, penalty / 0.5)`, with a floor of 1.0.

Calibration: when roughly **half of the criteria warn** the rating lands on 1.0, while a
handful of warnings on an otherwise healthy domain only lowers it marginally. The
`THRESHOLD` (0.5) and the error weight (2×) are knobs, exposed as settings
(`tests.dns.threshold`, `tests.dns.error-weight`). `min()`/the floor give a natural ceiling —
no free fall.

The 1.0–5.0 rating is mapped onto the Rating model as:

- **Overall** — all criteria.
- **Integrity & security** — the DNSSEC and Consistency modules (validation integrity and
  being steered to a consistent answer).
- **Standards** — the remaining modules (delegation, reachability, syntax, timers).

## Visitor-impact re-weighting

To keep visitor consequence — not raw engine defaults — in charge, some test cases are
re-weighted **down** (never removed, so the criterion still counts in the "X of Y"
denominator but no longer lowers the rating):

**Downgraded to NOTICE** (low visitor impact):

- Address02/03 — reverse DNS for the name servers.
- Zone — SOA expire timer inside/outside the RFC recommendation.
- Syntax — discouraged-but-legal forms (double dash, numeric TLD, RName RFC822 form).

**Kept high** (reliability / security):

- Connectivity03/04 — AS and prefix diversity (protection against a single point of failure).
- Delegation, Consistency, Basic — that the zone can be reached and answers consistently.
- DNSSEC — *broken* DNSSEC (bad/expired signatures) makes the domain unreachable for
  validating resolvers; kept as an error. *Absence* of DNSSEC is held mild (NOTICE) — a
  missing protection, not a breakage.

The re-weighting is applied **in code** (`SEVERITY_OVERRIDES` in `tests/zonemaster_dns.py`).
This is deliberate: Zonemaster's `--profile` **replaces** the whole `test_levels` map rather
than merging per tag, so a *partial* profile would silently suppress every unlisted tag —
including CRITICAL delegation failures. Doing it in code keeps every default severity
intact, lets new Zonemaster tags flow through, and lets the calibration CLI recompute the
rating offline from saved raw JSON.

`defaults/webperf-dns.profile.json` mirrors the same weights as a **complete** pinned
`test_levels` map, for callers who explicitly opt into engine-side weighting
(`tests.dns.profile.use=true`). Because it is a full pin, it must be regenerated from
`zonemaster-cli --dump-profile` when the Zonemaster version is upgraded.

## Settings

| Setting | Alias | Default | Meaning |
| --- | --- | --- | --- |
| `tests.dns.timeout` | `dnstimeout` | `180` | Seconds per domain. |
| `tests.dns.ipv6` | `dnsipv6` | `false` | Enable IPv6 queries (needs IPv6 in Docker). |
| `tests.dns.registrable` | `dnsregistrable` | `true` | Test the registrable domain (strip `www`) vs the exact hostname. |
| `tests.dns.threshold` | `dnsthreshold` | `0.5` | Calibration: share of damaged criteria that hits the floor. |
| `tests.dns.error-weight` | `dnserrorweight` | `2.0` | Calibration: how many warnings an error weighs. |
| `tests.dns.profile.use` | `dnsprofile` | `false` | Also push the weights into Zonemaster via the bundled complete profile. |
| `tests.dns.image` | `dnsimage` | `zonemaster/cli` | Docker image (pin a version here). |

## How is the test run?

Via the Docker image `zonemaster/cli` (same pattern as Sitespeed):

```
docker run --rm zonemaster/cli \
  --json --level=INFO --show_testcase --no-ipv6 example.com
```

- `--level=INFO` is needed to count "X of Y criteria".
- `--no-ipv6` avoids false errors when Docker has no IPv6. Enable IPv6
  (`tests.dns.ipv6=true`) if the run environment supports it — it gives a more complete
  result (Address tests among others).
- The test needs network egress, including **external ASN lookups** (Cymru/RIPE) for
  Connectivity03/04. Same caveat as our other external tests — see the general page on
  GitHub Actions.

## Calibration (offline)

The module is also a stand-alone CLI for calibration without re-querying DNS:

```
# Save raw JSON per domain
python tests/zonemaster_dns.py -f gov-domains.txt --workers 4 --save-dir raw/
# Rescore offline while trying different knobs (no DNS traffic)
python tests/zonemaster_dns.py --from-dir raw/ --threshold 0.4 --error-weight 3.0
```

## Read more

* https://zonemaster.net/
* https://github.com/zonemaster/zonemaster

## How to setup?

### Prerequirements

* Fork this repository.
* Docker must be available, and the machine running the test needs network egress
  (including external ASN lookups). As the delegation is public, the domain must be
  publicly resolvable.

### Setup with GitHub Actions

Read more on the [general page for github actions](../getting-started-github-actions.md).

### Setup Locally

* Follow the [general local setup steps for this repository](../getting-started-local.md).
* The `zonemaster/cli` image is pulled automatically on first use.

## Known limitations and open questions

- **The test partly rates the hosting provider, not the site.** Name-server diversity is
  decided by the DNS provider. A site on shared hosting can rarely fix "both name servers in
  the same network" without moving DNS (e.g. to a third party) or changing host — and even
  github.com gets a WARNING on prefix diversity. *Should such a single point of failure cost
  full rating, or be reported as an actionable notice?* This is left open for the community
  to decide.
- **External dependencies:** the ASN lookups require Cymru/RIPE to answer; otherwise
  Connectivity03/04 are undetermined and should not be penalized.
- **Calibration:** is "half warn → 1.0" and error = 2× warning the right balance for our
  audience (public sector), which values standards compliance highly?

## License

Zonemaster: 2-clause BSD. webperf_core: MIT. Both permissive and compatible. We call
Zonemaster as an external tool via Docker and do not embed its source, so there are no
license obligations beyond keeping their copyright/license notice if we ever distribute
their code.

## FAQ

No frequently asked questions yet :)
