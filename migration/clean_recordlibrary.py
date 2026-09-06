import csv
from datetime import datetime

input_file = "/Users/davidgolden/Documents/WPKN_Migration/recordlibrary.csv"
output_file = "/Users/davidgolden/Documents/WPKN_Migration/recordlibrary_clean.csv"

keep_fields = [
    'LibraryNumber', 'MediaType', 'Status', 'Artist', 'Title',
    'Genre', 'Style', 'ReleaseYear', 'ReleaseDate', 'Label',
    'Comments', 'Section', 'NeedsReview', 'ID'
]

def clean_date(date_str):
    if not date_str or date_str.strip() == '':
        return ''
    try:
        dt = datetime.strptime(date_str.strip(), '%m/%d/%Y %H:%M:%S')
        return dt.strftime('%Y-%m-%d')
    except ValueError:
        return ''

with open(input_file, newline='', encoding='cp1252') as infile, \
     open(output_file, 'w', newline='', encoding='utf-8') as outfile:

    reader = csv.DictReader(infile, delimiter='|', quotechar='"')
    writer = csv.DictWriter(outfile, fieldnames=keep_fields, 
                            delimiter='|', quotechar='"',
                            quoting=csv.QUOTE_NONNUMERIC,
                            extrasaction='ignore')
    writer.writeheader()

    count = 0
    for row in reader:
        row['ReleaseDate'] = clean_date(row.get('ReleaseDate', ''))
        if not row['Status'] or row['Status'].strip() == '':
            row['Status'] = '8'
        if not row['MediaType'] or row['MediaType'].strip() == '':
            row['MediaType'] = '1'
        writer.writerow(row)
        count += 1

print(f"Done! {count} records written to recordlibrary_clean.csv")
