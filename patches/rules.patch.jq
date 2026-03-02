map(select(.id != 5)) +
[
  {
    "id": 101, "priority": 1,
    "action": {"type": "block"},
    "condition": {
      "urlFilter": "||coccoc.com",
      "resourceTypes": ["main_frame","sub_frame","stylesheet","script","image","font","object","xmlhttprequest","ping","csp_report","media","websocket","other"]
    }
  },
  {
    "id": 102, "priority": 1,
    "action": {"type": "block"},
    "condition": {
      "urlFilter": "||qccoccocmedia.vn",
      "resourceTypes": ["main_frame","sub_frame","stylesheet","script","image","font","object","xmlhttprequest","ping","csp_report","media","websocket","other"]
    }
  },
  {
    "id": 103, "priority": 1,
    "action": {"type": "block"},
    "condition": {
      "urlFilter": "||coccoc.telemetry.eyeo.com",
      "resourceTypes": ["main_frame","sub_frame","stylesheet","script","image","font","object","xmlhttprequest","ping","csp_report","media","websocket","other"]
    }
  }
]

