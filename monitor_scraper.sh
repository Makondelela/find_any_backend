#!/bin/bash
while true; do
  clear
  echo "=== Scraper Monitor ==="
  echo "Time: $(date '+%H:%M:%S')"
  echo ""
  
  # Check processes
  count=$(ps aux | grep career24_scraper.py | grep -v grep | wc -l)
  if [ $count -gt 0 ]; then
    echo "✓ Status: RUNNING ($count processes)"
  else
    echo "✗ Status: COMPLETED"
  fi
  
  echo ""
  echo "Last log entries:"
  tail -3 scraper_output.log
  echo ""
  echo "Output file:"
  ls -lh data_jobs_careers24.json 2>/dev/null | awk '{print $5, $9}'
  
  echo ""
  echo "Press Ctrl+C to stop monitoring"
  sleep 10
done
