# Runtime dependency maintenance

`pyproject.toml` defines the runtime dependencies. CI audits the versions that a
fresh installation resolves with `pip-audit --strict .`; this project-path
scan excludes development tools. Its result depends on current package indexes
and advisory data, so rerunning it is the way to check current findings.

## Historical findings and applicability

The 5 October 2026 environment scan reported ten rows across three packages.
Deduplicating repeated records by package and advisory ID gives seven findings:

| Package and advisory | Fixed in | Assessment for SC2AM |
| --- | --- | --- |
| Click `PYSEC-2026-2132` ([GHSA-47fr-3ffg-hgmw](https://github.com/pallets/click/security/advisories/GHSA-47fr-3ffg-hgmw)) | 8.3.3 | The advisory affects `click.edit()`. SC2AM does not call it, so this path is not applicable to the current code. The minimum is raised to avoid retaining the known vulnerable release. |
| idna `PYSEC-2026-215` ([GHSA-65pc-fj4g-8rjx](https://github.com/kjd/idna/security/advisories/GHSA-65pc-fj4g-8rjx)) | 3.15 | idna is brought in through Requests and handles internationalized hostnames. The reported resource exhaustion needs specially crafted, very long input; this is not evidence of an exploitable SC2AM path, but the indirect dependency is in the URL-processing path. |
| urllib3 `PYSEC-2026-141` ([GHSA-qccp-gfcp-xxvc](https://github.com/urllib3/urllib3/security/advisories/GHSA-qccp-gfcp-xxvc)) | 2.7.0 | The report requires a low-level proxy API and cross-origin redirect flow. SC2AM uses `requests.get()` and does not configure that low-level API. |
| urllib3 `PYSEC-2026-142` ([GHSA-mf9v-mfxr-j63j](https://github.com/urllib3/urllib3/security/advisories/GHSA-mf9v-mfxr-j63j)) | 2.7.0 | The report requires specific streaming and decompression calls. SC2AM downloads artwork through `requests.get()` and does not call `drain_conn()`; exposure to the reported conditions was not reproduced. |
| urllib3 `PYSEC-2026-4177` ([GHSA-vxq7-64xx-v4gw](https://github.com/urllib3/urllib3/security/advisories/GHSA-vxq7-64xx-v4gw)) | 2.8.0 | The report concerns crafted chunked HTTP responses. Requests is used for artwork downloads, so the HTTP client path exists; a matching response or exploit was not reproduced. |
| urllib3 `PYSEC-2026-4176` ([GHSA-gh4c-6fx4-qh6g](https://github.com/urllib3/urllib3/security/advisories/GHSA-gh4c-6fx4-qh6g)) | 2.8.0 | The report requires chunked, deflate encoded streaming responses with trailing data. This response was not reproduced in SC2AM. |
| urllib3 `PYSEC-2026-4175` ([GHSA-8988-9cw3-xx77](https://github.com/urllib3/urllib3/security/advisories/GHSA-8988-9cw3-xx77)) | 2.8.0 | The report requires HTTPS proxy TLS configuration. SC2AM does not configure an HTTPS forwarding proxy; behavior under external proxy environment settings was not tested. |

These findings indicate vulnerable package versions, not proof of exploitability.
The declared minimums now exclude every affected version reported by this scan:
Click 8.3.3, idna 3.15, and urllib3 2.8.0. A fresh resolution on 7 October 2026
selected Click 8.5.0, idna 3.20, and urllib3 2.8.0 and returned no known
vulnerabilities. A routine install without upgrade options can leave already
installed transitive packages in place.

## Updating an existing installation

Activate the virtual environment used to run SC2AM, then update the project and
its dependencies:

```bash
python -m pip install --upgrade \
  "https://github.com/zFl4wless/sc2am/releases/download/v2.0.1/sc2am-2.0.1-py3-none-any.whl"
python -m pip check
```

The example uses the latest published release, v2.0.1. Once v2.1.0 is
published, use its wheel URL from the [GitHub release](https://github.com/zFl4wless/sc2am/releases)
to receive the dependency minimums described above. Do not assume that a
package with the same name on a package index is this GitHub release.

For a source checkout, use `python -m pip install --upgrade -e .` instead. The
upgrade option lets pip replace installed dependencies to satisfy the current
metadata. Restart shells or processes that keep the old environment loaded.

To repeat the runtime audit from a checkout:

```bash
python -m pip install pip-audit
python -m pip_audit --strict .
```
