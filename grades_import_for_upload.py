import csv
import os
import requests
from datetime import datetime
import sys
import pandas as pd

CANVAS_BASE_URL = "SCHOOL.instructure.com"
CANVAS_TOKEN = "GENERATED TOKEN"
NTFY_TOPIC = "NAMED TOPIC"

A_CUTOFF = 89.5
CURRENT_WEIGHT = 0.8
FINAL_WEIGHT = 0.2
EXCLUDE_COURSES = ["COURSES TO EXCLUDE"]
OUTPUT_FILE = f"canvas_grades_{datetime.now().strftime("%Y-%m-%d")}.csv"


def get_grades():
  url = f"{CANVAS_BASE_URL}/api/v1/courses"
  headers = {"Authorization": f"Bearer {CANVAS_TOKEN}"}
  params = {
    "enrollment_status": "active",
    "include[]": "total_scores",
    "per_page": 100,
  }
  grades = {}

  while url:
    resp = requests.get(url, headers=headers, params=params, timeout=15)
    resp.raise_for_status()
    print(resp.status_code, resp.url)
    print(resp.history)
    for course in resp.json():
      name = course.get("name")
      if name in EXCLUDE_COURSES:
        continue
      for enr in course.get("enrollments", []):
        score = enr.get("computed_current_score")
        if name and score is not None:
          grades[name] = score
    url = resp.links.get("next", {}).get("url")
    params = None
  return grades

def needed_on_final(current_score):
  return (A_CUTOFF - current_score * CURRENT_WEIGHT) / FINAL_WEIGHT

def write_csv(grades):
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Course", "Current Grade (%)", "Final Grade Needed (%)"])
        for course, score in grades.items():
            writer.writerow([course, round(score, 2), round(needed_on_final(score), 2)])
    print(f"Wrote {OUTPUT_FILE}")

def build_message(grades):
    lines = []
    for course, score in grades.items():
        need = needed_on_final(score)
        if need > 100:
            result = f"{need:.1f}% (A not reachable)"
        elif need <= 60:
            result = f"A locked in {need:.1f}"
        else:
            result = f"{need:.1f}%"
        lines.append(f"{course}: {score:.1f}% -> need {result}")
    return "\n".join(lines)


def send_push(body):
    resp = requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=body.encode("utf-8"),
        headers={"Title": "Final grades needed for an A"},
        timeout=15,
    )
    resp.raise_for_status()
    print("Notification sent")

def main():
    grades = get_grades()
    if not grades:
        print("No graded courses found.")
        return
    write_csv(grades)
    send_push(build_message(grades))

if __name__ == "__main__":
  main()
