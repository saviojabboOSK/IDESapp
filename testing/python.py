import csv

input_file = 'influx.data.csv'
output_file = 'filtered_influx_data.csv'

def extract_mac(topic):
    parts = topic.split('/')
    if len(parts) >= 2:
        return parts[-2]
    return ''

with open(input_file, newline='') as infile, open(output_file, 'w', newline='') as outfile:
    reader = csv.reader(infile)
    writer = csv.writer(outfile)
    writer.writerow(['measurement_time', 'value', 'measurement_type', 'mac_address'])
    for row in reader:
        if len(row) < 11:
            continue
        measurement_time = row[5]
        value = row[6]
        measurement_type = row[7]
        topic = row[10]
        mac_address = extract_mac(topic)
        writer.writerow([measurement_time, value, measurement_type, mac_address])

print(f"Filtered data written to {output_file}")