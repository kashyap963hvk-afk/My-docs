#!/usr/bin/env bash
# Start OpenSearch (search engine) on the VM, port 9200, data kept in a Docker volume.
set -euo pipefail
sudo sysctl -w vm.max_map_count=262144   # OpenSearch refuses to start without this

docker rm -f opensearch 2>/dev/null || true
docker run -d --name opensearch --restart unless-stopped \
  -p 127.0.0.1:9200:9200 -p 172.17.0.1:9200:9200 \
  -e discovery.type=single-node \
  -e DISABLE_SECURITY_PLUGIN=true \
  -e DISABLE_INSTALL_DEMO_CONFIG=true \
  -e OPENSEARCH_JAVA_OPTS="-Xms2g -Xmx2g" \
  -v opensearch-data:/usr/share/opensearch/data \
  opensearchproject/opensearch:3.9.0
echo "OpenSearch is starting. Test in 30 seconds with: curl -s localhost:9200"
