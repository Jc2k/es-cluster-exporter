# es-cluster-exporter

A prometheus exporter for es cluster level stats. This is meant as a companion for [elasticsearch-prometheus-exporter](https://github.com/vvanholl/elasticsearch-prometheus-exporter). You should deploy this on every ES node in your cluster and then deploy a single es-cluster-exporter for a cluster-wide overview.

Right now, this is mostly for tracking shard growth:

 * If you have massive numbers of shards your performance will suck. If you have massive numbers of tiny shards your performance will suck for no reason.

 * If you have too few shards you will have massive shards, and your life will suck for other reasons (fail over of small shards is easier than fail over of massive shards).
 
 * If you have massive shards your performance will suck.

