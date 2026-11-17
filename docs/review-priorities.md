# Independent guide review priorities

All 60 guides remain `draft`. Passing examples and internally calibrated
contract tests are not independent technical review. Before changing a guide
to `reviewed`, record a named independent reviewer and date in its front matter
and inspect its applicability, failure modes, references and real adapters.

Suggested first review batch, ordered by consequence of a wrong recommendation:

1. `verify-token-claims`: signature, issuer, audience and algorithm policy.
2. `restrict-outbound-destinations`: redirect and DNS/network boundary assumptions.
3. `confine-file-access`: POSIX filename, symlink and directory ownership limits.
4. `transactional-outbox`: PostgreSQL commit and publishing guarantees.
5. `ack-after-commit`: redelivery, acknowledgement and broker failure behavior.
6. `quantize-money`: exact input bounds and independence from caller decimal context.

For each review, check the declared Python/runtime/library/service requirements
against the code and primary sources, rerun its public contract with required
disposable services, and record remaining limits. Seek a reviewer other than
the guide's author or its automated verifier. Do not bulk-promote the catalog
based on CI or the agent pilot.
