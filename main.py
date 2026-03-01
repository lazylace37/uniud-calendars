import asyncio
import concurrent.futures
import json
import urllib.parse
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from uniud import Course, get_course_lessons, get_year_courses, get_years


def format_datetime(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%SZ")


def create_vevent(
    summary: str,
    uid: str,
    dtstart: str,
    dtend: str,
    dtstamp: str,
    last_modified: str,
    location: str | None = None,
) -> str:
    location_line = f"LOCATION:{location}\n" if location else ""
    return (
        f"BEGIN:VEVENT\n"
        f"DTSTART:{dtstart}\n"
        f"DTEND:{dtend}\n"
        f"SUMMARY:{summary}\n"
        f"UID:{uid}\n"
        f"LAST-MODIFIED:{last_modified}\n"
        f"DTSTAMP:{dtstamp}\n"
        f"{location_line}"
        f"END:VEVENT"
    )


def create_calendar(events: list[str]) -> str:
    return (
        "BEGIN:VCALENDAR\n"
        "VERSION:2.0\n"
        "PRODID:-//University of Udine//Timetables//EN\n"
        "CALSCALE:GREGORIAN\n"
        "METHOD:PUBLISH\n"
        "X-WR-TIMEZONE:Europe/Rome\n" + "\n".join(events) + "\n"
        "END:VCALENDAR"
    )


def nesteddefaultdict():
    return defaultdict(nesteddefaultdict)


def get_course_timetables(course: Course, latest_year: int, now: datetime):
    course_dict: defaultdict = nesteddefaultdict()
    for anno in course["elenco_anni"]:
        lessons_map = defaultdict(list)
        anno_di_insegnamento: str = str(anno["valore"].split("|")[1])

        lessons, closures = get_course_lessons(
            course["valore"], latest_year, anno["valore"]
        )

        # region Create and save .ical file
        dtstamp = format_datetime(now)
        last_modified = format_datetime(now)

        vevents = []
        for lesson in lessons:
            uid = f"{(int)(lesson.start_date.timestamp())}"
            vevent = create_vevent(
                summary=lesson.nome_insegnamento,
                uid=uid,
                dtstart=format_datetime(lesson.start_date),
                dtend=format_datetime(lesson.end_date),
                dtstamp=dtstamp,
                last_modified=last_modified,
                location=f"{lesson.docente} - {lesson.room}",
            )
            vevents.append(vevent)
            lessons_map[lesson.nome_insegnamento].append(vevent)
        for closure in closures:
            uid = f"{(int)(closure.start_date.timestamp())}"
            vevent = create_vevent(
                summary="HOLIDAY: lessons not scheduled",
                uid=uid,
                dtstart=format_datetime(closure.start_date),
                dtend=format_datetime(closure.end_date),
                dtstamp=dtstamp,
                last_modified=last_modified,
            )
            vevents.append(vevent)

        # Sort events
        vevents.sort(key=lambda e: e.split("DTSTART:")[1].split("\n")[0])

        ical_file_name = (
            f"{course['label']} - ANNO {anno['label']}.ics"
            if anno_di_insegnamento.isdigit()
            else f"{course['label']} - {anno['label']}.ics"
        )
        ical_file_path_name = (
            f"ical/{course['label']}/{course['tipo']}/{ical_file_name}"
        )
        ical_file_path = Path(ical_file_path_name)
        ical_file_path.parent.mkdir(exist_ok=True, parents=True)
        with open(str(ical_file_path), "w") as f:
            f.write(create_calendar(vevents))
        # endregion

        link = f"https://raw.githubusercontent.com/lazylace37/uniud-calendars/main/{urllib.parse.quote(ical_file_path_name)}"
        course_dict[anno_di_insegnamento][anno["label"]] = link

        # region Create and save .ical file for each lesson
        for lesson_name, vevents in lessons_map.items():
            vevents.sort(key=lambda e: e.split("DTSTART:")[1].split("\n")[0])
            ical_file_name = f"{lesson_name}.ics"
            ical_file_path_name = f"ical/{course['label']}/{course['tipo']}/{anno['label']}/{ical_file_name}"
            ical_file_path = Path(ical_file_path_name)
            ical_file_path.parent.mkdir(exist_ok=True, parents=True)
            with open(str(ical_file_path), "w") as f:
                f.write(create_calendar(vevents))
        # endregion
    print(f"Done {course['label']} - {course['tipo']}")
    return course["label"], course["tipo"], course_dict


def main():
    # Delete all calendars
    for f in Path("./ical").glob("**/*"):
        if f.is_file():
            f.unlink()

    ordered_years = sorted(get_years(), key=lambda y: int(y["valore"]), reverse=True)
    assert len(ordered_years) > 0

    latest_year = int(ordered_years[0]["valore"])
    lastest_year_courses = get_year_courses(latest_year)

    now = datetime.now(timezone.utc)
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        future = asyncio.gather(
            *[
                loop.run_in_executor(
                    executor, get_course_timetables, course, latest_year, now
                )
                for course in lastest_year_courses
            ]
        )
    results = loop.run_until_complete(future)
    results_time_s = (datetime.now(timezone.utc) - now).total_seconds()
    print(f"Download courses timetables took {results_time_s}s")

    all_courses: defaultdict = nesteddefaultdict()
    for course_label, course_type, course_dict in results:
        for anno_di_insegnamento, anno in course_dict.items():
            for anno_label, link in anno.items():
                all_courses[course_label][course_type][anno_di_insegnamento][
                    anno_label
                ] = link

    # Write .json file
    with open("ical/calendars.json", "w") as f:
        f.write(json.dumps(all_courses))

    # Write README.md
    environment = Environment(loader=FileSystemLoader("./"))
    template = environment.get_template("README.md.template")
    content = template.render(
        all_courses=all_courses,
    )
    with open("README.md", mode="w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    main()
