#!/usr/bin/env python3

import requests
import time
import yaml

prom_server = "<promethues_server_goes_here>"
query_url=prom_server + '/api/v1/query'
rebase_time = int(time.time())
rule_file_name = "data.yml"

metric_io_table = [
    dict(
        query = str('gtp_tickets_refunded:cumulative'),
        metric_to_record = 'gtp_tickets_refunded:rebase',
        group_name = "rebased gtp_tickets_refunded at " + str(rebase_time)
    ),
    dict(
        query = str('gtp_tickets_sold:cumulative'),
        metric_to_record = 'gtp_tickets_sold:rebase',
        group_name = "rebased gtp_tickets_sold at " + str(rebase_time)
    ),
    dict(
        query = str('gtp_completed_orders_total_value:cumulative'),
        metric_to_record = 'gtp_completed_orders_total_value:rebase',
        group_name = "rebased gtp_completed_orders_total_value at " + str(rebase_time)
    ),
    dict(
        query = str('gtp_completed_transactions:cumulative'),
        metric_to_record = 'gtp_completed_transactions:rebase',
        group_name = "rebased gtp_completed_transactions at " + str(rebase_time)
    ),
    dict(
        query = str('increase(gtp_completed_loyalty_transactions{OrganisationName!="Availability Test Vendor"}[1y])'),
        metric_to_record = 'gtp_completed_loyalty_transactions:rebase',
        group_name = "rebased gtp_completed_loyalty_transactions at " + str(rebase_time)
    )
]

def query_metrics(query: str):
    """Used to query the configured prometheus instance for it's metrics.

    Args:
        query: the metric to query for.

    Returns:
        list: A list of metrics, essentially the result list from the Prometheus HTTP API.
    """
    query_params = {'query': str(query), 'time': rebase_time}
    print("query_params:" + str(query_params))
    r = requests.get(query_url, params=query_params)
    r.raise_for_status()
    response = r.json()
    return response["data"]["result"]

def convert_metrics_to_rules(metrics: list, output_metric: str):
    """
    Used to convert a list of metrics to a list of recording rules,
    with the value at that point in time as the value for the recording rule.

    Args:
        metrics: the result list from the prom http endpoint
        output_metric: the new metric name to record

    Returns:
        rules: a list of rules to be placed in a recording rule group
    """
    rules = []
    print("Converting metrics to rules for " + output_metric)
    for metric in metrics:
        # print(metric)
        rule = dict(
            record = output_metric,
            expr = metric["value"][1],
            labels = dict(
                CinemaChainId = metric["metric"]["CinemaChainId"],
                OrganisationName = metric["metric"]["OrganisationName"],
                job = metric["metric"]["job"],
                region = metric["metric"]["region"],
                service = metric["metric"]["service"],
            )
        )
        rules.append(rule)
    return rules
    
rule_file = dict(
    groups = []
)

for metric in metric_io_table:
    print('Generating rules for group: "' + metric["group_name"] + '"')
    metrics = query_metrics(metric["query"])
    rules = convert_metrics_to_rules(metrics, metric["metric_to_record"])

    group = dict(
        name = metric["group_name"],
        interval = '15s',
        rules = rules
    )

    rule_file["groups"].append(group)
    
print("Writing to " + rule_file_name)
with open(rule_file_name, 'w') as outfile:
    yaml.dump(rule_file, outfile, default_flow_style=False)
