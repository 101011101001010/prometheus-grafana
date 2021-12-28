import asyncio

import flask
from apscheduler.schedulers.background import BackgroundScheduler
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Gauge

import network

tools: list = [
    "pscheduler/powstream",
    "pscheduler/iperf3",
    "pscheduler/ping"
]

powstream_types: list = [
    "histogram-owdelay",
    "packet-loss-rate"
]

ping_types: list = [
    "histogram-rtt",
    "packet-loss-rate-bidir"
]

iperf3_types: list = [
    "throughput"
]

statistic_types: list = [
    "histogram-owdelay",
    "histogram-rtt",
    "throughput"
]

time_range: int = 1800
overall_count: int = 0
url: str = "http://192.168.15.129"
ret_text: str = "<body style='background: black; color: white;'>" \
                "<div style='font-family: Courier New; font-size: 10pt;'>" \
                "</div>" \
                "</body>"

app = flask.Flask(__name__)
app.config["DEBUG"] = False
metrics = PrometheusMetrics(app=None, path="/metrics", export_defaults=False)
suffix = "_v6"

ps_metrics = Gauge(f"ps_metrics_personal{suffix}", "Metrics - OWD / RTT / Throughput", ["src", "src_h", "dst", "dst_h", "type", "index"])
ps_avg = Gauge(f"ps_avg_personal{suffix}", "Average", ["src", "src_h", "dst", "dst_h", "tool", "index"])
ps_min = Gauge(f"ps_min_personal{suffix}", "Minimum", ["src", "src_h", "dst", "dst_h", "tool", "index"])
ps_max = Gauge(f"ps_max_personal{suffix}", "Maximum", ["src", "src_h", "dst", "dst_h", "tool", "index"])
ps_var = Gauge(f"ps_var_personal{suffix}", "Variance", ["src", "src_h", "dst", "dst_h", "tool", "index"])
ps_std = Gauge(f"ps_std_personal{suffix}", "Standard deviation", ["src", "src_h", "dst", "dst_h", "tool", "index"])
ps_packet_loss = Gauge(f"ps_packet_loss_personal{suffix}", "Packet loss", ["src", "src_h", "dst", "dst_h", "tool", "index"])


def gather_uris(tool: str, metadata_key: str, events: list) -> tuple:
    uri_list: list = []
    uri_keys: list = []

    for event in events:
        updated: int = event.get("time-updated")
        event_type: str = event.get("event-type")
        base_uri: str = event.get("base-uri")

        if updated is None or updated == "null" or base_uri is None or len(base_uri) == 0:
            continue
        if tool == "pscheduler/powstream" and event_type not in powstream_types:
            continue
        if tool == "pscheduler/ping" and event_type not in ping_types:
            continue
        if tool == "pscheduler/iperf3" and event_type not in iperf3_types:
            continue

        uri_list.append(url + base_uri + f"?time-range={time_range}")
        uri_keys.append(base_uri.replace(f"/esmond/perfsonar/archive/{metadata_key}/", "").replace("/base", ""))
        summaries: list = event.get("summaries")

        if summaries is None:
            continue

        for summary in summaries:
            summary_type: str = summary.get("summary-type")
            summary_window: str = summary.get("summary-window")
            uri: str = summary.get("uri")

            if summary_type == "statistics" and summary_window == "0":
                uri_list.append(url + uri)
                uri_keys.append("statistics")
                break

            if summary_type == "average" and summary_window == "86400":
                uri_list.append(url + uri)
                uri_keys.append("average")
                break

    return uri_keys, uri_list


async def process_test(tool: str, source: str, destination: str, source_host: str, destination_host: str, metadata_key: str, events: list, index: int):
    uri_keys, uri_list = gather_uris(tool, metadata_key, events)

    if uri_keys is None or uri_list is None:
        return

    results: list = []

    for uri in uri_list:
        if uri is not None:
            response = await network.get_response(uri)
            results.append(response)
            await asyncio.sleep(0.25)

    for uri_key, result in zip(uri_keys, results):
        if uri_key is None or result is None:
            return

        if isinstance(result, list):
            if len(result) > 0:
                latest_data = max(result, key=lambda x: x["ts"])
                latest_data = latest_data.get("val")
            else:
                latest_data = None
        else:
            latest_data = result

        if latest_data is None:
            continue

        if uri_key == "histogram-owdelay" or uri_key == "histogram-rtt":
            value_sum: float = 0
            value_count: int = 0

            for value, count in latest_data.items():
                value_sum += (float(value) * count)
                value_count += count

            if value_count > 0:
                value = value_sum / value_count
                key_short: str = uri_key.split("-")[-1]

                if key_short == "owdelay":
                    ps_metrics.labels(src=source, dst=destination, src_h=source_host, dst_h=destination_host, type="owdelay", index=index).set(value)
                elif key_short == "rtt":
                    ps_metrics.labels(src=source, dst=destination, src_h=source_host, dst_h=destination_host, type="rtt", index=index).set(value)

        elif uri_key == "statistics":
            mean: float = latest_data.get("mean")
            minimum: float = latest_data.get("minimum")
            maximum: float = latest_data.get("maximum")
            variance: float = latest_data.get("variance")
            std: float = latest_data.get("standard-deviation")

            if mean is not None:
                ps_avg.labels(src=source, dst=destination, src_h=source_host, dst_h=destination_host, tool=tool, index=index).set(mean)
            if minimum is not None:
                ps_min.labels(src=source, dst=destination, src_h=source_host, dst_h=destination_host, tool=tool, index=index).set(minimum)
            if maximum is not None:
                ps_max.labels(src=source, dst=destination, src_h=source_host, dst_h=destination_host, tool=tool, index=index).set(maximum)
            if variance is not None:
                ps_var.labels(src=source, dst=destination, src_h=source_host, dst_h=destination_host, tool=tool, index=index).set(variance)
            if std is not None:
                ps_std.labels(src=source, dst=destination, src_h=source_host, dst_h=destination_host, tool=tool, index=index).set(std)

        elif uri_key == "packet-loss-rate" or uri_key == "packet-loss-rate-bidir":
            ps_packet_loss.labels(src=source, dst=destination, src_h=source_host, dst_h=destination_host, tool=tool, index=index).set(latest_data)

        elif uri_key == "throughput":
            ps_metrics.labels(src=source, dst=destination, src_h=source_host, dst_h=destination_host, type="throughput", index=index).set(latest_data)

        elif uri_key == "average":
            ps_avg.labels(src=source, dst=destination, src_h=source_host, dst_h=destination_host, tool=tool, index=index).set(latest_data)


async def a():
    global ret_text, overall_count
    overall_count += 1
    print("\n[PerfSONAR] Running...")
    print("Retrieving tests from base archive...")
    results: list = await network.get_response(url + "/esmond/perfsonar/archive")

    if results is None:
        print("No result from base archive.")
        return

    indices: dict = {}
    count: int = 0
    index_tracker: int = 0

    for test in results:
        tool: str = test.get("tool-name")
        source: str = test.get("source")
        destination: str = test.get("destination")
        source_host: str = test.get("input-source")
        destination_host: str = test.get("input-destination")
        metadata_key: str = test.get("metadata-key")
        events: list = test.get("event-types")

        if tool not in tools or source is None or destination is None or source_host is None or destination_host is None or metadata_key is None or events is None or len(events) == 0:
            continue

        key: str = f"{source}<>{destination}"

        if key in indices:
            index: int = indices[key]
        else:
            index: int = index_tracker
            indices[key] = index
            index_tracker += 1

        count += 1
        print(f"-- Processing Test #{count}: {tool} ({source} <----> {destination})")
        await process_test(tool, source, destination, source_host, destination_host, metadata_key, events, index)
        await asyncio.sleep(0.25)

    print("Run completed.\n")


def crawl_task():
    asyncio.run(a())


scheduler = BackgroundScheduler()
scheduler.add_job(crawl_task, 'interval', minutes=int(time_range/60))
scheduler.start()


@app.route('/skip')
@metrics.do_not_track()
def skip():
    pass


@app.route("/")
async def home():
    return "<h1>PerfSONAR Exporter</h1>" \
           "<a href=\"metrics\">Metrics</a>"


if __name__ == "__main__":
    asyncio.run(a())
    metrics.init_app(app)
    app.run(host="0.0.0.0")
