import csv
import re

input_file = 'influx.data.csv'
output_file = 'filtered_influx_data.csv'

def extract_mac(topic):
    # Extract MAC address from topic (e.g., .../60C342FEFF63B0E4/...)
    match = re.search(r'/([0-9A-F]{12})/', topic)
    return match.group(1) if match else ''

with open(input_file, newline='') as infile, open(output_file, 'w', newline='') as outfile:
    reader = csv.reader(infile)
    writer = csv.writer(outfile)
    # Write header
    writer.writerow(['measurement_time', 'value', 'measurement_type', 'mac_address'])
    for row in reader:
        if len(row) < 10:
            continue  # skip malformed lines
        measurement_time = row[5]
        value = row[6]
        measurement_type = row[7]
        topic = row[10]
        mac_address = extract_mac(topic)
        writer.writerow([measurement_time, value, measurement_type, mac_address])

print(f"Filtered data written to {output_file}")