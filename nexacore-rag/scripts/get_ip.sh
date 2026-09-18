#!/usr/bin/env bash
# Prints the details needed for deliverable (e): the IP of the machine running the project.
# Take a screenshot of this output while the app is running.
echo "Date/time      : $(date)"
echo "Hostname       : $(hostname)"
echo "OS             : $(lsb_release -ds 2>/dev/null || grep PRETTY_NAME /etc/os-release | cut -d= -f2)"
echo "Local IP(s)    : $(hostname -I)"
echo "Public IP      : $(curl -s --max-time 5 https://api.ipify.org || echo 'not reachable')"
echo "Qdrant         : $(curl -s --max-time 3 http://localhost:6333/healthz || echo 'not running')"
echo "Streamlit 8501 : $(curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://localhost:8501 || echo 'not running')"
