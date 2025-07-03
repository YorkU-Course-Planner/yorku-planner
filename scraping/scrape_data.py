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

    # Iterate through rows, skipping the main header row (index 0)
    for i, row in enumerate(rows):
        if i == 0:
            continue
        if not isinstance(row, Tag):
            continue
        tds = [td for td in row.find_all('td', recursive=False) if isinstance(td, Tag)]
        if len(tds) == 4 and tds[3].get('colspan') == '8':
            current_fac = tds[0].get_text(strip=True) or None
            current_dept = tds[1].get_text(strip=True) or None
            current_term = tds[2].get_text(strip=True) or None
            current_adms_context_title = tds[3].get_text(strip=True) or None
            continue
        elif len(tds) >= 7 and tds[0].get('colspan') == '3':
            if len(tds) < 9:
                print(f"Warning: Row {i} had {len(tds)} tds, expected 9. HTML: {str(row)[:100]}")
            course_id = get_td_text(tds, 1)
            loi = get_td_text(tds, 2)
            course_type = get_td_text(tds, 3)
            meet = get_td_text(tds, 4)
            cat_no = get_td_text(tds, 5)
            schedule_entries = []
            schedule_td = tds[6] if len(tds) > 6 else None
            if isinstance(schedule_td, Tag):
                schedule_table = schedule_td.find('table')
                if isinstance(schedule_table, Tag):
                    inner_rows = schedule_table.find_all('tr') if isinstance(schedule_table, Tag) else []
                    for inner_row in inner_rows:
                        if isinstance(inner_row, Tag):
                            inner_tds = inner_row.find_all('td') if isinstance(inner_row, Tag) else []
                            if len(inner_tds) == 5:
                                schedule_entry = {
                                    "Day": get_td_text(inner_tds, 0),
                                    "Time": get_td_text(inner_tds, 1),
                                    "Dur": get_td_text(inner_tds, 2),
                                    "Campus": get_td_text(inner_tds, 3),
                                    "Room": get_td_text(inner_tds, 4)
                                }
                                schedule_entries.append(schedule_entry)
            instructors = get_td_text(tds, 7)
            notes_td = tds[8] if len(tds) > 8 else None
            notes_text = notes_td.get_text(strip=True) if isinstance(notes_td, Tag) else None
            course_outline_link = None
            if isinstance(notes_td, Tag):
                course_outline_link_tag = notes_td.find('a')
                if isinstance(course_outline_link_tag, Tag):
                    course_outline_link = course_outline_link_tag.get('href')
            if schedule_entries:
                for sched_entry in schedule_entries:
                    parsed_rows.append({
                        "faculty": current_fac,
                        "department": current_dept,
                        "term": current_term,
                        "course_title": current_adms_context_title,
                        "course_id": course_id,
                        "loi": loi,
                        "type": course_type,
                        "meet": meet,
                        "catalog_number": cat_no,
                        "day": sched_entry.get("Day"),
                        "time": sched_entry.get("Time"),
                        "duration": sched_entry.get("Dur"),
                        "campus": sched_entry.get("Campus"),
                        "room": sched_entry.get("Room"),
                        "instructors": instructors,
                        "notes_or_fees": notes_text,
                        "course_outline_link": course_outline_link
                    })
            else:
                parsed_rows.append({
                    "faculty": current_fac,
                    "department": current_dept,
                    "term": current_term,
                    "course_title": current_adms_context_title,
                    "course_id": course_id,
                    "loi": loi,
                    "type": course_type,
                    "meet": meet,
                    "catalog_number": cat_no,
                    "day": None,
                    "time": None,
                    "duration": None,
                    "campus": None,
                    "room": None,
                    "instructors": instructors,
                    "notes_or_fees": notes_text,
                    "course_outline_link": course_outline_link
                })
        else:
            print(f"Skipping row {i}: {len(tds)} tds. HTML: {str(row)[:100]}")

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
