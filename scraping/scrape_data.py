import pandas as pd
from bs4 import BeautifulSoup
import requests
import json
import re
from bs4 import Tag

def fetch_html_content(url):
    """
    Fetches the HTML content from the given URL.

    Args:
        url (str): The York University Course Timetable URL to fetch.

    Returns:
        str: The HTML content, or None if an error occurred.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30) # Increased timeout
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
        return None

def get_td_text(tds, idx):
    try:
        td = tds[idx]
        return td.get_text(strip=True) if isinstance(td, Tag) else None
    except IndexError:
        return None

def extract_course_data_from_html(html_content):
    """
    Extracts course data from the given HTML content.

    Args:
        html_content (str): The HTML content of the timetable page.

    Returns:
        pd.DataFrame: A DataFrame containing the extracted course data.
                      Returns an empty DataFrame if no data is found.
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # After: soup = BeautifulSoup(html_content, 'html.parser')
    for idx, table in enumerate(soup.find_all('table')):
        for tr in table.find_all('tr', attrs={'bgcolor': '#000000'}):
            print(f"Table {idx} header row: {tr.get_text(separator=' | ', strip=True)}")

    main_table = None

    if main_table:
        rows = main_table.find_all('tr')
        print(f"Main table found with {len(rows)} rows")
    else:
        print("No main table found")
    
    # Find all tables
    all_tables = soup.find_all('table')

    for table in all_tables:
        if not isinstance(table, Tag):
            continue
        # Look for the specific header row within each table
        header_row = table.find('tr', attrs={'bgcolor': '#000000'})
        if isinstance(header_row, Tag):
            # Confirm it has the expected bold white text headers
            tds_in_header = header_row.find_all('td')
            # Check if one of the first few td's contains "Fac" (case-insensitive), dynamic check that it's the correct main data table
            print([td.get_text(strip=True) for td in tds_in_header])
            if any("Fac" in td.get_text(strip=True) for td in tds_in_header):
                main_table = table
                break

    if not main_table:
        print("Could not find the main course data table based on header row detection.")
        return pd.DataFrame()

    rows = main_table.find_all('tr')

    parsed_rows = []
    current_fac = None
    current_dept = None
    current_term = None
    current_adms_context_title = None
    last_course = None  # Track the last main course row for nesting sections
    last_section = None  # Track the last section for meeting times
    row_type_counts = {"course": 0, "section": 0, "meeting_time": 0, "colspan": 0, "other": 0}

    # Iterate through rows, skipping the main header row (index 0)
    for i, row in enumerate(rows):
        if i == 0:
            continue
        if not isinstance(row, Tag):
            continue
        tds = [td for td in row.find_all('td', recursive=False) if isinstance(td, Tag)]
        # Faculty/Dept/Term/Title row
        if len(tds) == 4 and tds[3].get('colspan') == '8':
            current_fac = tds[0].get_text(strip=True) or None
            current_dept = tds[1].get_text(strip=True) or None
            current_term = tds[2].get_text(strip=True) or None
            current_adms_context_title = tds[3].get_text(strip=True) or None
            continue
        # 7+ tds with colspan (colspan row)
        elif len(tds) >= 7 and tds[0].get('colspan') == '3':
            row_type_counts["colspan"] += 1
            # Try to extract as much as possible
            course_id = get_td_text(tds, 1)
            loi = get_td_text(tds, 2)
            course_type = get_td_text(tds, 3)
            meet = get_td_text(tds, 4)
            cat_no = get_td_text(tds, 5)
            instructors = get_td_text(tds, 7) if len(tds) > 7 else None
            notes_td = tds[8] if len(tds) > 8 else None
            notes_text = notes_td.get_text(strip=True) if isinstance(notes_td, Tag) else None
            course_outline_link = None
            if isinstance(notes_td, Tag):
                course_outline_link_tag = notes_td.find('a')
                if isinstance(course_outline_link_tag, Tag):
                    course_outline_link = course_outline_link_tag.get('href')
            course_record = {
                "faculty": current_fac,
                "department": current_dept,
                "term": current_term,
                "course_title": current_adms_context_title,
                "course_id": course_id,
                "loi": loi,
                "type": course_type,
                "meet": meet,
                "catalog_number": cat_no,
                "instructors": instructors,
                "notes_or_fees": notes_text,
                "course_outline_link": course_outline_link,
                "sections": []
            }
            parsed_rows.append(course_record)
            last_course = course_record
            last_section = None
        # 9-td course row (main course row)
        elif len(tds) == 9:
            row_type_counts["course"] += 1
            course_id = get_td_text(tds, 0)
            loi = get_td_text(tds, 1)
            course_type = get_td_text(tds, 2)
            meet = get_td_text(tds, 3)
            cat_no = get_td_text(tds, 4)
            day = get_td_text(tds, 5)
            time = get_td_text(tds, 6)
            instructors = get_td_text(tds, 7)
            notes_td = tds[8]
            notes_text = notes_td.get_text(strip=True) if isinstance(notes_td, Tag) else None
            course_outline_link = None
            if isinstance(notes_td, Tag):
                course_outline_link_tag = notes_td.find('a')
                if isinstance(course_outline_link_tag, Tag):
                    course_outline_link = course_outline_link_tag.get('href')
            course_record = {
                "faculty": current_fac,
                "department": current_dept,
                "term": current_term,
                "course_title": current_adms_context_title,
                "course_id": course_id,
                "loi": loi,
                "type": course_type,
                "meet": meet,
                "catalog_number": cat_no,
                "day": day,
                "time": time,
                "instructors": instructors,
                "notes_or_fees": notes_text,
                "course_outline_link": course_outline_link,
                "sections": []
            }
            parsed_rows.append(course_record)
            last_course = course_record
            last_section = None
        # 5-td row: section or meeting time
        elif len(tds) == 5:
            section_types = ["TUTR", "ONLN", "SEMR", "STDO"]
            is_section = any(st in (get_td_text(tds, idx) or "") for idx in range(5) for st in section_types)
            if is_section and last_course is not None:
                row_type_counts["section"] += 1
                section = {
                    "section_type": next((get_td_text(tds, idx) for idx in range(5) if (get_td_text(tds, idx) or "") and any(st in (get_td_text(tds, idx) or "") for st in section_types)), None),
                    "day": get_td_text(tds, 0),
                    "time": get_td_text(tds, 1),
                    "duration": get_td_text(tds, 2),
                    "campus": get_td_text(tds, 3),
                    "room": get_td_text(tds, 4),
                    "meeting_times": []
                }
                if "sections" not in last_course or last_course["sections"] is None:
                    last_course["sections"] = []
                last_course["sections"].append(section)
                last_section = section
            elif last_section is not None:
                row_type_counts["meeting_time"] += 1
                # Treat as meeting time for the last section
                meeting_time = {
                    "day": get_td_text(tds, 0),
                    "time": get_td_text(tds, 1),
                    "duration": get_td_text(tds, 2),
                    "campus": get_td_text(tds, 3),
                    "room": get_td_text(tds, 4)
                }
                if "meeting_times" not in last_section or last_section["meeting_times"] is None:
                    last_section["meeting_times"] = []
                last_section["meeting_times"].append(meeting_time)
            elif last_course is not None:
                row_type_counts["meeting_time"] += 1
                # If no section, treat as meeting time for the course
                meeting_time = {
                    "day": get_td_text(tds, 0),
                    "time": get_td_text(tds, 1),
                    "duration": get_td_text(tds, 2),
                    "campus": get_td_text(tds, 3),
                    "room": get_td_text(tds, 4)
                }
                if "meeting_times" not in last_course or last_course["meeting_times"] is None:
                    last_course["meeting_times"] = []
                last_course["meeting_times"].append(meeting_time)
            else:
                row_type_counts["other"] += 1
                # orphan 5-td row, just add as a record
                parsed_rows.append({"row_index": i, "tds": [get_td_text(tds, idx) for idx in range(5)]})
        else:
            row_type_counts["other"] += 1
            # Try to capture all data, even if row is malformed
            parsed_rows.append({"row_index": i, "tds": [td.get_text(strip=True) for td in tds]})

    # Create DataFrame
    if parsed_rows:
        df = pd.DataFrame(parsed_rows)
        # Post-processing: clean up empty strings or whitespace.
        for col in df.columns:
            if df[col].dtype == 'object': # Only apply to string columns
                df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
                df[col] = df[col].replace('', None)
    else:
        df = pd.DataFrame()
        print("No course data rows found in the HTML table based on identified patterns.")

    print(f"Row type summary: {{}}".format(row_type_counts))
    return df

# --- Main execution ---
if __name__ == "__main__":
    html_file = "scraping/content.html"
    print(f"Reading HTML content from: {html_file}")
    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()

    print('--- BEGIN HTML CONTENT (first 1000 chars) ---')
    print(html_content[:1000])
    print('--- END HTML CONTENT ---')
    print("HTML content loaded. Parsing data...")
    df = extract_course_data_from_html(html_content)

    if not df.empty:
        # Convert DataFrame to JSON
        # 'orient="records"' produces a list of dictionaries, one for each row
        json_output = df.to_json(orient="records", indent=4)
        # Ensure json_output is a string
        if json_output is None:
            json_output = "[]"
        # Save to a JSON file
        output_filename = "scraping/latest_course_catalog.json"
        with open(output_filename, "w") as f:
            f.write(json_output)
        print(f"JSON generated: {output_filename}")
    else:
        print("No course data was extracted from the HTML.")
