#!/usr/bin/env python3

import requests
import time
import yaml
import argparse

parser = argparse.ArgumentParser(description='Converts current prometheus metrics, to recording rules at a point in time.')
parser.add_argument('-s', '--server', type=str, dest='server', required=True,
                    help='The prometheus server to query. Include protocol, fqdn and port')
parser.add_argument('-t', '--time', type=int, dest='custom_time', default=int(time.time()),
                    help='A custom time to query at, as UNIX time in seconds. Defaults to now.')
parser.add_argument('-o', '--output-file', type=str, dest='output_file', default='data.yaml',
                    help='Where to save the rule files. Default to "data.yaml"')

args = parser.parse_args()

server = args.server
query_url = server + '/api/v1/query'
rebase_time = args.custom_time
rule_file_name = args.output_file

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
        query = str('round(increase(gtp_completed_loyalty_transactions{OrganisationName!="Availability Test Vendor"}[1y]))'),
        metric_to_record = 'gtp_completed_loyalty_transactions:rebase',
        group_name = "rebased gtp_completed_loyalty_transactions at " + str(rebase_time)
    )
]

def pause():
    scriptPause = input("Press <ENTER> to continue.")

def query_prometheus(query: str):
    """Used to query the configured prometheus instance for it's metrics.

    Args:
        query: the metric to query for.

    Returns:
        list: A list of metrics, essentially the result list from the Prometheus HTTP API.
    """
    print("Querying " + query)
    query_params = {'query': query, 'time': rebase_time}
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
    print("Creating rules for " + output_metric)
    rules = []
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
    
print('About to convert the result of these queries:')
for metric in metric_io_table:
    print(metric["query"])

print('with these arguments:')
print(str(args))
pause()

rule_file = dict(
    groups = []
)

rebase_time_group = {
    'name': 'cumulative_metric_rebase_time_seconds group',
    'rules': [
        {
            'record': 'cumulative_metric_rebase_time_seconds',
            'expr': str(time.time()),
            'labels': {'prometheus_instance': server}
        },
        {
            'alert': 'monitor__rebased_metrics_expiring',
            'expr': '((time() - cumulative_metric_rebase_time_seconds) / 3600 / 24) > 150',
            'labels': {
                'alerttype': 'alert',
                'severity': 'high'
            },
            'annotations': {
                'title': 'Cumulative metrics will need to be rebased within 30d',
                'details': ('It has been {{ $value }} since the cumulative metrics '
                            'were last rebased. Consider using this tool to save your '
                            'sanity https://git.bencl.app/rebase-prom-metrics')
            }
        }
    ]
}
rule_file["groups"].append(rebase_time_group)

for metric in metric_io_table:
    print('Generating rules for group: "' + metric["group_name"] + '"')
    metrics = query_prometheus(metric["query"])
    rules = convert_metrics_to_rules(metrics, metric["metric_to_record"])

    group = dict(
        name = metric["group_name"],
        rules = rules
    )

    rule_file["groups"].append(group)
    

print("Writing to " + rule_file_name)
with open(rule_file_name, 'w') as outfile:
    yaml.dump(rule_file, outfile, default_flow_style=False)
