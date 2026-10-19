"""Build an iCalendar feed from Open Seminar Finder seminar JSON files.

Usage: python3 build_ics.py <dir with seminars/*.json> <output.ics>
Includes only seminars with status "interested".
"""
import glob, json, os, sys
from datetime import datetime, timezone, timedelta

def esc(s):
    return (str(s).replace("\\", "\\\\").replace(";", "\\;")
            .replace(",", "\\,").replace("\r\n", "\\n").replace("\n", "\\n"))

def fold(line):
    out, b = [], line.encode("utf-8")
    while len(b) > 75:
        cut = 75 if not out else 74
        while cut > 0 and (b[cut] & 0xC0) == 0x80:
            cut -= 1
        out.append(b[:cut].decode("utf-8"))
        b = b[cut:]
    out.append(b.decode("utf-8"))
    return "\r\n ".join(out)

def utc(iso):
    d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return d.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def main(src, dst):
    docs = []
    for p in sorted(glob.glob(os.path.join(src, "**", "*.json"), recursive=True)):
        with open(p) as f:
            raw = json.load(f)
        data = raw.get("data", raw)
        data["id"] = raw.get("id") or os.path.splitext(os.path.basename(p))[0]
        if data.get("status") == "interested" and data.get("start"):
            docs.append(data)
    docs.sort(key=lambda d: d["start"])
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0",
             "PRODID:-//Open Seminar Finder//EN", "CALSCALE:GREGORIAN",
             "METHOD:PUBLISH", "X-WR-CALNAME:Open Bio Seminars",
             "X-WR-CALDESC:Open biology seminars marked Interested in Open Seminar Finder",
             "REFRESH-INTERVAL;VALUE=DURATION:PT12H", "X-PUBLISHED-TTL:PT12H"]
    for d in docs:
        start = d["start"]
        end = d.get("end") or (datetime.fromisoformat(start.replace("Z", "+00:00")) + timedelta(hours=1)).isoformat()
        summary = (d.get("speaker") + ": " if d.get("speaker") else "") + (d.get("title") or "Seminar")
        desc = []
        if d.get("speaker"):
            desc.append(d["speaker"] + (", " + d["speakerAffil"] if d.get("speakerAffil") else ""))
        series = " · ".join(x for x in [d.get("series"), d.get("host")] if x)
        if series: desc.append(series)
        if d.get("access"): desc.append("Access: " + d["access"])
        if d.get("join"): desc.append("Join/register: " + d["join"])
        if d.get("url"): desc.append("Event page: " + d["url"])
        if d.get("notes"): desc.append(d["notes"])
        ev = ["BEGIN:VEVENT", "UID:" + d["id"] + "@open-seminar-finder",
              "DTSTAMP:" + now, "DTSTART:" + utc(start), "DTEND:" + utc(end),
              "SUMMARY:" + esc(summary), "DESCRIPTION:" + esc("\n".join(desc))]
        loc = d.get("join") or d.get("url")
        if loc: ev.append("LOCATION:" + esc(loc))
        if d.get("url"): ev.append("URL:" + d["url"])
        ev.append("END:VEVENT")
        lines += ev
    lines.append("END:VCALENDAR")
    with open(dst, "w", newline="") as f:
        f.write("\r\n".join(fold(l) for l in lines) + "\r\n")
    print(f"wrote {len(docs)} events to {dst}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
