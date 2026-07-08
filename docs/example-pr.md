# Example: PR-driven CSV append

This PR demonstrates the Jenkins CSV-appender pipeline.

When this PR is opened, Jenkins will read the `key=value` lines from
this description and append a new row to `data/metrics.csv`. The change
will then be pushed back to this branch.
