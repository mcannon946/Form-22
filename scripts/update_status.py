#!/usr/bin/env python3
"""Update STATUS.md from status.json  called by GitHub Actions."""
import json, pathlib, datetime

ROOT = pathlib.Path(__file__).parent.parent

def load_status():
        with open(ROOT / "status.json") as f:
                    return json.load(f)

                    def badge(status):
                            colors = {"complete": "brightgreen", "in_progress": "blue",
                                          "pending": "lightgrey", "blocked": "red"}
                                              label = status.replace("_", " ")
                                                  color = colors.get(status, "lightgrey")
                                                      return f"![{label}](https://img.shields.io/badge/status-{label.replace(' ','%20')}-{color})"
                                                      
                                                      def write_status_md(data):
                                                          lines = ["# NC Form-22 Generator  Milestone Status\n",
                                                                       f"_Last updated: {data['last_updated']} UTC_\n\n",
                                                                                    "| # | Milestone | Status | Notes |\n",
                                                                                                 "|---|-----------|--------|-------|\n"]
                                                                                                     for m in data["milestones"]:
                                                                                                                lines.append(f"| {m['id']} | {m['title']} | {badge(m['status'])} | {m.get('notes','')} |\n")
                                                                                                                    with open(ROOT / "STATUS.md", "w") as f:
                                                                                                                            f.writelines(lines)
                                                                                                                                print("STATUS.md updated.")
                                                                                                                                
                                                                                                                                def main():
                                                                                                                                    data = load_status()
                                                                                                                                        data["last_updated"] = datetime.datetime.utcnow().isoformat(timespec="seconds")
                                                                                                                                            write_status_md(data)
                                                                                                                                                with open(ROOT / "status.json", "w") as f:
                                                                                                                                                        json.dump(data, f, indent=2)
                                                                                                                                                        
                                                                                                                                                        if __name__ == "__main__":
                                                                                                                                                            main()}