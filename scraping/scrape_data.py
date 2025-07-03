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

    main_table = None
    
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
            if any("Fac" in td.get_text(strip=True) for td in tds_in_header[:3]):
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
        tds = [td for td in row.find_all('td', recursive=False) if isinstance(td, Tag)] # Direct children TDs, Tag objects

        # Case 1: Context header row (e.g., "AP ADMB S2 Essentials of Emergency Management")
        # These rows have 3 specific TDs (Fac, Dept, Term) and then a TD with colspan='8' for the title.
        if len(tds) == 4 and tds[3].get('colspan') == '8':
            current_fac = tds[0].get_text(strip=True) or None
            current_dept = tds[1].get_text(strip=True) or None
            current_term = tds[2].get_text(strip=True) or None
            current_adms_context_title = tds[3].get_text(strip=True) or None
            continue # This row is a context header, not a data entry
        
        # Case 2: Actual data row
        # These rows start with a <td colspan='3'>&nbsp;</td> (index 0)
        # followed by 8 more actual data columns (total 9 direct `<td>` children)
        elif len(tds) == 9 and tds[0].get('colspan') == '3':
            # Extract data from the relevant cells (tds[1] to tds[8])
            course_id = tds[1].get_text(strip=True) if isinstance(tds[1], Tag) else None
            loi = tds[2].get_text(strip=True) if isinstance(tds[2], Tag) else None
            course_type = tds[3].get_text(strip=True) if isinstance(tds[3], Tag) else None
            meet = tds[4].get_text(strip=True) if isinstance(tds[4], Tag) else None
            cat_no = tds[5].get_text(strip=True) if isinstance(tds[5], Tag) else None

            # Handle the nested table for schedule information (tds[6])
            schedule_entries = []
            if isinstance(tds[6], Tag):
                schedule_table = tds[6].find('table')
                if isinstance(schedule_table, Tag):
                    inner_rows = schedule_table.find_all('tr')
                    for inner_row in inner_rows:
                        if isinstance(inner_row, Tag):
                            inner_tds = inner_row.find_all('td')
                            if len(inner_tds) == 5:
                                schedule_entry = {
                                    "Day": inner_tds[0].get_text(strip=True) if isinstance(inner_tds[0], Tag) else None,
                                    "Time": inner_tds[1].get_text(strip=True) if isinstance(inner_tds[1], Tag) else None,
                                    "Dur": inner_tds[2].get_text(strip=True) if isinstance(inner_tds[2], Tag) else None,
                                    "Campus": inner_tds[3].get_text(strip=True) if isinstance(inner_tds[3], Tag) else None,
                                    "Room": inner_tds[4].get_text(strip=True) if isinstance(inner_tds[4], Tag) else None
                                }
                                schedule_entries.append(schedule_entry)
            
            # Instructors (tds[7])
            instructors = tds[7].get_text(strip=True) if isinstance(tds[7], Tag) else None
            
            # Notes/Additional Fees (tds[8])
            notes_td = tds[8]
            notes_text = notes_td.get_text(strip=True) if isinstance(notes_td, Tag) else None
            course_outline_link = None
            if isinstance(notes_td, Tag):
                course_outline_link_tag = notes_td.find('a')
                if isinstance(course_outline_link_tag, Tag):
                    course_outline_link = course_outline_link_tag.get('href')
            
            # If there are multiple schedule entries (multiple meeting times for one course section),
            # create a separate record for each to keep the final DataFrame/JSON flat.
            if schedule_entries:
                for sched_entry in schedule_entries:
                    parsed_rows.append({
                        "Fac": current_fac,
                        "Dept": current_dept,
                        "Term": current_term,
                        "Course Title": current_adms_context_title, # Title of the ADMS group
                        "Course ID": course_id,
                        "LOI": loi,
                        "Type": course_type,
                        "Meet": meet,
                        "Cat.No.": cat_no,
                        "Day": sched_entry.get("Day"),
                        "Time": sched_entry.get("Time"),
                        "Dur": sched_entry.get("Dur"),
                        "Campus": sched_entry.get("Campus"),
                        "Room": sched_entry.get("Room"),
                        "Instructors": instructors,
                        "Notes/Additional Fees": notes_text, # Use just the text for the main entry
                        "Course Outline Link": course_outline_link
                    })
            else: # Handle cases where schedule table might be empty or missing for some reason
                parsed_rows.append({
                    "Fac": current_fac,
                    "Dept": current_dept,
                    "Term": current_term,
                    "Course Title": current_adms_context_title,
                    "Course ID": course_id,
                    "LOI": loi,
                    "Type": course_type,
                    "Meet": meet,
                    "Cat.No.": cat_no,
                    "Day": None,
                    "Time": None,
                    "Dur": None,
                    "Campus": None,
                    "Room": None,
                    "Instructors": instructors,
                    "Notes/Additional Fees": notes_text,
                    "Course Outline Link": course_outline_link
                })
        # If it's neither a context row nor a data row, skip it.
        # This handles other empty rows, or unexpected structures.

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
        output_filename = "scraping/york_university_course_timetable.json"
        with open(output_filename, "w") as f:
            f.write(json_output)
        print(f"JSON generated: {output_filename}")
    else:
        print("No course data was extracted from the HTML.")