# rebase-prom-metrics

a little tool to query a Prometheus server, and create recording rules based on the results returned. Intented to be used as a dirty hack to rebase cumulative metrics past the retention period of your Prometheus server.

A metric and alert are created to help notify when the next rebasing is required.

```yaml
groups:
- name: cumulative_metric_rebase_time_seconds group
  rules:
  - expr: '1527405923.0883791'
    labels:
      prometheus_instance: some.prometheus.server:9090
    record: cumulative_metric_rebase_time_seconds
  - alert: monitor__rebased_metrics_expiring
    annotations:
      details: It has been {{ $value }} since the cumulative metrics were last rebased.
        Consider using this tool to save your sanity https://git.bencl.app/rebase-prom-metrics
      title: Cumulative metrics will need to be rebased within 30d
    expr: ((time() - cumulative_metric_rebase_time_seconds) / 3600 / 24) > 150
    labels:
      alerttype: alert
      severity: high
```

Recording rules are created based on the data in `metric_io_table`. This contains a list of dictionairies, each with a `query`, `metric_to_record` and `group_name` variable. These are used to query, record and the rule group, respectively.
