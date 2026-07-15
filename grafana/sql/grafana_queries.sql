-- Current machine status
SELECT current_state, last_beat FROM monitor_heartbeat WHERE id = 1;

-- Shift performance table
SELECT shift_date AS "Date", shift_name AS "Shift",
       up_seconds / 3600.0 AS "Up hours",
       down_seconds / 3600.0 AS "Down hours",
       efficiency_pct AS "Efficiency"
FROM shift_performance
ORDER BY shift_date DESC, shift_name;

-- Efficiency trend
SELECT (shift_date::timestamp + CASE shift_name
  WHEN 'A' THEN interval '6 hours'
  WHEN 'B' THEN interval '14 hours'
  ELSE interval '22 hours' END) AS "time",
  efficiency_pct AS "efficiency"
FROM shift_performance
WHERE $__timeFilter(shift_date::timestamp)
ORDER BY "time";

-- Recent events
SELECT event_time AS "time", state, source
FROM machine_events
WHERE $__timeFilter(event_time)
ORDER BY event_time DESC;
