del(.update_url) |

.permissions -= ["favicon", "metricsPrivate"] |

.content_scripts |= map(
  select(.js | map(test("scrapper|promote|ccserp")) | any | not)
) |

walk(
  if type == "object" and has("exclude_matches") then
    .exclude_matches |= map(select(test("coccoc\\.com|fireant\\.vn|doubleclick\\.net") | not)) |
    if .exclude_matches == [] then del(.exclude_matches) else . end
  else . end
) |

if (.declarative_net_request.rule_resources | map(select(.path == "rules.json")) | length) == 0
then .declarative_net_request.rule_resources += [{"id": "ruleset_patched", "enabled": true, "path": "rules.json"}]
else .
end

