# (11, "pwrSta"),
# (12, "pwrStep"),
# (13, "EVSEPwrMax"),
# (14, "EVSEVolMax"),
# (15, "EVSEVolMin"),
# (16, "EVSECurMax"),
# (17, "realVol"),
# (18, "realCur"),
# (19, "stopReason")

import matplotlib.pyplot as plt
import mpld3
from datetime import datetime
import os
import shutil

input_log_file = "test logs/2024-07-30.log"

start_list = []
end_list = []

chgstart_keyword = '"chgRun":	1'
chgend_keyword = '"chgRun":	2,'

conn_ids = ["1", "2"]
conn_id_keyword = '"connId":'

output_folder = "output"

# Function to find keywords in a row
def find_keywords(row, key):
    try:
        start_index = row.find(key) + len(key)
        end_index = row.find(",", start_index) # or "}" for meterCur
        if end_index == -1:
            end_index = row.find("}", start_index)
        output = row[start_index:end_index]
        return output
    except ValueError as e:
        print(e)
        return "0"

# Function to read file sections
def read_file_section(start, end):
    try:
        with open(input_log_file, "r", encoding="utf-8") as file:
            file.seek(start)
            return file.readlines()[start:end]
    except FileNotFoundError:
        print(f"Error: The file '{input_log_file}' was not found.")
        return []
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")
        return []

# Read and save file section to new log
def save_session_to_log(content, session_number):
    log_file_name = f"session-{session_number}.log"
    try:
        if isinstance(content, list):
            content = ''.join(content)
        with open(log_file_name, 'w') as log_file:
            log_file.write(content)
        return log_file_name
    except Exception as e:
        print(f"Error saving log file '{log_file_name}': {e}")
        return None

# Write new log file filtered by chgstep & connID
def filter_log_file(input_file, output_file_prefix, chgstep, conn_id):
    chgstep_keyword = f'"chgStep":{chgstep}'
    
    output_file = f"{output_file_prefix}-{conn_id}.log"
    try:
        with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
            for line in infile:
                connId = find_keywords(line, conn_id_keyword)
                if chgstep_keyword in line and conn_id == connId:
                    outfile.write(line)
        return output_file
    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found.")
    except Exception as e:
        print(f"Error filtering the file '{input_file}': {e}")

def parse_log_file(log_file):
    data = {
        1: {"name": "GunPwrMax", "values": [], "time_in_secs": []},
        2: {"name": "EVPwrMax", "values": [], "time_in_secs": []},
        3: {"name": "EVVolMax", "values": [], "time_in_secs": []},
        4: {"name": "EVCurMax", "values": [], "time_in_secs": []},
        5: {"name": "reqVol", "values": [], "time_in_secs": []},
        6: {"name": "reqCur", "values": [], "time_in_secs": []},
        7: {"name": "soc", "values": [], "time_in_secs": []},
        8: {"name": "socTime", "values": [], "time_in_secs": []},
        9: {"name": "meterVol", "values": [], "time_in_secs": []},
        10: {"name": "meterCur", "values": [], "time_in_secs": []}
    }

    first = 0 # initialize first time stamp
    try:
        with open(log_file, 'r') as file:
            for line in file:
                for key, series in data.items():
                    value = find_keywords(line, f'"{series["name"]}":')
                    series["values"].append(int(value))

                    # converting date to seconds
                    if line.startswith('[INFO] '):
                        datetime_str = line[7:29]
                    else:
                        datetime_str = line[:23] 
                    dt = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S.%f") # 2024-01-13T11:38:55.523 
                    seconds = dt.timestamp()
                    if first == 0:
                        first = seconds
                        series["time_in_secs"].append(0)
                    else:
                        series["time_in_secs"].append(seconds - first)
        return data
    except FileNotFoundError:
        print(f"Error: File '{log_file}' not found.")
        return {}
    except Exception as e:
        print(f"Error parsing the log file '{log_file}': {e}")
        return {}

def plot_data(data, selection, index, conn_id):
    try:
        selected_series = data[selection]["name"]
        selected_values = data[selection]["values"][::10]
        selected_times = data[selection]["time_in_secs"][::10]

        if(len(selected_values) > 30):
            plt.figure(figsize=(12, 7))
            plt.plot(selected_times, selected_values, label=selected_series, color='blue', linewidth=0.7, marker='o', markersize=2, alpha=0.7)
            plt.xlabel('Time in Seconds')
            plt.ylabel('Value')
            plt.title(f'Graph of {selected_series}')
            plt.legend()

            plt.xlim(0, max(selected_times) * 1.05)
            plt.ylim(0, max(selected_values) * 1.05)

            plt.locator_params(axis='x', nbins=10)
            plt.locator_params(axis='y', nbins=10) 

            img_path = os.path.join(output_folder, f"graph_session_{index}-{conn_id}.png")
            plt.savefig(img_path)

        # Save the plot as an interactive HTML file
        #mpld3.save_html(plt.gcf(), f"interactive_graph_session_{index}.html")
        plt.clf()  
    except KeyError:
        print(f"Error: Invalid selection '{selection}'. No data series found.")
    except Exception as e:
        print(f"Error generating the plot: {e}")

def clear_output_folder(folder):
    if os.path.exists(folder):
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)  # Delete the file
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)  # Delete the directory
            except Exception as e:
                print(f"Error deleting file {file_path}: {e}")
    else:
        os.makedirs(folder)  # Create the folder if it doesn't exist

def find_charging_sessions(content):
    start_list, end_list = [], []
    temp_hold_var = 0
    for index, line in enumerate(content):
        if chgstart_keyword in line and temp_hold_var != 1:
            start_list.append(index)
            temp_hold_var = 1
        elif chgend_keyword in line and temp_hold_var == 1:
            end_list.append(index)
            temp_hold_var = 2

    if not start_list or not end_list:
        print("Error: No charging sessions found in the log.")
        return []
    
    return [[start, end] for start, end in zip(start_list, end_list)]

def validate_chgstep():
    chgstep = input("Enter the charge step number (1-9): ")
    try:
        chgstep = int(chgstep)
        if chgstep < 1 or chgstep > 9:
            raise ValueError
        return chgstep
    except ValueError:
        print("Error: Invalid charge step. Please enter a number between 1 and 9.")
        return None

def get_user_selection():
    data_series_mapping = {
            1: 'GunPwrMax',
            2: 'EVPwrMax',
            3: 'EVVolMax',
            4: 'EVCurMax',
            5: 'reqVol',
            6: 'reqCur',
            7: 'soc',
            8: 'socTime',
            9: 'meterVol',
            10: 'meterCur'
        }
    
    # Display the options to the user
    for key, name in data_series_mapping.items():
        print(f"{key}: {name}")

    try:
        selection = int(input("Enter the number corresponding to the data series you want to plot: "))
        if selection not in data_series_mapping:
            raise ValueError
        return selection
    except ValueError:
        print("Error: Invalid selection. Please enter a number between 1 and 10.")
        return None

def process_and_plot_session(index, session, chgstep, selection):
    content = read_file_section(session[0], session[1])
    temp_log_file = save_session_to_log(content, index + 1)
    if not temp_log_file:
        return

    for conn_id in conn_ids:
        log_prefix = f'filtered_session_{index + 1}'
        filtered_log = filter_log_file(temp_log_file, log_prefix, chgstep, conn_id)
        data = parse_log_file(filtered_log)
        
        if not data:
            continue
        
        plot_data(data, selection, index + 1, conn_id)
        os.remove(filtered_log)

    os.remove(temp_log_file)

def main():
    try:
        clear_output_folder(output_folder)

        # Read the log file content
        with open(input_log_file, 'r') as file:
            content = file.readlines()

        total_charging_sessions = find_charging_sessions(content)
        if not total_charging_sessions:
            return

        chgstep = validate_chgstep()
        if chgstep is None:
            return

        selection = get_user_selection()
    
        for index, session in enumerate(total_charging_sessions):     
            process_and_plot_session(index, session, chgstep, selection)

    except FileNotFoundError:
        print(f"Error: Log file '{input_log_file}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()