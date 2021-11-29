#!/bin/bash -e
# /usr/share/node_exporter/users.sh

USERS=$(who | wc -l)

echo "# HELP node_current_users Current user count."
echo "# TYPE node_current_users gauge"
echo "node_current_users ${USERS}"

